import os
import requests
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Query
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from app.menu_handler import load_menu
from app.graph import app_graph
from app.config import META_VERIFY_TOKEN, META_ACCESS_TOKEN, PHONE_NUMBER_ID

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing App & Loading Menu...")
    load_menu()  # Ingest PDF/Excel menu into RAG
    yield

app = FastAPI(title="Omnichannel Multi-Agent Restaurant", lifespan=lifespan)

def send_whatsapp_message(to_number: str, text: str):
    """Sends native message via Meta Graph API"""
    if not META_ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print(f"MOCK WA SEND to {to_number}: {text}")
        return
        
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "text": {"body": text}}
    requests.post(url, headers=headers, json=payload)

@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: int = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Meta Webhook Verification"""
    if hub_mode == "subscribe" and hub_verify_token == META_VERIFY_TOKEN:
        return hub_challenge
    raise HTTPException(status_code=403, detail="Invalid verify token")

@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """Receive messages from WhatsApp/Insta & Process via LangGraph"""
    body = await request.json()
    
    try:
        # Parse Meta WhatsApp Webhook structure
        entry = body['entry'][0]
        changes = entry['changes'][0]['value']
        
        if 'messages' in changes:
            msg = changes['messages'][0]
            phone_number = msg['from']
            user_text = msg['text']['body']
            
            # The phone number acts as the unique LangGraph Thread ID!
            config = {"configurable": {"thread_id": phone_number}}
            
            # Check if Graph is paused for this user (HITL)
            state = app_graph.get_state(config)
            if state.next:
                # Resume graph with user's 'yes' or 'no'
                stream = app_graph.stream(Command(resume=user_text), config=config, stream_mode="values")
            else:
                # Normal chat input
                stream = app_graph.stream({"messages":[HumanMessage(content=user_text)]}, config=config, stream_mode="values")
                
            for _ in stream: pass # Execute stream
            
            # Get latest state
            new_state = app_graph.get_state(config)
            
            if new_state.next:
                # Graph paused on interrupt(), send the interrupt message to user
                bot_reply = new_state.tasks[0].interrupts[0].value
            else:
                # Graph finished execution
                bot_reply = new_state.values["messages"][-1].content
                
            # Reply back to WhatsApp
            send_whatsapp_message(phone_number, bot_reply)
            
    except Exception as e:
        print(f"Webhook Error: {e}")
        
    return {"status": "ok"}
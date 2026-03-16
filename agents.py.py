from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import Command, interrupt
from langgraph.graph import MessagesState
from app.config import GROQ_API_KEY, GEMINI_API_KEY
from app.tools import (search_menu, map_and_weather, timer, event_manager_google_sheet, 
                       calculator_and_converter, TransferToWaiter, TransferToEventManager)

llm_manager = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7, api_key=GEMINI_API_KEY)
llm_pii = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, api_key=GEMINI_API_KEY)
llm_waiter = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7, api_key=GROQ_API_KEY)

def pii_middleware_node(state: MessagesState):
    """Redacts PII data (credit cards, UPI, phones) without RegEx."""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, HumanMessage):
        prompt = f"Identify private info (financial, cards, UPI, names, numbers, addresses). Replace with [REDACTED]. Return ONLY redacted text.\nInput: {last_msg.content}"
        redacted = llm_pii.invoke(prompt).content.strip()
        return {"messages": [HumanMessage(content=redacted, id=last_msg.id)]}
    return {}

manager_tools =[event_manager_google_sheet, map_and_weather, TransferToWaiter]
def event_manager_node(state: MessagesState) -> Command[Literal["waiter", "manager_tools", "__end__"]]:
    sys_prompt = """You are the Event Manager. 🎩 
    - Be highly hospitable, use professional emojis.
    - If user wants to order food -> use TransferToWaiter.
    - If it's about social gatherings/events -> Help them!
    - Use event_manager_google_sheet to record events."""
    
    response = llm_manager.bind_tools(manager_tools).invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    if response.tool_calls:
        for tc in response.tool_calls:
            if tc["name"] == "TransferToWaiter": return Command(goto="waiter")
        return Command(goto="manager_tools", update={"messages": [response]})
    return Command(goto="__end__", update={"messages": [response]})

waiter_tools =[search_menu, timer, calculator_and_converter, map_and_weather, TransferToEventManager]
def waiter_node(state: MessagesState) -> Command[Literal["waiter_tools", "event_manager", "__end__"]]:
    sys_prompt = """You are the AI Waiter 👨‍🍳. Be lively, use food emojis (🍔🥗), and format text beautifully for WhatsApp (*bold*, _italic_).
    1. ALWAYS use the search_menu tool to read our actual menu before suggesting food.
    2. Use map_and_weather to suggest food matching the local vibe.
    3. AFTER order selection, STRICTLY ask together:
       - Spicy level? (No, Low, Medium, High 🌶️)
       - Any customizations? (And suggest 1 complementary side/drink).
    4. Calculate bill using calculator_and_converter.
    5. If asked about parties/events -> TransferToEventManager."""
    
    response = llm_waiter.bind_tools(waiter_tools).invoke([SystemMessage(content=sys_prompt)] + state["messages"])
    if response.tool_calls:
        for tc in response.tool_calls:
            if tc["name"] == "TransferToEventManager": return Command(goto="event_manager")
        return Command(goto="waiter_tools", update={"messages": [response]})
    return Command(goto="__end__", update={"messages": [response]})
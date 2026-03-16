from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from langchain_core.messages import ToolMessage
from app.agents import (pii_middleware_node, event_manager_node, waiter_node, 
                        manager_tools, waiter_tools, MessagesState)

def manager_tools_node(state: MessagesState):
    last_msg = state["messages"][-1]
    for tc in last_msg.tool_calls:
        if tc["name"] == "event_manager_google_sheet":
            # HITL feature
            approval = interrupt("Please reply 'yes' to confirm saving this event, or 'no' to cancel. 📅")
            if approval.lower() not in ["yes", "y"]:
                return Command(goto="event_manager", update={"messages": [ToolMessage(tool_call_id=tc["id"], content="User denied.")]})
    
    result = ToolNode(manager_tools).invoke(state)
    return Command(goto="event_manager", update=result)

def waiter_tools_node(state: MessagesState):
    result = ToolNode(waiter_tools).invoke(state)
    return Command(goto="waiter", update=result)

builder = StateGraph(MessagesState)
builder.add_node("pii_middleware", pii_middleware_node)
builder.add_node("event_manager", event_manager_node)
builder.add_node("waiter", waiter_node)
builder.add_node("manager_tools", manager_tools_node)
builder.add_node("waiter_tools", waiter_tools_node)

builder.add_edge(START, "pii_middleware")
builder.add_edge("pii_middleware", "event_manager")

memory = MemorySaver()
app_graph = builder.compile(checkpointer=memory)

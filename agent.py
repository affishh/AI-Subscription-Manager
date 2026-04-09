import os
from dotenv import load_dotenv
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver 


from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_community.tools.tavily_search import TavilySearchResults

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Subscription

from datetime import date
import json
load_dotenv()

# ---------------- STATE ---------------- #
class State(TypedDict):
    messages: Annotated[list, add_messages]

# ---------------- LLM ---------------- #
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    streaming=True
)

# ---------------- LONG-TERM MEMORY (FILE) ---------------- #
def save_memory(user_id: int, query: str):
    filename = f"memory_{user_id}.json"
    data = []
    if os.path.exists(filename):
        with open(filename, "r") as f:
            data = json.load(f)
    data.append(query)
    with open(filename, "w") as f:
        json.dump(data[-10:], f)

def load_memory(user_id: int):
    filename = f"memory_{user_id}.json"
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as f:
        return json.load(f)

# ---------------- TOOLS (USER-SPECIFIC) ---------------- #
@tool
def get_total_cost(config: RunnableConfig):
    """Get total subscription cost for current user"""
    user_id = config["configurable"].get("user_id")
    db = SessionLocal()
    subs = db.query(Subscription).filter(Subscription.user_id == user_id).all()
    db.close()
    total = sum(s.cost for s in subs)
    return f"Your total subscription cost is {total}"

@tool
def get_expiring_subscriptions(config: RunnableConfig):
    """Get subscriptions expiring today"""
    user_id = config["configurable"].get("user_id")
    db = SessionLocal()
    subs = db.query(Subscription).filter(Subscription.user_id == user_id).all()
    db.close()
    today = date.today()
    expiring = [s.tool_name for s in subs if s.renewal_date <= today]
    return f"Expiring subscriptions: {', '.join(expiring)}" if expiring else "No subscriptions expiring today"

@tool
def get_highest_subscription(config: RunnableConfig):
    """Find most expensive subscription"""
    user_id = config["configurable"].get("user_id")
    db = SessionLocal()
    subs = db.query(Subscription).filter(Subscription.user_id == user_id).all()
    db.close()
    if not subs: return "No subscriptions found"
    highest = max(subs, key=lambda x: x.cost)
    return f"Most expensive is {highest.tool_name} costing {highest.cost}"


@tool
def get_lowest_subscription(config: RunnableConfig):
    """Find cheapest subscription"""
    user_id = config["configurable"].get("user_id")
    db = SessionLocal()
    subs = db.query(Subscription).filter(Subscription.user_id == user_id).all()
    db.close()
    if not subs: return "No subscriptions found"
    lowest = min(subs, key=lambda x: x.cost)
    return f"Cheapest is {lowest.tool_name} costing {lowest.cost}"

@tool
def record_user_preference(preference: str, config: RunnableConfig):
    """Record user preference for personalization"""
    user_id = config["configurable"].get("user_id")
    filename = f"preferences_{user_id}.json"
    data = []
    if os.path.exists(filename):
        with open(filename, "r") as f:
            data = json.load(f)
    data.append(preference)
    with open(filename, "w") as f:
        json.dump(data, f)
    return "Preference recorded"

web_search = TavilySearchResults(max_results=2)

tools = [get_total_cost, get_expiring_subscriptions, get_lowest_subscription, record_user_preference, web_search]
llm_with_tools = llm.bind_tools(tools)

# ---------------- NODES ---------------- #
def assistant(state: State, config: RunnableConfig):
    user_id = config["configurable"].get("user_id")
    
    # Save current query to long-term memory
    last_msg = state["messages"][-1].content
    save_memory(user_id, last_msg)
    
    past_queries = load_memory(user_id)
    system_prompt = SystemMessage(content=(
        "You are an intelligent subscription management assistant. "
        "Always prefer using tools to answer queries about subscriptions, costs, and renewals."
        "Use memory for personalization and context."
        f"Context: The user previously asked about: {', '.join(past_queries[-3:])}"
    ))
    return {"messages": [llm_with_tools.invoke([system_prompt] + state["messages"])]}

def route_tools(state: State):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# ---------------- GRAPH CONSTRUCTION ---------------- #
builder = StateGraph(State)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

builder.set_entry_point("assistant")
builder.add_conditional_edges("assistant", route_tools)
builder.add_edge("tools", "assistant")

# COMPILE AT THE END
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
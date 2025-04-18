# app/agent/state.py

from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class UserProfile(TypedDict, total=False):
    name: str
    timezone: str
    preferences: dict

class State(TypedDict, total=False):
    """
    Holds the running list of messages, the user profile,
    and any extra state keys (like remaining_steps) needed by tools.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    profile: UserProfile
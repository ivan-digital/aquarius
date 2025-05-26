# app/server/models.py
from pydantic import BaseModel
from typing import List, Tuple

class AgentResponse(BaseModel):
    success: bool
    message: str
    history: List[Tuple[str, str]]

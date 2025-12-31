# backend/models/query_schemas.py
from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    
    # NEW ADVANCED OPTIONS
    chunks: Optional[int] = 5                # 1-10
    temperature: Optional[float] = 0.7       # 0.0 - 1.0
    style: Optional[str] = "Detailed"        # Concise, Detailed, Bullet
    document_names: Optional[List[str]] = None  # e.g. ["paper1.pdf"] – specific papers

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str
    history: List[dict]
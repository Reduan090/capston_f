from pydantic import BaseModel
from typing import List

class UploadResponse(BaseModel):
    message: str
    document_count: int
    chunks_added: int
    filenames: List[str]
    
class TopicSuggestion(BaseModel):
    topic: str
    research_question: str
    importance: str
    current_direction: str
    research_gap: str
    confidence_score: int
    status: str
    sources: List[str]
# backend/routers/query.py
from fastapi import APIRouter, HTTPException
from models.query_schemas import QueryRequest, QueryResponse
from vector_db.client import get_collection
from utils.embedding import get_embeddings
from db.database import get_db_connection
import requests
import uuid

router = APIRouter(prefix="/query", tags=["query"])

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"

def query_ollama(prompt: str, temperature: float = 0.7) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    return response.json()["response"]

def get_chat_history(session_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY timestamp", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]

def save_message(session_id: str, role: str, content: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
                   (session_id, role, content))
    conn.commit()
    conn.close()

@router.post("/", response_model=QueryResponse)
async def query_research_bot(request: QueryRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Session handle
    session_id = request.session_id or str(uuid.uuid4())
    save_message(session_id, "user", question)

    # Get previous history
    history = get_chat_history(session_id)
    history_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[:-1]])

    # Advanced options with validation
    chunks = max(1, min(10, request.chunks or 5))
    temperature = max(0.0, min(1.0, request.temperature or 0.7))
    style = (request.style or "Detailed").capitalize()
    if style not in ["Concise", "Detailed", "Bullet"]:
        style = "Detailed"

    # Multi-doc filter
    filter_dict = None
    if request.document_names:
        filter_dict = {"source": {"$in": request.document_names}}

    # Embed and search
    question_embedding = get_embeddings([question])[0]
    collection = get_collection()
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=chunks,
        where=filter_dict,
        include=["documents", "metadatas"]
    )

    contexts = results["documents"][0] if results["documents"] else []
    sources = list(set(meta["source"] for meta in results["metadatas"][0])) if results["metadatas"] else []

    context_str = "\n\n".join(contexts) if contexts else "No relevant documents found."

    # Style instruction
    style_instruction = ""
    if style == "Concise":
        style_instruction = "Be concise and direct. Use short sentences."
    elif style == "Bullet":
        style_instruction = "Answer using clear bullet points."
    else:  # Detailed
        style_instruction = "Provide a detailed, comprehensive answer with explanations."

    # Final prompt
    prompt = f"""You are an expert research assistant. Answer based on the context and previous conversation.

Previous conversation:
{history_context}

Current context:
{context_str}

Instructions:
- {style_instruction}
- Be accurate and helpful.

Question: {question}

Answer:"""

    # Generate answer with temperature
    answer = query_ollama(prompt, temperature)

    # Save and return
    save_message(session_id, "assistant", answer)
    full_history = get_chat_history(session_id)

    return QueryResponse(
        answer=answer,
        sources=sources,
        session_id=session_id,
        history=full_history
    )
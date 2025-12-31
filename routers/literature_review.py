# backend/routers/literature_review.py
from fastapi import APIRouter, HTTPException, Query
from vector_db.client import get_collection
import requests

router = APIRouter(prefix="/literature-review", tags=["literature-review"])

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"

@router.get("/")
def generate_literature_review(
    focus_area: str = Query(None, description="e.g. 'IoT security gaps', 'deep learning performance'"),
    length: str = Query("medium", description="short / medium / long")
):
    collection = get_collection()
    all_data = collection.get(include=["documents", "metadatas"])
    
    if not all_data["documents"]:
        raise HTTPException(status_code=404, detail="No documents uploaded yet. Please upload PDFs first.")
    
    # Group chunks by paper source
    papers = {}
    for doc, meta in zip(all_data["documents"], all_data["metadatas"]):
        source = meta["source"]
        papers.setdefault(source, []).append(doc)
    
    full_texts = {src: "\n\n".join(chunks) for src, chunks in papers.items()}
    
    # Length control
    word_limits = {"short": 500, "medium": 1000, "long": 2000}
    max_words = word_limits.get(length.lower(), 1000)
    
    # Focus instruction
    focus_instruction = f"Focus especially on: {focus_area}. " if focus_area else ""
    
    # Build context
    context_parts = [f"### Paper: {src}\n{text}\n" for src, text in full_texts.items()]
    full_context = "\n".join(context_parts)
    
    # Prompt
    prompt = f"""You are an expert academic reviewer. Write a comprehensive literature review.

Instructions:
- {focus_instruction}
- Summarize key contributions of each paper
- Compare methods, datasets, and results across papers
- Identify common themes, differences, research gaps, and future directions
- Keep the review under approximately {max_words} words
- Use formal academic style with clear sections (e.g. Introduction, Methods Comparison, Key Findings, Gaps & Future Work)

Papers:
{full_context}

Literature Review:"""

    # Call Ollama
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        })
        response.raise_for_status()
        review = response.json()["response"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

    return {
        "review": review,
        "paper_count": len(full_texts),
        "papers": list(full_texts.keys()),
        "focus_area": focus_area or "General",
        "length": length.capitalize()
    }
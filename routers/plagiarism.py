# backend/routers/plagiarism.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import numpy as np
from utils.embedding import get_embeddings
from vector_db.client import get_collection
from sklearn.metrics.pairwise import cosine_similarity
import fitz  # PyMuPDF
import uuid
import re

router = APIRouter(prefix="/plagiarism", tags=["Plagiarism & PDF Upload"])


# ========================= MODELS ========================= #

class PlagiarismRequest(BaseModel):
    text: str
    threshold: float = 0.70   # Sensitivity like Turnitin


class SentenceReport(BaseModel):
    sentence: str
    score: float
    label: str   # copied / partial / original


class PlagiarismResponse(BaseModel):
    originality_score: float
    plagiarism_percent: float
    sentences: list          # highlight UI uses this
    matches: list            # source match preview
    status: str
    heatmap_ready: bool = True   # UI flag indicator


# ========================= HELPERS ========================= #

def split_sentences(text):
    return [s.strip() for s in re.split(r"[.!?]", text) if len(s.strip()) > 10]


def extract_pdf_text(file_bytes):
    try:
        pdf = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in pdf:
            text += page.get_text()
        return text
    except Exception:
        return None


# ========================= 1) PDF UPLOAD ========================= #

@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")

    content = await file.read()
    text = extract_pdf_text(content)

    if not text or len(text) < 50:
        raise HTTPException(500, "PDF text extraction failed or empty.")

    chunks = [text[i:i+1500] for i in range(0, len(text), 1500)]
    embeddings = get_embeddings(chunks)
    collection = get_collection()

    ids = [str(uuid.uuid4()) for _ in chunks]
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"source": file.filename}] * len(chunks),
        ids=ids
    )

    return {
        "status": "success",
        "file": file.filename,
        "chunks_stored": len(chunks),
        "message": "PDF uploaded, processed & indexed successfully."
    }


# ========================= 2) PLAGIARISM CHECK ========================= #

@router.post("/check", response_model=PlagiarismResponse)
def check_plagiarism(req: PlagiarismRequest):

    collection = get_collection()
    db = collection.get(include=["documents", "metadatas"])

    if not db["documents"]:
        raise HTTPException(400, "No papers found in database. Upload PDF first.")

    sentences = split_sentences(req.text)
    input_embeddings = get_embeddings(sentences)
    stored_embeddings = get_embeddings(db["documents"])
    matrix = cosine_similarity(input_embeddings, stored_embeddings)

    reports, matches = [], []
    plag_weight = 0

    for i, sentence in enumerate(sentences):
        score = float(np.max(matrix[i]))
        idx = int(np.argmax(matrix[i]))

        if score >= 0.85:
            label = "copied"; plag_weight += 1
        elif score >= 0.65:
            label = "partial"; plag_weight += 0.5
        else:
            label = "original"

        reports.append({
            "sentence": sentence,
            "score": round(score, 3),
            "label": label
        })

        if score > req.threshold:
            matches.append({
                "source": db["metadatas"][idx].get("source", "Unknown"),
                "similarity": round(score, 3),
                "matched_text": db["documents"][idx][:250]
            })

    plagiarism_percent = round((plag_weight / len(sentences)) * 100, 2)
    originality = 100 - plagiarism_percent

    return PlagiarismResponse(
        originality_score=originality,
        plagiarism_percent=plagiarism_percent,
        sentences=reports,
        matches=matches[:10],
        status="High Plagiarism ❌" if plagiarism_percent > 35 else "Mostly Original ✓",
        heatmap_ready=True
    )

# backend/routers/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import List
import os
import shutil

from utils.pdf_parser import extract_text_from_pdf
from utils.chunking import chunk_text
from utils.embedding import get_embeddings
from vector_db.client import get_collection
from models.schemas import UploadResponse

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_FOLDER = "uploaded_pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.post("/", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdfs(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    saved_filenames = []
    total_chunks = 0
    collection = get_collection()

    for file in files:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail=f"Only PDF allowed: {file.filename}")

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_filenames.append(file.filename)

        text = extract_text_from_pdf(file_path)
        if not text:
            os.remove(file_path)
            continue

        chunks = chunk_text(text)
        total_chunks += len(chunks)

        embeddings = get_embeddings(chunks)

        ids = [f"{file.filename}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"source": file.filename, "chunk_index": i} for i in range(len(chunks))]

        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

        # Optional: temp file delete
        # os.remove(file_path)

    return UploadResponse(
        message="Documents processed and added to vector DB successfully!",
        document_count=len(saved_filenames),
        chunks_added=total_chunks,
        filenames=saved_filenames
    )
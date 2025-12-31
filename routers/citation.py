# backend/routers/citation.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import requests, json, re
from db.database import get_db_connection

router = APIRouter(prefix="/citation", tags=["citation"])

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"

# --------------------------------------------------------
# Base Request Models
# --------------------------------------------------------
class CitationRequest(BaseModel):
    text: str                     # input extracted citation details
    save_to_db: Optional[bool] = False


class CitationResponse(BaseModel):
    APA: str
    MLA: str
    IEEE: str
    Chicago: str
    Harvard: str
    Vancouver: str
    Springer: str
    BibTeX: str

# --------------------------------------------------------
# LLM Caller
# --------------------------------------------------------
def call_llm(prompt: str) -> str:
    try:
        res = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        })
        res.raise_for_status()
        return res.json()["response"].strip()
    except Exception as e:
        raise HTTPException(500, f"LLM ERROR: {e}")

# --------------------------------------------------------
# (A) AUTO FETCH DOI / CROSSREF / ARXIV
# --------------------------------------------------------
@router.get("/fetch")
def fetch_metadata(query: str):
    if query.startswith("10."):     # DOI
        url = f"https://api.crossref.org/works/{query}"
    elif "arxiv" in query.lower():
        url = f"https://export.arxiv.org/api/query?id_list={query.split('/')[-1]}"
    else:
        return {"error": "Provide valid DOI or ArXiv ID"}

    try:
        r = requests.get(url).json()
        data = r.get("message", {})

        return {
            "title": data.get("title", [""])[0],
            "authors": [f"{a.get('given','')} {a.get('family','')}" for a in data.get("author", [])],
            "year": data.get("issued", {}).get("date-parts", [[None]])[0][0],
            "journal": data.get("container-title", [""])[0],
            "volume": data.get("volume"),
            "issue": data.get("issue"),
            "pages": data.get("page"),
            "doi": data.get("DOI"),
            "publisher": data.get("publisher")
        }

    except:
        return {"error": "Metadata not found or invalid query"}

# --------------------------------------------------------
# (B) Multi-Style Citation Generation
# --------------------------------------------------------
@router.post("/generate", response_model=CitationResponse)
def generate_citation(req: CitationRequest):

    prompt = f"""
Generate citation in 8 formats from given reference details.
Return only JSON strictly in format below.

Input:
{req.text}

Output JSON:
{{
 "APA": "...",
 "MLA": "...",
 "IEEE": "...",
 "Chicago": "...",
 "Harvard": "...",
 "Vancouver": "...",
 "Springer": "...",
 "BibTeX": "..."
}}
"""

    raw = call_llm(prompt)

    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(match.group(0)) if match else None
    except:
        data = None

    if not data:
        raise HTTPException(500, "Formatting failed. Model returned invalid JSON.")

    # --- Save to DB optional ---
    if req.save_to_db:
        save_to_library(data)

    return data


# --------------------------------------------------------
# Save to Local DB
# --------------------------------------------------------
def save_to_library(formats: dict):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS citation_library(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        apa TEXT,
        mla TEXT,
        ieee TEXT,
        chicago TEXT,
        harvard TEXT,
        vancouver TEXT,
        springer TEXT,
        bibtex TEXT,
        saved_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""
        INSERT INTO citation_library 
        (apa, mla, ieee, chicago, harvard, vancouver, springer, bibtex)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        formats["APA"], formats["MLA"], formats["IEEE"], formats["Chicago"],
        formats["Harvard"], formats["Vancouver"], formats["Springer"], formats["BibTeX"]
    ))

    conn.commit()
    conn.close()


# --------------------------------------------------------
# Get Saved Citations
# --------------------------------------------------------
@router.get("/library")
def get_library():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM citation_library ORDER BY saved_at DESC")
    rows = cur.fetchall()
    conn.close()

    return {"saved_items": [dict(row) for row in rows]}

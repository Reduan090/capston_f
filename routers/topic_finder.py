# backend/routers/topic_finder.py
from fastapi import APIRouter, HTTPException, Query
from vector_db.client import get_collection
import requests
from typing import List, Dict
from pydantic import BaseModel
import xml.etree.ElementTree as ET
import re, json
from collections import Counter

router = APIRouter(prefix="/topic-finder", tags=["topic-finder"])

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"

ARXIV_CATEGORIES = {
    "Computer Science": "cs",
    "AI/ML": "cs.LG",
    "Medicine & Health": "q-bio",
    "Physics": "physics",
    "Mathematics": "math",
    "Engineering": "eess"  # fallback category
}

# ---------- Response Schemas ----------
class TopicSuggestion(BaseModel):
    topic: str
    research_question: str
    importance: str
    current_direction: str
    research_gap: str
    confidence_score: int
    status: str
    sources: List[str]

class TopicFinderResponse(BaseModel):
    topics: List[TopicSuggestion]
    trend_chart_config: Dict
    word_cloud_data: Dict
    paper_count: int
    message: str = "Topics generated from uploaded documents"


# ---------- Route ----------
@router.get("/", response_model=TopicFinderResponse)
def topic_finder(
    domain: str = Query(...),
    time_period: str = Query("Last 1 Year"),
    num_topics: int = Query(5, ge=3, le=10),
    use_uploaded_docs: bool = Query(True)
):
    # Time filter mapping
    time_filters = {
        "Last 1 Year": "since:2024-01-01",
        "Last 5 Years": "since:2020-01-01",
        "Last 10 Years": "since:2015-01-01"
    }
    time_filter = time_filters.get(time_period)

    # ================== FETCH TRENDS ==================
    trend_data = ""
    year_counts = Counter()

    try:
        cat = ARXIV_CATEGORIES.get(domain, "cs")
        arxiv_url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending"
        
        xml_raw = requests.get(arxiv_url, timeout=10).text
        root = ET.fromstring(xml_raw)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        papers = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns).text
            link = entry.find("atom:id", ns).text
            year = entry.find("atom:published", ns).text[:4]
            year_counts[year] += 1
            papers.append(f"{title} | {link}")

        trend_data = "\n".join(papers[:20])

    except Exception as e:
        trend_data = f"No trend data found. Error: {e}"

    # ================== UPLOADED DOCUMENTS PROCESSING ==================
    uploaded_context = ""
    paper_count = 0
    word_freq = Counter()

    if use_uploaded_docs:
        coll = get_collection().get(include=["documents", "metadatas"])
        if coll["documents"]:
            paper_count = len(coll["documents"])
            text = " ".join(coll["documents"]).lower()
            uploaded_context = text[:5000]  # prevent token overload

            for word in re.findall(r'\b[a-zA-Z]{4,}\b', text):
                if word not in {"this","that","with","from","have","been","were","which"}:
                    word_freq[word] += 1

    # ================== LLM PROMPT ==================
    prompt = f"""
Generate {num_topics} academic research topics in {domain}. 
Use trend data and uploaded documents to identify research gaps.

Trends:
{trend_data}

User documents:
{uploaded_context}

Return JSON only with:
topic, research_question, importance, current_direction, research_gap, confidence_score,
status (Emerging/Well-established/High-risk), sources (2-3 links)
"""

    try:
        res = requests.post(OLLAMA_URL, json={"model": MODEL_NAME,"prompt": prompt,"stream":False}).json()
        data = re.search(r'\[.*\]', res["response"], re.DOTALL).group(0)
        topics = json.loads(data)

    except Exception as e:
        raise HTTPException(500, f"LLM Output parsing failed → {e}")

    # Trend chart generation
    trend_chart = {
        "labels": list(year_counts.keys()),
        "data": list(year_counts.values())
    }

    # Word cloud
    word_cloud = {"words":[{"text": w, "value": c} for w,c in word_freq.most_common(50)]}

    return TopicFinderResponse(
        topics=topics,
        trend_chart_config=trend_chart,
        word_cloud_data=word_cloud,
        paper_count=paper_count
    )

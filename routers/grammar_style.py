# backend/routers/grammar_style.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from typing import Optional
import textstat
import re, json

# ====================== SESSION MEMORY FOR CHAT ====================== #
chat_sessions = {}  


router = APIRouter(prefix="/grammar-style", tags=["grammar-style"])

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"


# ===================================================================== #
# Base Schema
# ===================================================================== #
class TextRequest(BaseModel):
    text: str
    style: Optional[str] = "academic"
    session_id: Optional[str] = "default"   # <--- added for auto chat save


# ===================================================================== #
# LLM Call Function
# ===================================================================== #
def call_llm(prompt: str) -> str:
    try:
        res = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.35}
        })
        res.raise_for_status()
        return res.json()["response"].strip()
    except Exception as e:
        raise HTTPException(500, f"LLM ERROR: {e}")


# ===================================================================== #
# Helper → Save result directly to chat memory
# ===================================================================== #
def save_to_chat(session_id, text, role="assistant"):
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    chat_sessions[session_id].append({role: text})


def get_history(session_id):
    history = ""
    for msg in chat_sessions.get(session_id, []):
        if "user" in msg: history += f"User: {msg['user']}\n"
        if "assistant" in msg: history += f"Assistant: {msg['assistant']}\n"
    return history


# ===================================================================== #
# 1. Grammar Check
# ===================================================================== #
@router.post("/check")
def grammar_check(req: TextRequest):

    prompt = f"""
You are a research-grade academic writing editor.
Correct grammar, fix structure, improve readability.

Return format:

**Corrected Version**
...

**Issues Fixed**
- bullet list

**Suggestions**
- bullet list

Text:
\"\"\"{req.text}\"\"\"
"""

    result = call_llm(prompt)

    # store for chat continuation
    save_to_chat(req.session_id, result)

    try:
        readability = textstat.flesch_reading_ease(req.text)
    except:
        readability = "N/A"

    return {
        "corrected_text": result,
        "readability_score": readability,
        "note": "70+ easy, 30-50 academic level"
    }


# ===================================================================== #
# 2. Paraphrase
# ===================================================================== #
@router.post("/paraphrase")
def paraphrase(req: TextRequest):

    tone_map = {
        "academic": "Rewrite formally using academic vocabulary.",
        "simple": "Rewrite using easy everyday language.",
        "technical": "Rewrite using expert technical terminology.",
        "concise": "Rewrite shorter & direct without losing meaning."
    }

    tone = tone_map.get(req.style.lower(), tone_map["academic"])

    prompt = f"""
Paraphrase text in style: {tone}

Text:
\"\"\"{req.text}\"\"\"

Return ONLY paraphrased final output.
"""

    result = call_llm(prompt)

    # 🔥 auto save for chat continuation
    save_to_chat(req.session_id, result)

    return {"style": req.style, "paraphrased": result}


# ===================================================================== #
# 3. Refine/Improve
# ===================================================================== #
@router.post("/refine")
def refine(req: TextRequest):
    prompt = f"""
Improve writing quality & clarity.

Text:
\"\"\"{req.text}\"\"\"

Return improved text only.
"""
    result = call_llm(prompt)
    save_to_chat(req.session_id, result)
    return {"refined": result}


# ===================================================================== #
# 4. Translate
# ===================================================================== #
@router.post("/translate")
def translate(req: TextRequest):
    prompt = f"""
Rewrite text in 3 different academic styles:

Text:
\"\"\"{req.text}\"\"\"

Return strict JSON only:
{{"formal":"...","concise":"...","detailed":"..."}}
"""
    raw = call_llm(prompt)

    try:
        matched = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(matched.group(0)) if matched else {"raw": raw}
    except:
        data = {"raw": raw}

    # Save each version for chat request
    save_to_chat(req.session_id, str(data))
    return data


# ===================================================================== #
# 5. Live Chat (FINAL FIXED)
# ===================================================================== #
class ChatRequest(BaseModel):
    session_id: str
    message: str

@router.post("/chat")
def grammar_chat(req: ChatRequest):

    # save user msg
    save_to_chat(req.session_id, req.message, role="user")

    prompt = f"""
You are a writing assistant. Improve text based on conversation.
If user says "more detailed/shorter/better summary",
modify previous assistant answer intelligently.

Conversation:
{get_history(req.session_id)}

Reply now:
"""

    reply = call_llm(prompt)

    save_to_chat(req.session_id, reply, role="assistant")

    return {"reply": reply, "session_id": req.session_id}

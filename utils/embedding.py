# backend/utils/embedding.py
import os
import time
from typing import List

import requests

# Ollama local server – default port 11434
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")


def _embed_one(text: str, session: requests.Session, timeout_s: float, retries: int) -> List[float]:
    payload = {"model": OLLAMA_EMBED_MODEL, "prompt": text}
    last_exc: Exception | None = None

    for attempt in range(retries + 1):
        try:
            resp = session.post(f"{OLLAMA_BASE_URL}/api/embeddings", json=payload, timeout=timeout_s)
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]
        except requests.exceptions.ConnectionError as e:
            # No point retrying if Ollama isn't reachable.
            raise Exception("Ollama not running! Run 'ollama serve' in terminal.") from e
        except requests.HTTPError as e:
            # Retry on 5xx (Ollama can 500 on transient OOM/overload).
            status_code = getattr(e.response, "status_code", None)
            if status_code is not None and 500 <= status_code < 600 and attempt < retries:
                time.sleep(0.25 * (2**attempt))
                last_exc = e
                continue
            raise
        except Exception as e:
            last_exc = e
            if attempt < retries:
                time.sleep(0.25 * (2**attempt))
                continue
            break

    raise last_exc or Exception("Unknown embedding error")


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using Ollama's embedding model.

    Notes:
    - We intentionally embed per text to avoid sending one giant prompt (common cause of 500s).
    """
    if isinstance(texts, str):
        texts = [texts]

    texts = [t for t in texts if t is not None and str(t).strip() != ""]
    if not texts:
        return []

    timeout_s = float(os.getenv("OLLAMA_EMBED_TIMEOUT_S", "120"))
    retries = int(os.getenv("OLLAMA_EMBED_RETRIES", "2"))

    try:
        with requests.Session() as session:
            return [_embed_one(text, session=session, timeout_s=timeout_s, retries=retries) for text in texts]
    except Exception as e:
        raise Exception(f"Embedding error: {str(e)}")
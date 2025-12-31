# backend/utils/chunking.py
import tiktoken

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    chunks = []
    i = 0
    while i < len(tokens):
        chunk = tokens[i:i + chunk_size]
        chunk_text = encoding.decode(chunk)
        chunks.append(chunk_text)
        i += chunk_size - chunk_overlap
    return chunks
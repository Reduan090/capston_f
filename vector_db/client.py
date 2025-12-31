# backend/vector_db/client.py
import chromadb
from chromadb.config import Settings
import os

# Persistent directory – data server restart holeo thakbe
CHROMA_DATA_PATH = "chroma_db"
COLLECTION_NAME = "research_documents"

# Create directory if not exists
os.makedirs(CHROMA_DATA_PATH, exist_ok=True)

# Chroma client (persistent)
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

def get_collection():
    """Get or create the Chroma collection"""
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}  # cosine similarity better for text
        )
    return collection
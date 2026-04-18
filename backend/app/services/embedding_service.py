import os
import numpy as np
import faiss
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.database import chunks_collection
from app.config import settings

EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 3072  # dimension for Gemini models/gemini-embedding-001


def _safe_log(message: str) -> None:
    try:
        print(message)
    except Exception:
        pass

embedding_service = GoogleGenerativeAIEmbeddings(
    model=EMBEDDING_MODEL,
    google_api_key=settings.GEMINI_API_KEY
)

def get_embedding(text: str) -> list[float]:
    """Get Google GenAI embedding vector for a single text string."""
    return embedding_service.embed_query(text)


def index_chunks(file_id: str, chunks: list[dict]):
    """
    Embed all chunks and store them in a FAISS per-file index.
    Also persists each chunk with its embedding_id to MongoDB.
    """
    if not chunks:
        _safe_log(f"Warning: No chunks to index for file_id={file_id}")
        return

    _safe_log(f"Embedding {len(chunks)} chunks for file_id={file_id}...")
    embeddings = [get_embedding(c["text"]) for c in chunks]

    # Build FAISS index
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    vectors = np.array(embeddings, dtype="float32")
    index.add(vectors)

    # Persist FAISS index to disk
    os.makedirs(settings.FAISS_DIR, exist_ok=True)
    index_path = os.path.join(settings.FAISS_DIR, f"{file_id}.index")
    faiss.write_index(index, index_path)
    _safe_log(f"FAISS index saved -> {index_path}")

    # Persist chunks to MongoDB with embedding_id (= position in FAISS)
    for i, chunk in enumerate(chunks):
        chunks_collection.insert_one(
            {
                "file_id": file_id,
                "text": chunk["text"],
                "start_time": chunk.get("start_time"),
                "end_time": chunk.get("end_time"),
                "chunk_index": chunk["chunk_index"],
                "embedding_id": i,
            }
        )
    _safe_log(f"Success: {len(chunks)} chunks stored in MongoDB for file_id={file_id}")


def search(file_id: str, query: str, top_k: int = 4) -> list[dict]:
    """
    Embed the query and search the file's FAISS index.
    Returns top_k most relevant chunks from MongoDB.
    """
    index_path = os.path.join(settings.FAISS_DIR, f"{file_id}.index")
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"FAISS index not found for file_id={file_id}")

    index = faiss.read_index(index_path)
    q_vec = np.array([get_embedding(query)], dtype="float32")
    _, ids = index.search(q_vec, top_k)

    results = []
    for idx in ids[0]:
        if idx == -1:
            continue  # FAISS returns -1 for empty slots
        chunk = chunks_collection.find_one(
            {"file_id": file_id, "embedding_id": int(idx)},
            {"_id": 0},  # exclude Mongo ObjectId from result
        )
        if chunk:
            results.append(chunk)
    return results

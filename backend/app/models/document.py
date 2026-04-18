from typing import Optional
from datetime import datetime
from pydantic import BaseModel


# ── Stored in MongoDB: documents collection ──
class DocumentMeta(BaseModel):
    file_id: str
    original_filename: str
    processed_filename: str   # UUID-based safe name e.g. "abc123.mp4"
    file_type: str            # "pdf" | "audio" | "video"
    file_path: str
    media_url: str            # Static URL frontend can use to stream file
    status: str = "processing"   # processing | ready | error
    created_at: datetime = datetime.utcnow()


# ── Stored in MongoDB: chunks collection ──
class ChunkMeta(BaseModel):
    file_id: str
    text: str
    start_time: Optional[float] = None   # seconds (audio/video only)
    end_time: Optional[float] = None
    chunk_index: int
    embedding_id: int          # Position in FAISS index


# ── Request / Response schemas ──
class AskRequest(BaseModel):
    file_id: str
    question: str


class SummaryRequest(BaseModel):
    file_id: str


class UploadResponse(BaseModel):
    file_id: str
    original_filename: str
    file_type: str
    status: str
    message: str


class AskResponse(BaseModel):
    answer: str
    timestamp: Optional[float] = None   # seconds to seek to
    file_type: str
    media_url: Optional[str] = None     # frontend uses this for the player
    sources: list

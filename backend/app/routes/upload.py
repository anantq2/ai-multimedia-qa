import uuid
import os
import shutil
import traceback

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Depends

from app.database import documents_collection
from app.services import pdf_service, whisper_service, embedding_service
from app.services.auth_service import get_current_user
from app.config import settings

router = APIRouter()


def _safe_log(message: str) -> None:
    try:
        print(message)
    except Exception:
        pass

# Allowed MIME types and their category
ALLOWED_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "audio/mpeg": "audio",
    "audio/wav": "audio",
    "audio/x-wav": "audio",
    "audio/ogg": "audio",
    "video/mp4": "video",
    "video/webm": "video",
    "video/quicktime": "video",
}


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a file for processing. Requires JWT auth."""
    # ── Validation ──────────────────────────────────────────────────────────
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed: PDF, MP3, WAV, OGG, MP4, WEBM, MOV",
        )

    # ── UUID-based rename (pro touch) ───────────────────────────────────────
    file_id = str(uuid.uuid4())
    ext = (file.filename or "file").rsplit(".", 1)[-1].lower()
    safe_filename = f"{file_id}.{ext}"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    # ── Chunked write (no RAM overflow) ────────────────────────────────────
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_type = ALLOWED_TYPES[file.content_type]
    # URL the frontend media player can use to stream/play the file
    media_url = f"/media/{safe_filename}"

    # ── Persist metadata to MongoDB ─────────────────────────────────────────
    doc = {
        "file_id": file_id,
        "original_filename": file.filename,
        "processed_filename": safe_filename,
        "file_type": file_type,
        "file_path": save_path,
        "media_url": media_url,
        "status": "processing",
        "uploaded_by": user.get("username", "anonymous"),
    }
    documents_collection.insert_one(doc)

    # ── Kick off extraction + embedding in the background ──────────────────
    background_tasks.add_task(_process_file, file_id, save_path, file_type)

    return {
        "file_id": file_id,
        "original_filename": file.filename,
        "file_type": file_type,
        "status": "processing",
        "message": "File uploaded successfully. Processing started in background.",
    }


@router.get("/status/{file_id}")
async def get_status(file_id: str):
    """Poll this endpoint to check if file processing is done. (No auth required for polling)"""
    doc = documents_collection.find_one({"file_id": file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "file_id": file_id,
        "status": doc["status"],
        "file_type": doc["file_type"],
        "error": doc.get("error"),
    }


# ── Background Task ────────────────────────────────────────────────────────
def _process_file(file_id: str, path: str, file_type: str):
    """Extract text / transcribe → chunk → embed → index."""
    try:
        if file_type == "pdf":
            chunks = pdf_service.extract_chunks(path)
        else:
            # Audio and video both go through Whisper
            chunks = whisper_service.transcribe(path)

        embedding_service.index_chunks(file_id, chunks)

        documents_collection.update_one(
            {"file_id": file_id}, {"$set": {"status": "ready"}}
        )
        _safe_log(f"Success: File {file_id} is ready.")
    except Exception as e:
        documents_collection.update_one(
            {"file_id": file_id}, {"$set": {"status": "error", "error": str(e)}}
        )
        try:
            traceback.print_exc()
        except Exception:
            pass
        _safe_log(f"Error: Processing failed for {file_id}: {repr(e)}")

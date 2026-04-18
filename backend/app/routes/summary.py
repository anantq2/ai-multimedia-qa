from fastapi import APIRouter, HTTPException, Depends
from app.models.document import SummaryRequest
from app.database import documents_collection, chunks_collection
from app.services.summary_service import summarize
from app.services.auth_service import get_current_user
from app.services.redis_service import cache_get, cache_set

router = APIRouter()


@router.post("/summary")
async def get_summary(request: SummaryRequest, user: dict = Depends(get_current_user)):
    """
    Generate AI summary of an uploaded file.
    Results are cached in Redis for 10 minutes to avoid redundant LLM calls.
    Requires JWT auth.
    """
    # ── Check Redis cache first ────────────────────────────────────────────
    cache_key = f"summary:{request.file_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # ── Validate ────────────────────────────────────────────────────────────
    doc = documents_collection.find_one({"file_id": request.file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    if doc["status"] != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"File is not ready yet. Current status: {doc['status']}",
        )

    # ── Fetch all chunks and join text ─────────────────────────────────────
    chunks = list(
        chunks_collection.find(
            {"file_id": request.file_id},
            {"_id": 0, "text": 1, "chunk_index": 1}
        ).sort("chunk_index", 1)
    )
    if not chunks:
        raise HTTPException(status_code=404, detail="No content found for this file")

    full_text = " ".join([c["text"] for c in chunks])

    # ── Summarize via LLM ───────────────────────────────────────────────────
    summary = summarize(full_text)

    result = {
        "file_id": request.file_id,
        "original_filename": doc.get("original_filename"),
        "file_type": doc["file_type"],
        "summary": summary,
    }

    # ── Cache the result for 10 minutes ────────────────────────────────────
    cache_set(cache_key, result, ttl_seconds=600)

    return result

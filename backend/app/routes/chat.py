import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.models.document import AskRequest
from app.database import documents_collection
from app.services import embedding_service, llm_service
from app.services.auth_service import get_current_user

router = APIRouter()


# ── Helper: validate file and get relevant chunks ─────────────────────────
def _validate_and_search(file_id: str, question: str):
    """Shared logic for /ask and /ask-stream."""
    doc = documents_collection.find_one({"file_id": file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    if doc["status"] != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"File is not ready yet. Current status: {doc['status']}",
        )
    relevant_chunks = embedding_service.search(file_id, question)
    return doc, relevant_chunks


@router.post("/ask")
async def ask(request: AskRequest, user: dict = Depends(get_current_user)):
    """Standard Q&A — returns full answer at once. Requires JWT auth."""
    doc, relevant_chunks = _validate_and_search(request.file_id, request.question)

    if not relevant_chunks:
        return {
            "answer": "I couldn't find relevant information in the uploaded file.",
            "timestamp": None,
            "file_type": doc["file_type"],
            "media_url": doc.get("media_url"),
            "sources": [],
        }

    # ── LLM answer ─────────────────────────────────────────────────────────
    answer_text = llm_service.answer(request.question, relevant_chunks)

    # ── Timestamp (for audio/video Play button) ────────────────────────────
    timestamp = None
    if doc["file_type"] in ("audio", "video"):
        timestamp = relevant_chunks[0].get("start_time")

    return {
        "answer": answer_text,
        "timestamp": timestamp,
        "file_type": doc["file_type"],
        "media_url": doc.get("media_url"),
        "sources": [
            {
                "text": c["text"][:300],
                "start_time": c.get("start_time"),
                "end_time": c.get("end_time"),
            }
            for c in relevant_chunks
        ],
    }


@router.post("/ask-stream")
async def ask_stream(request: AskRequest, user: dict = Depends(get_current_user)):
    """
    Real-time streaming Q&A using Server-Sent Events (SSE).
    Sends tokens as they arrive from the LLM, then a final metadata event.
    Requires JWT auth.
    """
    doc, relevant_chunks = _validate_and_search(request.file_id, request.question)

    if not relevant_chunks:
        # Even for "no results", stream the message via SSE for consistency
        async def empty_stream():
            msg = "I couldn't find relevant information in the uploaded file."
            yield f"data: {json.dumps({'type': 'token', 'content': msg})}\n\n"
            meta = {
                "type": "done",
                "timestamp": None,
                "file_type": doc["file_type"],
                "media_url": doc.get("media_url"),
                "sources": [],
            }
            yield f"data: {json.dumps(meta)}\n\n"

        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    # ── Timestamp (for audio/video Play button) ────────────────────────────
    timestamp = None
    if doc["file_type"] in ("audio", "video"):
        timestamp = relevant_chunks[0].get("start_time")

    async def event_generator():
        """Yield SSE events: token chunks → final 'done' event with metadata."""
        async for token in llm_service.answer_stream(request.question, relevant_chunks):
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        # Final event with metadata
        meta = {
            "type": "done",
            "timestamp": timestamp,
            "file_type": doc["file_type"],
            "media_url": doc.get("media_url"),
            "sources": [
                {
                    "text": c["text"][:300],
                    "start_time": c.get("start_time"),
                    "end_time": c.get("end_time"),
                }
                for c in relevant_chunks
            ],
        }
        yield f"data: {json.dumps(meta)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
        },
    )

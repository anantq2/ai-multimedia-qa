import whisper

# Load once at module level (avoids reloading on every request)
# Use "base" for speed during demo. Switch to "small" or "medium" for accuracy.
_model = None


def _get_model():
    global _model
    if _model is None:
        print("Loading Whisper model (first time only)...")
        _model = whisper.load_model("base")
        print("Whisper model loaded.")
    return _model


def transcribe(file_path: str, chunk_duration_sec: int = 30) -> list[dict]:
    """
    Transcribe audio or video file using Whisper.
    Returns timestamp-aware chunks:
    [{"text": "...", "start_time": 10.2, "end_time": 40.5, "chunk_index": 0}, ...]

    chunk_duration_sec: How many seconds to group into a single chunk.
    """
    model = _get_model()
    result = model.transcribe(file_path, verbose=False)
    segments = result.get("segments", [])

    chunks = []
    buffer_text = ""
    buffer_start = None
    buffer_end = None

    for seg in segments:
        if buffer_start is None:
            buffer_start = seg["start"]

        buffer_text += " " + seg["text"]
        buffer_end = seg["end"]

        # Flush chunk when duration exceeds threshold
        if (buffer_end - buffer_start) >= chunk_duration_sec:
            chunks.append(
                {
                    "text": buffer_text.strip(),
                    "start_time": round(buffer_start, 2),
                    "end_time": round(buffer_end, 2),
                    "chunk_index": len(chunks),
                }
            )
            buffer_text = ""
            buffer_start = None
            buffer_end = None

    # Flush any remaining text that didn't fill a full chunk
    if buffer_text.strip():
        chunks.append(
            {
                "text": buffer_text.strip(),
                "start_time": round(buffer_start, 2) if buffer_start else 0,
                "end_time": round(buffer_end, 2) if buffer_end else 0,
                "chunk_index": len(chunks),
            }
        )

    return chunks

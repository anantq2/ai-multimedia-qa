import fitz  # PyMuPDF


def extract_chunks(file_path: str, chunk_size: int = 500) -> list[dict]:
    """
    Extract text from PDF and split into word-based chunks.
    Returns list of dicts with keys: text, start_time, end_time, chunk_index.
    (start_time / end_time are None for PDFs — only meaningful for audio/video)
    """
    doc = fitz.open(file_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()

    words = full_text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk_text = " ".join(words[i : i + chunk_size])
        if chunk_text.strip():  # skip empty chunks
            chunks.append(
                {
                    "text": chunk_text,
                    "start_time": None,
                    "end_time": None,
                    "chunk_index": len(chunks),
                }
            )
    return chunks

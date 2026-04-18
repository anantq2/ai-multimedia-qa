"""tests/test_chat_routes.py — /api/ask and /api/ask-stream."""
import json
import pytest
from unittest.mock import patch

MOCK_CHUNKS = [
    {"text": "The sun is a star.", "start_time": None, "end_time": None, "chunk_index": 0, "embedding_id": 0},
]
MOCK_AUDIO_CHUNKS = [
    {"text": "Intro audio.", "start_time": 5.5, "end_time": 35.5, "chunk_index": 0, "embedding_id": 0},
]
MOCK_ANSWER = "The sun is indeed a star at the center of our solar system."


# ── /api/ask ─────────────────────────────────────────────────────────────────

class TestAsk:
    def test_ask_pdf_success(self, client, auth_headers, pdf_doc, pdf_chunks):
        with patch("app.routes.chat.embedding_service.search", return_value=MOCK_CHUNKS), \
             patch("app.routes.chat.llm_service.answer", return_value=MOCK_ANSWER):
            response = client.post("/api/ask", json={
                "file_id": "pdf-001", "question": "What is the sun?"
            }, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == MOCK_ANSWER
        assert data["timestamp"] is None          # PDF — no timestamp
        assert data["file_type"] == "pdf"
        assert isinstance(data["sources"], list)

    def test_ask_audio_returns_timestamp(self, client, auth_headers, audio_doc, audio_chunks):
        with patch("app.routes.chat.embedding_service.search", return_value=MOCK_AUDIO_CHUNKS), \
             patch("app.routes.chat.llm_service.answer", return_value=MOCK_ANSWER):
            response = client.post("/api/ask", json={
                "file_id": "audio-002", "question": "What is the intro?"
            }, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["timestamp"] == 5.5
        assert data["file_type"] == "audio"
        assert data["media_url"] is not None

    def test_ask_no_relevant_chunks(self, client, auth_headers, pdf_doc):
        with patch("app.routes.chat.embedding_service.search", return_value=[]):
            response = client.post("/api/ask", json={
                "file_id": "pdf-001", "question": "Something unrelated?"
            }, headers=auth_headers)

        assert response.status_code == 200
        assert "couldn't find" in response.json()["answer"].lower()

    def test_ask_file_not_found(self, client, auth_headers):
        response = client.post("/api/ask", json={
            "file_id": "does-not-exist", "question": "Any question?"
        }, headers=auth_headers)
        assert response.status_code == 404

    def test_ask_file_not_ready(self, client, auth_headers, processing_doc):
        response = client.post("/api/ask", json={
            "file_id": "proc-003", "question": "Any question?"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "not ready" in response.json()["detail"].lower()

    def test_ask_requires_auth(self, client, pdf_doc):
        response = client.post("/api/ask", json={
            "file_id": "pdf-001", "question": "Any question?"
        })
        assert response.status_code == 403

    def test_ask_sources_truncated_to_300_chars(self, client, auth_headers, pdf_doc):
        long_chunk = [{"text": "A" * 500, "start_time": None, "end_time": None, "chunk_index": 0}]
        with patch("app.routes.chat.embedding_service.search", return_value=long_chunk), \
             patch("app.routes.chat.llm_service.answer", return_value="Answer"):
            response = client.post("/api/ask", json={
                "file_id": "pdf-001", "question": "What?"
            }, headers=auth_headers)

        sources = response.json()["sources"]
        assert len(sources[0]["text"]) <= 300


# ── /api/ask-stream ───────────────────────────────────────────────────────────

class TestAskStream:
    def _parse_sse(self, text):
        """Parse SSE response body into a list of data objects."""
        events = []
        for line in text.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        return events

    async def _mock_stream(*args, **kwargs):
        yield "Token1 "
        yield "Token2"

    def test_ask_stream_pdf_success(self, client, auth_headers, pdf_doc, pdf_chunks):
        async def gen(*a, **kw):
            yield "Hello "
            yield "world"

        with patch("app.routes.chat.embedding_service.search", return_value=MOCK_CHUNKS), \
             patch("app.routes.chat.llm_service.answer_stream", return_value=gen()):
            response = client.post("/api/ask-stream", json={
                "file_id": "pdf-001", "question": "What is the sun?"
            }, headers=auth_headers)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        token_events = [e for e in events if e["type"] == "token"]
        done_events  = [e for e in events if e["type"] == "done"]
        assert len(token_events) >= 1
        assert len(done_events)  == 1
        assert done_events[0]["file_type"] == "pdf"

    def test_ask_stream_audio_timestamp(self, client, auth_headers, audio_doc, audio_chunks):
        async def gen(*a, **kw):
            yield "Audio answer"

        with patch("app.routes.chat.embedding_service.search", return_value=MOCK_AUDIO_CHUNKS), \
             patch("app.routes.chat.llm_service.answer_stream", return_value=gen()):
            response = client.post("/api/ask-stream", json={
                "file_id": "audio-002", "question": "What is the intro?"
            }, headers=auth_headers)

        events = self._parse_sse(response.text)
        done  = next(e for e in events if e["type"] == "done")
        assert done["timestamp"] == 5.5

    def test_ask_stream_no_chunks_returns_fallback(self, client, auth_headers, pdf_doc):
        with patch("app.routes.chat.embedding_service.search", return_value=[]):
            response = client.post("/api/ask-stream", json={
                "file_id": "pdf-001", "question": "Something?"
            }, headers=auth_headers)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        token_events = [e for e in events if e["type"] == "token"]
        assert any("couldn't find" in e["content"].lower() for e in token_events)

    def test_ask_stream_file_not_found(self, client, auth_headers):
        response = client.post("/api/ask-stream", json={
            "file_id": "ghost", "question": "?"
        }, headers=auth_headers)
        assert response.status_code == 404

    def test_ask_stream_file_not_ready(self, client, auth_headers, processing_doc):
        response = client.post("/api/ask-stream", json={
            "file_id": "proc-003", "question": "?"
        }, headers=auth_headers)
        assert response.status_code == 400

    def test_ask_stream_requires_auth(self, client, pdf_doc):
        response = client.post("/api/ask-stream", json={
            "file_id": "pdf-001", "question": "?"
        })
        assert response.status_code == 403

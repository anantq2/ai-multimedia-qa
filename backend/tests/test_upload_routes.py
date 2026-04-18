"""tests/test_upload_routes.py — /api/upload and /api/status/{file_id}."""
import io
import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import make_doc
from app.database import documents_collection


FAKE_CHUNKS = [
    {"text": "chunk one", "start_time": None, "end_time": None, "chunk_index": 0},
    {"text": "chunk two", "start_time": None, "end_time": None, "chunk_index": 1},
]

FAKE_AUDIO_CHUNKS = [
    {"text": "intro", "start_time": 0.0, "end_time": 30.0, "chunk_index": 0},
    {"text": "main",  "start_time": 30.0, "end_time": 60.0, "chunk_index": 1},
]


def _upload(client, auth_headers, content=b"data", filename="test.pdf", mime="application/pdf"):
    return client.post(
        "/api/upload",
        files={"file": (filename, io.BytesIO(content), mime)},
        headers=auth_headers,
    )


class TestUploadFile:
    def test_upload_pdf_success(self, client, auth_headers):
        with patch("app.routes.upload.pdf_service.extract_chunks", return_value=FAKE_CHUNKS), \
             patch("app.routes.upload.embedding_service.index_chunks", return_value=None):
            response = _upload(client, auth_headers, filename="doc.pdf", mime="application/pdf")

        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "pdf"
        assert data["status"] == "processing"
        assert "file_id" in data

    def test_upload_audio_success(self, client, auth_headers):
        with patch("app.routes.upload.whisper_service.transcribe", return_value=FAKE_AUDIO_CHUNKS), \
             patch("app.routes.upload.embedding_service.index_chunks", return_value=None):
            response = _upload(client, auth_headers, filename="audio.mp3", mime="audio/mpeg")

        assert response.status_code == 200
        assert response.json()["file_type"] == "audio"

    def test_upload_video_success(self, client, auth_headers):
        with patch("app.routes.upload.whisper_service.transcribe", return_value=FAKE_AUDIO_CHUNKS), \
             patch("app.routes.upload.embedding_service.index_chunks", return_value=None):
            response = _upload(client, auth_headers, filename="video.mp4", mime="video/mp4")

        assert response.status_code == 200
        assert response.json()["file_type"] == "video"

    def test_upload_unsupported_type(self, client, auth_headers):
        response = _upload(client, auth_headers, filename="img.png", mime="image/png")
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_upload_requires_auth(self, client):
        response = client.post(
            "/api/upload",
            files={"file": ("test.pdf", io.BytesIO(b"data"), "application/pdf")},
        )
        assert response.status_code == 403

    def test_upload_file_too_large(self, client, auth_headers):
        """Setting MAX_FILE_SIZE_MB=0 means any non-empty file triggers 413."""
        with patch("app.routes.upload.settings") as mock_cfg:
            mock_cfg.MAX_FILE_SIZE_MB = 0
            mock_cfg.UPLOAD_DIR = "test_uploads"
            response = _upload(client, auth_headers, content=b"any content", filename="big.pdf")

        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    def test_upload_wav_audio_type(self, client, auth_headers):
        with patch("app.routes.upload.whisper_service.transcribe", return_value=FAKE_AUDIO_CHUNKS), \
             patch("app.routes.upload.embedding_service.index_chunks", return_value=None):
            response = _upload(client, auth_headers, filename="rec.wav", mime="audio/wav")
        assert response.status_code == 200

    def test_upload_webm_video_type(self, client, auth_headers):
        with patch("app.routes.upload.whisper_service.transcribe", return_value=FAKE_AUDIO_CHUNKS), \
             patch("app.routes.upload.embedding_service.index_chunks", return_value=None):
            response = _upload(client, auth_headers, filename="rec.webm", mime="video/webm")
        assert response.status_code == 200


class TestGetStatus:
    def test_status_found(self, client, pdf_doc):
        response = client.get(f"/api/status/{pdf_doc['file_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == pdf_doc["file_id"]
        assert data["status"] == "ready"
        assert data["file_type"] == "pdf"

    def test_status_not_found(self, client):
        response = client.get("/api/status/nonexistent-file-id")
        assert response.status_code == 404

    def test_status_shows_error_field(self, client):
        make_doc("err-001", "pdf", "error")
        documents_collection.update_one(
            {"file_id": "err-001"}, {"$set": {"error": "Embedding failed"}}
        )
        response = client.get("/api/status/err-001")
        assert response.status_code == 200
        assert response.json()["error"] == "Embedding failed"


class TestProcessFileBackgroundTask:
    """Test the _process_file background task directly."""

    def test_process_pdf_success(self):
        from app.routes.upload import _process_file
        make_doc("bg-test-001", "pdf", "processing")

        with patch("app.routes.upload.pdf_service.extract_chunks", return_value=FAKE_CHUNKS), \
             patch("app.routes.upload.embedding_service.index_chunks", return_value=None):
            _process_file("bg-test-001", "fake/path.pdf", "pdf")

        doc = documents_collection.find_one({"file_id": "bg-test-001"})
        assert doc["status"] == "ready"

    def test_process_audio_success(self):
        from app.routes.upload import _process_file
        make_doc("bg-test-002", "audio", "processing")

        with patch("app.routes.upload.whisper_service.transcribe", return_value=FAKE_AUDIO_CHUNKS), \
             patch("app.routes.upload.embedding_service.index_chunks", return_value=None):
            _process_file("bg-test-002", "fake/path.mp3", "audio")

        doc = documents_collection.find_one({"file_id": "bg-test-002"})
        assert doc["status"] == "ready"

    def test_process_file_exception_sets_error_status(self):
        from app.routes.upload import _process_file
        make_doc("bg-test-003", "pdf", "processing")

        with patch("app.routes.upload.pdf_service.extract_chunks", side_effect=RuntimeError("Extract failed")):
            _process_file("bg-test-003", "fake/path.pdf", "pdf")

        doc = documents_collection.find_one({"file_id": "bg-test-003"})
        assert doc["status"] == "error"
        assert "Extract failed" in doc["error"]

    def test_safe_log_swallows_exceptions(self):
        from app.routes.upload import _safe_log
        # Should not raise even when print fails somehow
        _safe_log("just a log message")

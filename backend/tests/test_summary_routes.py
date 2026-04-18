"""tests/test_summary_routes.py — /api/summary."""
import json
import pytest
from unittest.mock import patch

FAKE_SUMMARY = "• The document covers solar energy.\n• It explains photovoltaic cells."


class TestSummary:
    def test_summary_success(self, client, auth_headers, pdf_doc, pdf_chunks):
        with patch("app.routes.summary.summarize", return_value=FAKE_SUMMARY):
            response = client.post("/api/summary", json={"file_id": "pdf-001"},
                                   headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == "pdf-001"
        assert data["summary"] == FAKE_SUMMARY
        assert data["file_type"] == "pdf"
        assert data["original_filename"] == "file.pdf"

    def test_summary_file_not_found(self, client, auth_headers):
        response = client.post("/api/summary", json={"file_id": "ghost"},
                               headers=auth_headers)
        assert response.status_code == 404

    def test_summary_file_not_ready(self, client, auth_headers, processing_doc):
        response = client.post("/api/summary", json={"file_id": "proc-003"},
                               headers=auth_headers)
        assert response.status_code == 400
        assert "not ready" in response.json()["detail"].lower()

    def test_summary_no_chunks(self, client, auth_headers, pdf_doc):
        """File is ready but has no chunks — should 404."""
        response = client.post("/api/summary", json={"file_id": "pdf-001"},
                               headers=auth_headers)
        assert response.status_code == 404
        assert "No content found" in response.json()["detail"]

    def test_summary_returned_from_cache(self, client, auth_headers, pdf_doc, pdf_chunks):
        """Second call should use Redis cache (no second LLM call)."""
        cached_value = {
            "file_id": "pdf-001",
            "original_filename": "file.pdf",
            "file_type": "pdf",
            "summary": "Cached summary.",
        }
        with patch("app.routes.summary.cache_get", return_value=cached_value) as mock_cache:
            response = client.post("/api/summary", json={"file_id": "pdf-001"},
                                   headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["summary"] == "Cached summary."
        mock_cache.assert_called_once_with("summary:pdf-001")

    def test_summary_result_is_cached(self, client, auth_headers, pdf_doc, pdf_chunks):
        """After computing, result should be stored in Redis cache."""
        with patch("app.routes.summary.cache_get", return_value=None), \
             patch("app.routes.summary.cache_set") as mock_set, \
             patch("app.routes.summary.summarize", return_value=FAKE_SUMMARY):
            client.post("/api/summary", json={"file_id": "pdf-001"}, headers=auth_headers)

        mock_set.assert_called_once()
        call_args = mock_set.call_args
        assert call_args[0][0] == "summary:pdf-001"

    def test_summary_requires_auth(self, client, pdf_doc):
        response = client.post("/api/summary", json={"file_id": "pdf-001"})
        assert response.status_code == 403

    def test_summary_invalid_body(self, client, auth_headers):
        response = client.post("/api/summary", json={}, headers=auth_headers)
        assert response.status_code == 422

"""tests/services/test_pdf_service.py — Unit tests for pdf_service.py."""
import pytest
from unittest.mock import MagicMock, patch


class TestExtractChunks:
    def _run(self, text, chunk_size=500):
        from app.services.pdf_service import extract_chunks
        mock_page = MagicMock()
        mock_page.get_text.return_value = text

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.close = MagicMock()

        with patch("app.services.pdf_service.fitz.open", return_value=mock_doc):
            return extract_chunks("fake/path.pdf", chunk_size=chunk_size)

    def test_basic_extraction_returns_chunks(self):
        text = " ".join([f"word{i}" for i in range(600)])  # 600 words
        chunks = self._run(text, chunk_size=500)
        assert len(chunks) == 2

    def test_each_chunk_has_required_keys(self):
        text = " ".join([f"word{i}" for i in range(100)])
        chunks = self._run(text, chunk_size=500)
        assert len(chunks) == 1
        chunk = chunks[0]
        assert "text" in chunk
        assert "start_time" in chunk
        assert "end_time" in chunk
        assert "chunk_index" in chunk

    def test_pdf_chunks_have_no_timestamps(self):
        text = " ".join([f"word{i}" for i in range(50)])
        chunks = self._run(text)
        for c in chunks:
            assert c["start_time"] is None
            assert c["end_time"] is None

    def test_chunk_index_is_sequential(self):
        text = " ".join([f"word{i}" for i in range(1200)])  # 3 chunks × 500
        chunks = self._run(text, chunk_size=500)
        assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))

    def test_empty_text_returns_no_chunks(self):
        chunks = self._run("")
        assert chunks == []

    def test_whitespace_only_returns_no_chunks(self):
        chunks = self._run("   \n\t  ")
        assert chunks == []

    def test_multi_page_text_concatenated(self):
        from app.services.pdf_service import extract_chunks

        page1 = MagicMock()
        page1.get_text.return_value = "Page one content. "
        page2 = MagicMock()
        page2.get_text.return_value = "Page two content."

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([page1, page2]))
        mock_doc.close = MagicMock()

        with patch("app.services.pdf_service.fitz.open", return_value=mock_doc):
            chunks = extract_chunks("fake.pdf", chunk_size=500)

        assert len(chunks) == 1
        assert "Page one" in chunks[0]["text"]
        assert "Page two" in chunks[0]["text"]

    def test_exact_chunk_size_boundary(self):
        # Exactly 500 words → fits in one chunk (range stops at chunk_size, not chunk_size-1)
        text = " ".join([f"w{i}" for i in range(500)])
        chunks = self._run(text, chunk_size=500)
        assert len(chunks) == 1

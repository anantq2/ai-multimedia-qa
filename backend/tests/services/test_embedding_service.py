"""tests/services/test_embedding_service.py — Unit tests for embedding_service.py."""
import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from app.database import chunks_collection


FAKE_DIM = 3072
FAKE_VECTOR = [0.01] * FAKE_DIM

CHUNKS = [
    {"text": "First chunk.",  "start_time": None, "end_time": None, "chunk_index": 0},
    {"text": "Second chunk.", "start_time": 0.0,  "end_time": 30.0, "chunk_index": 1},
]


class TestGetEmbedding:
    def test_returns_list_of_floats(self):
        from app.services.embedding_service import get_embedding, embedding_service as emb_svc

        with patch.object(emb_svc, "embed_query", return_value=FAKE_VECTOR):
            result = get_embedding("Hello world")

        assert isinstance(result, list)
        assert len(result) == FAKE_DIM

    def test_calls_embed_query(self):
        from app.services.embedding_service import get_embedding, embedding_service as emb_svc

        with patch.object(emb_svc, "embed_query", return_value=FAKE_VECTOR) as mock_eq:
            get_embedding("Test text")

        mock_eq.assert_called_once_with("Test text")


class TestIndexChunks:
    def test_index_chunks_stores_in_mongo(self, tmp_path):
        from app.services.embedding_service import index_chunks, embedding_service as emb_svc

        with patch.object(emb_svc, "embed_query", return_value=FAKE_VECTOR), \
             patch("app.services.embedding_service.settings") as mock_cfg, \
             patch("app.services.embedding_service.faiss") as mock_faiss:

            mock_cfg.FAISS_DIR = str(tmp_path)
            mock_index = MagicMock()
            mock_faiss.IndexFlatL2.return_value = mock_index

            index_chunks("test-file-x", CHUNKS)

        stored = list(chunks_collection.find({"file_id": "test-file-x"}))
        assert len(stored) == len(CHUNKS)
        assert stored[0]["text"] == "First chunk."
        assert stored[1]["start_time"] == 0.0

    def test_index_chunks_empty_list_returns_early(self, tmp_path):
        from app.services.embedding_service import index_chunks, embedding_service as emb_svc

        with patch.object(emb_svc, "embed_query") as mock_eq:
            index_chunks("file-empty", [])

        mock_eq.assert_not_called()
        assert chunks_collection.count_documents({"file_id": "file-empty"}) == 0

    def test_index_chunks_saves_faiss_file(self, tmp_path):
        from app.services.embedding_service import index_chunks, embedding_service as emb_svc

        with patch.object(emb_svc, "embed_query", return_value=FAKE_VECTOR), \
             patch("app.services.embedding_service.settings") as mock_cfg, \
             patch("app.services.embedding_service.faiss") as mock_faiss:

            mock_cfg.FAISS_DIR = str(tmp_path)
            mock_faiss.IndexFlatL2.return_value = MagicMock()

            index_chunks("file-faiss", CHUNKS)

        mock_faiss.write_index.assert_called_once()

    def test_embedding_id_matches_position(self, tmp_path):
        from app.services.embedding_service import index_chunks, embedding_service as emb_svc

        with patch.object(emb_svc, "embed_query", return_value=FAKE_VECTOR), \
             patch("app.services.embedding_service.settings") as mock_cfg, \
             patch("app.services.embedding_service.faiss") as mock_faiss:

            mock_cfg.FAISS_DIR = str(tmp_path)
            mock_faiss.IndexFlatL2.return_value = MagicMock()
            index_chunks("file-ids", CHUNKS)

        stored = list(chunks_collection.find({"file_id": "file-ids"}).sort("embedding_id", 1))
        for i, doc in enumerate(stored):
            assert doc["embedding_id"] == i


class TestSearch:
    def test_search_returns_top_k_chunks(self, tmp_path):
        from app.services.embedding_service import search, embedding_service as emb_svc

        # Pre-populate MongoDB with chunks
        chunks_collection.insert_many([
            {"file_id": "search-file", "text": "Chunk A", "start_time": None, "end_time": None, "chunk_index": 0, "embedding_id": 0},
            {"file_id": "search-file", "text": "Chunk B", "start_time": None, "end_time": None, "chunk_index": 1, "embedding_id": 1},
        ])

        mock_index = MagicMock()
        mock_index.search.return_value = (None, np.array([[0, 1]]))

        with patch.object(emb_svc, "embed_query", return_value=FAKE_VECTOR), \
             patch("app.services.embedding_service.faiss.read_index", return_value=mock_index), \
             patch("app.services.embedding_service.os.path.exists", return_value=True), \
             patch("app.services.embedding_service.settings") as mock_cfg:

            mock_cfg.FAISS_DIR = str(tmp_path)
            results = search("search-file", "What is Chunk A?", top_k=2)

        assert len(results) == 2

    def test_search_missing_index_raises(self, tmp_path):
        from app.services.embedding_service import search

        with patch("app.services.embedding_service.settings") as mock_cfg:
            mock_cfg.FAISS_DIR = str(tmp_path)
            with pytest.raises(FileNotFoundError):
                search("nonexistent-file", "question?")

    def test_search_filters_faiss_minus_one(self, tmp_path):
        """FAISS returns -1 for empty slots; these should be skipped."""
        from app.services.embedding_service import search, embedding_service as emb_svc

        chunks_collection.insert_one({
            "file_id": "sparse-file", "text": "Only chunk", "start_time": None,
            "end_time": None, "chunk_index": 0, "embedding_id": 0,
        })

        mock_index = MagicMock()
        # Returns one valid (0) and one invalid (-1) entry
        mock_index.search.return_value = (None, np.array([[0, -1]]))

        with patch.object(emb_svc, "embed_query", return_value=FAKE_VECTOR), \
             patch("app.services.embedding_service.faiss.read_index", return_value=mock_index), \
             patch("app.services.embedding_service.os.path.exists", return_value=True), \
             patch("app.services.embedding_service.settings") as mock_cfg:

            mock_cfg.FAISS_DIR = str(tmp_path)
            results = search("sparse-file", "anything?")

        assert len(results) == 1
        assert results[0]["text"] == "Only chunk"

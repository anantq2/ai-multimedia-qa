"""
tests/conftest.py — Session-wide fixtures and mocking infrastructure.

Strategy:
  1. Set env vars BEFORE any app import so pydantic-settings doesn't fail.
  2. Start mongomock BEFORE importing database.py (which creates MongoClient at import time).
  3. LangChain classes are patched at module level so embedding_service.py / llm_service.py
     instantiate with mocks rather than real API clients.
  4. Each test gets a clean DB state via the autouse `clean_collections` fixture.
  5. Redis is reset between tests via `reset_redis_singleton`.
"""
import os

# ── 1. Environment variables — MUST come before any app import ────────────────
os.environ.setdefault("GEMINI_API_KEY",   "test-gemini-api-key-for-testing-only")
os.environ.setdefault("MONGODB_URL",      "mongodb://localhost:27017")
os.environ.setdefault("JWT_SECRET_KEY",   "test-jwt-secret-key-long-enough-for-hs256-thirty-two-chars")
os.environ.setdefault("REDIS_URL",        "redis://localhost:6379/0")
os.environ.setdefault("UPLOAD_DIR",       "test_uploads")
os.environ.setdefault("FAISS_DIR",        "test_faiss_indexes")

import pytest
import mongomock
from unittest.mock import MagicMock, patch, AsyncMock

# ── 2. Patch MongoDB before any app module is imported ────────────────────────
_mongo_patcher = mongomock.patch(servers=(("localhost", 27017),))
_mongo_patcher.__enter__()

# ── 3. Patch LangChain so module-level instantiations don't hit real APIs ─────
_mock_llm_response = MagicMock()
_mock_llm_response.content = "Mock LLM answer for testing purposes."

_mock_llm = MagicMock()
_mock_llm.invoke.return_value = _mock_llm_response

_mock_embeddings = MagicMock()
_mock_embeddings.embed_query.return_value = [0.01] * 3072
_mock_embeddings.embed_documents.return_value = [[0.01] * 3072]

_llm_class_patcher     = patch("langchain_google_genai.ChatGoogleGenerativeAI",      return_value=_mock_llm)
_embed_class_patcher   = patch("langchain_google_genai.GoogleGenerativeAIEmbeddings", return_value=_mock_embeddings)
_llm_class_patcher.__enter__()
_embed_class_patcher.__enter__()

# ── 4. Now it is safe to import the FastAPI application ───────────────────────
from fastapi.testclient import TestClient          # noqa: E402
from app.main import app                           # noqa: E402
from app.database import (                         # noqa: E402
    users_collection,
    documents_collection,
    chunks_collection,
)
from app.services.auth_service import (            # noqa: E402
    create_access_token,
    hash_password,
)

# ══════════════════════════════════════════════════════════════════════════════
# Session-independent helpers
# ══════════════════════════════════════════════════════════════════════════════

def make_user(username="testuser", email="test@example.com", password="testpassword"):
    """Insert a user into the mock DB and return their plain credentials."""
    users_collection.delete_one({"username": username})
    users_collection.insert_one({
        "username": username,
        "email": email,
        "password": hash_password(password),
        "created_at": "2024-01-01T00:00:00",
    })
    return {"username": username, "email": email, "password": password}


def make_doc(file_id="pdf-001", file_type="pdf", status="ready"):
    doc = {
        "file_id": file_id,
        "original_filename": f"file.{file_type}",
        "processed_filename": f"{file_id}.{file_type}",
        "file_type": file_type,
        "file_path": f"test_uploads/{file_id}.{file_type}",
        "media_url": f"/media/{file_id}.{file_type}",
        "status": status,
        "uploaded_by": "testuser",
    }
    documents_collection.insert_one(doc)
    return doc


def make_chunks(file_id="pdf-001", with_timestamps=False):
    docs = [
        {
            "file_id": file_id,
            "text": "The earth orbits the sun at 30 km/s.",
            "start_time": 0.0 if with_timestamps else None,
            "end_time": 30.0 if with_timestamps else None,
            "chunk_index": 0,
            "embedding_id": 0,
        },
        {
            "file_id": file_id,
            "text": "The moon orbits the earth once per month.",
            "start_time": 30.0 if with_timestamps else None,
            "end_time": 60.0 if with_timestamps else None,
            "chunk_index": 1,
            "embedding_id": 1,
        },
    ]
    chunks_collection.insert_many(docs)
    return docs


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def clean_collections():
    """Wipe all collections before each test."""
    users_collection.delete_many({})
    documents_collection.delete_many({})
    chunks_collection.delete_many({})
    yield
    users_collection.delete_many({})
    documents_collection.delete_many({})
    chunks_collection.delete_many({})


@pytest.fixture(autouse=True)
def reset_redis_singleton():
    """Reset the global Redis singleton so each test starts fresh."""
    import app.services.redis_service as rs
    rs._redis_client = None
    yield
    rs._redis_client = None


@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def test_user():
    return make_user()


@pytest.fixture
def auth_token(test_user):
    return create_access_token(data={"sub": test_user["username"]})


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def pdf_doc():
    return make_doc("pdf-001", "pdf", "ready")


@pytest.fixture
def pdf_chunks(pdf_doc):
    return make_chunks("pdf-001", with_timestamps=False)


@pytest.fixture
def audio_doc():
    return make_doc("audio-002", "audio", "ready")


@pytest.fixture
def audio_chunks(audio_doc):
    return make_chunks("audio-002", with_timestamps=True)


@pytest.fixture
def processing_doc():
    return make_doc("proc-003", "pdf", "processing")

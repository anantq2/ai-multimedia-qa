"""tests/test_main.py — Root, health, and app-level endpoints."""
import pytest


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "AI Q&A API is running" in data["message"]
    assert data["docs"] == "/docs"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_endpoint_accessible(client):
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_endpoint_accessible(client):
    response = client.get("/redoc")
    assert response.status_code == 200


def test_media_mount_exists(client):
    """The /media/ static mount should return 404 for missing files, not 500."""
    response = client.get("/media/nonexistent_file.pdf")
    assert response.status_code == 404

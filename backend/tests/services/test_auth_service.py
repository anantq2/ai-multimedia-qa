"""tests/services/test_auth_service.py — Unit tests for auth_service.py."""
import pytest
from datetime import timedelta
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    get_current_user,
    register_user,
    authenticate_user,
)
from app.database import users_collection


# ── Password hashing ──────────────────────────────────────────────────────────

def test_hash_password_returns_string():
    hashed = hash_password("mysecret")
    assert isinstance(hashed, str)
    assert hashed != "mysecret"


def test_hash_password_different_each_call():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt salts differently each time


def test_verify_password_correct():
    hashed = hash_password("password123")
    assert verify_password("password123", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("password123")
    assert verify_password("wrongpassword", hashed) is False


# ── Token creation & decoding ─────────────────────────────────────────────────

def test_create_access_token_structure():
    token = create_access_token(data={"sub": "alice"})
    assert isinstance(token, str)
    assert len(token.split(".")) == 3   # Header.Payload.Signature


def test_create_access_token_custom_expiry():
    token = create_access_token(data={"sub": "alice"}, expires_delta=timedelta(minutes=5))
    payload = decode_token(token)
    assert payload["sub"] == "alice"


def test_decode_token_valid():
    token = create_access_token(data={"sub": "bob"})
    payload = decode_token(token)
    assert payload["sub"] == "bob"
    assert "exp" in payload


def test_decode_token_invalid_raises_401():
    with pytest.raises(HTTPException) as exc:
        decode_token("this.is.invalid")
    assert exc.value.status_code == 401


def test_decode_token_wrong_secret_raises_401():
    # Create a real token with the real key first
    token = create_access_token(data={"sub": "x"})
    # Now try to decode it with a *different* secret — should fail
    with patch("app.services.auth_service.settings.JWT_SECRET_KEY", "wrong-secret-key"):
        with pytest.raises(HTTPException) as exc:
            decode_token(token)
    assert exc.value.status_code == 401


# ── get_current_user dependency ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_current_user_valid(test_user):
    token = create_access_token(data={"sub": "testuser"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await get_current_user(creds)
    assert user["username"] == "testuser"
    assert "password" not in user   # password should be excluded


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.here")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_user_not_in_db():
    token = create_access_token(data={"sub": "nonexistentuser"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 401
    assert "User not found" in exc.value.detail


@pytest.mark.asyncio
async def test_get_current_user_token_missing_sub():
    # Token has no 'sub' claim
    token = create_access_token(data={"other": "field"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 401


# ── register_user ─────────────────────────────────────────────────────────────

def test_register_user_success():
    result = register_user("alice", "alice@example.com", "securepassword")
    assert result["username"] == "alice"
    assert result["email"] == "alice@example.com"

    # Verify it's in the DB
    db_user = users_collection.find_one({"username": "alice"})
    assert db_user is not None
    assert db_user["email"] == "alice@example.com"
    assert db_user["password"] != "securepassword"  # Hashed


def test_register_user_duplicate_username(test_user):
    with pytest.raises(HTTPException) as exc:
        register_user("testuser", "other@example.com", "pass123")
    assert exc.value.status_code == 400
    assert "Username already taken" in exc.value.detail


def test_register_user_duplicate_email(test_user):
    with pytest.raises(HTTPException) as exc:
        register_user("newusername", "test@example.com", "pass123")
    assert exc.value.status_code == 400
    assert "Email already registered" in exc.value.detail


# ── authenticate_user ─────────────────────────────────────────────────────────

def test_authenticate_user_success(test_user):
    result = authenticate_user("testuser", "testpassword")
    assert result is not None
    assert result["username"] == "testuser"


def test_authenticate_user_wrong_password(test_user):
    result = authenticate_user("testuser", "wrongpassword")
    assert result is None


def test_authenticate_user_nonexistent():
    result = authenticate_user("ghost", "anypassword")
    assert result is None

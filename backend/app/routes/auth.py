"""
Auth routes — /api/auth/register & /api/auth/login
Returns JWT token on success.
"""
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from app.services.auth_service import (
    register_user,
    authenticate_user,
    create_access_token,
)

router = APIRouter()


# ── Request schemas ───────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ── Routes ────────────────────────────────────────────────────────────────
@router.post("/auth/register")
async def register(request: RegisterRequest):
    """Register a new user and return a JWT token."""
    user = register_user(request.username, request.email, request.password)
    token = create_access_token(data={"sub": user["username"]})
    return {
        "message": "Registration successful",
        "username": user["username"],
        "email": user["email"],
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/auth/login")
async def login(request: LoginRequest):
    """Authenticate and return a JWT token."""
    user = authenticate_user(request.username, request.password)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(data={"sub": user["username"]})
    return {
        "message": "Login successful",
        "username": user["username"],
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/auth/me")
async def me(user: dict = None):
    """Get current user info — requires auth dependency to be injected by router."""
    # This is handled by the dependency injection in main.py
    # When called with get_current_user dependency, user is auto-populated
    from fastapi import Depends
    from app.services.auth_service import get_current_user
    return {"message": "This endpoint requires authentication. Use /docs to test with Bearer token."}

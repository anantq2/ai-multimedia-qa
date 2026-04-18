"""
JWT Authentication service — register, login, token verification.
Passwords are hashed with bcrypt. Tokens use HS256 JWT.
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.database import users_collection

# ── Password hashing ─────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Bearer token extractor ───────────────────────────────────────────────
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependency — inject into protected routes ─────────────────────
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """
    Extract and validate the JWT from the Authorization header.
    Returns the user dict from MongoDB.
    """
    payload = decode_token(credentials.credentials)
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = users_collection.find_one({"username": username}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ── User CRUD helpers ─────────────────────────────────────────────────────
def register_user(username: str, email: str, password: str) -> dict:
    """Create a new user. Raises HTTPException if username/email already exists."""
    if users_collection.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already taken")
    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_doc = {
        "username": username,
        "email": email,
        "password": hash_password(password),
        "created_at": datetime.utcnow().isoformat(),
    }
    users_collection.insert_one(user_doc)
    return {"username": username, "email": email}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Validate credentials and return user dict or None."""
    user = users_collection.find_one({"username": username})
    if not user or not verify_password(password, user["password"]):
        return None
    return user

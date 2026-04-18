"""
Redis service — connection, rate-limiting middleware, and caching helpers.
Gracefully degrades if Redis is unavailable (app still works without it).
"""
import json
import time
from typing import Optional

import redis
from fastapi import Request, HTTPException, status

from app.config import settings


# ── Redis Connection (lazy, non-blocking) ─────────────────────────────────
_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Get or create Redis connection. Returns None if Redis is unreachable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        _redis_client.ping()
        print("Redis connected successfully!")
        return _redis_client
    except Exception as e:
        print(f"Redis not available (app will work without caching/rate-limit): {e}")
        _redis_client = None
        return None


# ── Rate Limiter ──────────────────────────────────────────────────────────
async def rate_limit_middleware(request: Request, call_next):
    """
    Sliding-window rate limiter per user (from JWT) or per IP.
    Adds X-RateLimit-* headers to every response.
    """
    r = get_redis()
    if r is None:
        # Redis down → skip rate limiting, let the request through
        return await call_next(request)

    # Identify caller: prefer username from auth, fall back to IP
    identifier = request.client.host or "unknown"
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from app.services.auth_service import decode_token
            payload = decode_token(token)
            if payload and payload.get("sub"):
                identifier = payload.get("sub")
        except Exception:
            pass

    key = f"ratelimit:{identifier}"
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    max_requests = settings.RATE_LIMIT_REQUESTS

    try:
        pipe = r.pipeline()
        now = time.time()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, now - window)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Count requests in the window
        pipe.zcard(key)
        # Set TTL on the key
        pipe.expire(key, window)
        results = pipe.execute()

        request_count = results[2]

        if request_count > max_requests:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": f"Rate limit exceeded. Max {max_requests} requests per {window}s. Try again shortly."},
            )

        response = await call_next(request)

        # Add helpful rate-limit headers
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - request_count))
        response.headers["X-RateLimit-Reset"] = str(int(now + window))
        return response

    except Exception:
        # If Redis throws any error, let the request through
        return await call_next(request)


# ── Caching Helpers ───────────────────────────────────────────────────────
def cache_get(key: str) -> Optional[dict]:
    """Fetch a cached JSON value. Returns None if miss or Redis unavailable."""
    r = get_redis()
    if r is None:
        return None
    try:
        data = r.get(f"cache:{key}")
        return json.loads(data) if data else None
    except Exception:
        return None


def cache_set(key: str, value: dict, ttl_seconds: int = 600) -> None:
    """Store a JSON value in cache with TTL (default 10 min)."""
    r = get_redis()
    if r is None:
        return
    try:
        r.setex(f"cache:{key}", ttl_seconds, json.dumps(value))
    except Exception:
        pass  # Silently fail — caching is non-critical


def cache_delete(key: str) -> None:
    """Delete a cached key."""
    r = get_redis()
    if r is None:
        return
    try:
        r.delete(f"cache:{key}")
    except Exception:
        pass

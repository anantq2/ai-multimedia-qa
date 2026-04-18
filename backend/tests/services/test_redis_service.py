"""tests/services/test_redis_service.py — Unit tests for redis_service.py."""
import json
import time
import pytest
import fakeredis
from unittest.mock import patch, MagicMock
from fastapi import Request, HTTPException
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
import app.services.redis_service as rs


# ── Helpers ───────────────────────────────────────────────────────────────────

def fake_redis():
    """Return a fresh in-memory FakeRedis client."""
    return fakeredis.FakeRedis(decode_responses=True)


def _inject_redis(r):
    rs._redis_client = r


# ══════════════════════════════════════════════════════════════════════════════
# get_redis
# ══════════════════════════════════════════════════════════════════════════════

class TestGetRedis:
    def test_returns_client_when_reachable(self):
        fr = fake_redis()
        with patch("app.services.redis_service.redis.from_url", return_value=fr):
            result = rs.get_redis()
        assert result is fr

    def test_caches_client_on_second_call(self):
        fr = fake_redis()
        with patch("app.services.redis_service.redis.from_url", return_value=fr) as mock_url:
            rs.get_redis()
            rs.get_redis()
        mock_url.assert_called_once()   # Second call reuses cached

    def test_returns_none_when_unreachable(self):
        with patch("app.services.redis_service.redis.from_url", side_effect=Exception("refused")):
            result = rs.get_redis()
        assert result is None

    def test_returns_cached_client_if_already_set(self):
        fr = fake_redis()
        rs._redis_client = fr
        with patch("app.services.redis_service.redis.from_url") as mock_url:
            result = rs.get_redis()
        mock_url.assert_not_called()
        assert result is fr


# ══════════════════════════════════════════════════════════════════════════════
# cache_get / cache_set / cache_delete
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheGet:
    def test_returns_dict_on_hit(self):
        fr = fake_redis()
        fr.set("cache:mykey", json.dumps({"result": "value"}))
        _inject_redis(fr)
        assert rs.cache_get("mykey") == {"result": "value"}

    def test_returns_none_on_miss(self):
        _inject_redis(fake_redis())
        assert rs.cache_get("missing") is None

    def test_returns_none_when_redis_down(self):
        rs._redis_client = None
        assert rs.cache_get("anything") is None

    def test_returns_none_on_redis_error(self):
        fr = MagicMock()
        fr.get.side_effect = Exception("connection error")
        rs._redis_client = fr
        assert rs.cache_get("key") is None


class TestCacheSet:
    def test_stores_value_with_ttl(self):
        fr = fake_redis()
        _inject_redis(fr)
        rs.cache_set("testkey", {"data": 42}, ttl_seconds=60)
        stored = json.loads(fr.get("cache:testkey"))
        assert stored == {"data": 42}

    def test_noop_when_redis_down(self):
        rs._redis_client = None
        # Should not raise
        rs.cache_set("key", {"v": 1})

    def test_noop_on_redis_error(self):
        fr = MagicMock()
        fr.setex.side_effect = Exception("boom")
        rs._redis_client = fr
        rs.cache_set("key", {"v": 1})   # Should not raise


class TestCacheDelete:
    def test_deletes_existing_key(self):
        fr = fake_redis()
        fr.set("cache:delkey", "val")
        _inject_redis(fr)
        rs.cache_delete("delkey")
        assert fr.get("cache:delkey") is None

    def test_noop_when_redis_down(self):
        rs._redis_client = None
        rs.cache_delete("key")   # Should not raise

    def test_noop_on_redis_error(self):
        fr = MagicMock()
        fr.delete.side_effect = Exception("boom")
        rs._redis_client = fr
        rs.cache_delete("key")   # Should not raise


# ══════════════════════════════════════════════════════════════════════════════
# rate_limit_middleware
# ══════════════════════════════════════════════════════════════════════════════

class TestRateLimitMiddleware:
    """Test rate limit middleware using a minimal Starlette app."""

    def _make_app(self):
        from fastapi import FastAPI
        from fastapi.responses import PlainTextResponse
        from starlette.middleware.base import BaseHTTPMiddleware
        app = FastAPI()
        app.add_middleware(BaseHTTPMiddleware, dispatch=rs.rate_limit_middleware)
        
        @app.get("/")
        async def homepage():
            return PlainTextResponse("OK")
            
        return app

    def test_passes_when_redis_down(self):
        rs._redis_client = None
        app = self._make_app()

        with TestClient(app, raise_server_exceptions=True) as c:
            response = c.get("/")
        assert response.status_code == 200

    def test_passes_within_limit(self):
        fr = fake_redis()
        _inject_redis(fr)

        with patch("app.services.redis_service.settings") as mock_cfg:
            mock_cfg.RATE_LIMIT_REQUESTS = 30
            mock_cfg.RATE_LIMIT_WINDOW_SECONDS = 60
            mock_cfg.REDIS_URL = "redis://localhost:6379/0"

            app = self._make_app()
            with TestClient(app, raise_server_exceptions=True) as c:
                response = c.get("/")
        assert response.status_code == 200

    def test_rate_limit_headers_added(self):
        fr = fake_redis()
        _inject_redis(fr)

        with patch("app.services.redis_service.settings") as mock_cfg:
            mock_cfg.RATE_LIMIT_REQUESTS = 30
            mock_cfg.RATE_LIMIT_WINDOW_SECONDS = 60
            mock_cfg.REDIS_URL = "redis://localhost:6379/0"

            app = self._make_app()
            with TestClient(app, raise_server_exceptions=True) as c:
                response = c.get("/")

        assert "x-ratelimit-limit" in response.headers

    def test_rate_limit_exceeded_returns_429(self):
        import time

        fr = fake_redis()
        _inject_redis(fr)

        # Pre-fill the sorted set under the exact identifier TestClient uses
        now = time.time()
        for i in range(31):
            fr.zadd("ratelimit:testclient", {str(now + i): now + i})

        with patch("app.services.redis_service.settings") as mock_cfg:
            mock_cfg.RATE_LIMIT_REQUESTS = 30
            mock_cfg.RATE_LIMIT_WINDOW_SECONDS = 60
            mock_cfg.REDIS_URL = "redis://localhost:6379/0"

            app = self._make_app()
            with TestClient(app, raise_server_exceptions=False) as c:
                response = c.get("/")

        assert response.status_code == 429

    def test_username_extracted_from_jwt(self):
        """Rate limiter should use JWT sub as identifier."""
        from app.services.auth_service import create_access_token
        token = create_access_token(data={"sub": "alice"})

        fr = fake_redis()
        _inject_redis(fr)

        with patch("app.services.redis_service.settings") as mock_cfg:
            mock_cfg.RATE_LIMIT_REQUESTS = 30
            mock_cfg.RATE_LIMIT_WINDOW_SECONDS = 60
            mock_cfg.REDIS_URL = "redis://localhost:6379/0"

            app = self._make_app()
            with TestClient(app, raise_server_exceptions=True) as c:
                response = c.get("/", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        # The key in Redis should use username, not IP
        keys = fr.keys("ratelimit:alice")
        assert len(keys) == 1

    def test_redis_error_in_middleware_passes_through(self):
        """If Redis throws during rate limiting, request still goes through."""
        fr = MagicMock()
        fr.pipeline.side_effect = Exception("redis error")
        rs._redis_client = fr

        with patch("app.services.redis_service.settings") as mock_cfg:
            mock_cfg.RATE_LIMIT_REQUESTS = 30
            mock_cfg.RATE_LIMIT_WINDOW_SECONDS = 60

            app = self._make_app()
            with TestClient(app, raise_server_exceptions=True) as c:
                response = c.get("/")

        assert response.status_code == 200

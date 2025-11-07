from __future__ import annotations

from typing import Dict, Tuple

import sys
import types

import pytest

# Provide a lightweight stub for the optional redis dependency used in production.
redis_stub = types.ModuleType("redis")
redis_stub.Redis = object  # type: ignore[attr-defined]
redis_stub.RedisError = Exception
sys.modules.setdefault("redis", redis_stub)

# Minimal FastAPI stub for HTTPException
fastapi_stub = types.ModuleType("fastapi")


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


fastapi_stub.HTTPException = HTTPException  # type: ignore[attr-defined]
sys.modules.setdefault("fastapi", fastapi_stub)

from api.app.services.rate_limiter import RateLimiter


class FakePipeline:
    def __init__(self, store: Dict[str, int], key: str):
        self._store = store
        self._key = key
        self._commands: Dict[str, Tuple[str, int]] = {}

    def incr(self, key: str) -> "FakePipeline":
        self._commands["incr"] = (key, 1)
        return self

    def expire(self, key: str, seconds: int) -> "FakePipeline":
        self._commands["expire"] = (key, seconds)
        return self

    def execute(self) -> Tuple[int, bool]:
        key, _ = self._commands.get("incr", (self._key, 0))
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key], True

    def __enter__(self) -> "FakePipeline":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class FakeRedis:
    def __init__(self) -> None:
        self.store: Dict[str, int] = {}

    def pipeline(self):
        return FakePipeline(self.store, "")


def test_rate_limiter_allows_within_limit():
    limiter = RateLimiter(FakeRedis(), window_seconds=60, enabled=True)
    result = limiter.check("scope:user", limit=2)
    assert result is not None
    assert result.count == 1


def test_rate_limiter_blocks_when_limit_exceeded():
    limiter = RateLimiter(FakeRedis(), window_seconds=60, enabled=True)
    limiter.check("scope:user", limit=1)
    with pytest.raises(Exception) as exc:
        limiter.check("scope:user", limit=1)
    assert "Rate limit exceeded" in str(exc.value)


def test_rate_limiter_disabled_returns_none():
    limiter = RateLimiter(FakeRedis(), window_seconds=60, enabled=False)
    assert limiter.check("scope:user", limit=1) is None

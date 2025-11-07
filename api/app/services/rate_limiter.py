"""Redis-backed request rate limiting helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import redis
from fastapi import HTTPException


logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    key: str
    count: int
    limit: int
    window_seconds: int


class RateLimiter:
    """Simple fixed-window rate limiter stored in Redis."""

    def __init__(
        self,
        redis_client: redis.Redis,
        *,
        window_seconds: int,
        enabled: bool = True,
    ) -> None:
        self._redis = redis_client
        self._window_seconds = window_seconds
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _format_key(self, scope: str) -> str:
        return f"rate:{scope}"

    def check(self, scope: str, limit: int) -> Optional[RateLimitResult]:
        """Increment usage counter for ``scope`` and raise when exceeding ``limit``."""

        if not self._enabled or limit <= 0:
            return None

        redis_key = self._format_key(scope)

        try:
            with self._redis.pipeline() as pipeline:
                pipeline.incr(redis_key)
                pipeline.expire(redis_key, self._window_seconds)
                count, _ = pipeline.execute()
        except redis.RedisError as exc:  # pragma: no cover - depends on redis availability
            logger.warning("Rate limiter unavailable", extra={"error": str(exc)})
            return None

        if count > limit:
            logger.info(
                "Rate limit exceeded", extra={"key": redis_key, "count": count, "limit": limit}
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please retry after the current window.",
            )

        return RateLimitResult(redis_key, int(count), int(limit), self._window_seconds)


__all__ = ["RateLimiter", "RateLimitResult"]

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
        strict_mode: bool = True,
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client for storing rate limit counters
            window_seconds: Time window in seconds for rate limiting
            enabled: Whether rate limiting is enabled
            strict_mode: If True, fail requests when Redis is unavailable (fail closed).
                        If False, allow requests when Redis is unavailable (fail open).
        """
        self._redis = redis_client
        self._window_seconds = window_seconds
        self._enabled = enabled
        self._strict_mode = strict_mode

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _format_key(self, scope: str) -> str:
        return f"rate:{scope}"

    def check(self, scope: str, limit: int) -> Optional[RateLimitResult]:
        """
        Increment usage counter for ``scope`` and raise when exceeding ``limit``.

        Args:
            scope: Unique identifier for the rate limit scope
            limit: Maximum number of requests allowed in the window

        Returns:
            RateLimitResult if rate limiting is active, None otherwise

        Raises:
            HTTPException: If rate limit is exceeded or Redis is unavailable in strict mode
            ValueError: If limit is misconfigured (negative or zero when enabled)
        """
        if not self._enabled:
            return None

        # Validate limit configuration
        if limit <= 0:
            logger.error("Invalid rate limit configured", extra={"limit": limit})
            raise ValueError(f"Rate limit must be positive, got: {limit}")

        redis_key = self._format_key(scope)

        try:
            with self._redis.pipeline() as pipeline:
                pipeline.incr(redis_key)
                pipeline.expire(redis_key, self._window_seconds)
                count, _ = pipeline.execute()
        except redis.RedisError as exc:  # pragma: no cover - depends on redis availability
            logger.error(
                "Rate limiter unavailable",
                extra={"error": str(exc), "scope": scope, "strict_mode": self._strict_mode}
            )
            # In strict mode, fail closed for security
            if self._strict_mode:
                raise HTTPException(
                    status_code=503,
                    detail="Rate limiting service temporarily unavailable. Please retry shortly.",
                ) from exc
            # In non-strict mode, fail open (allow request)
            logger.warning("Allowing request despite rate limiter failure (non-strict mode)")
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

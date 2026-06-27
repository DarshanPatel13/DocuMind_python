"""Redis-backed fixed-window rate limiter.

Why Redis (not slowapi's in-memory counter): the limit must hold across multiple
gateway replicas. A counter in process memory resets per replica and per restart;
a shared Redis counter is correct under horizontal scaling. Java analogy:
Bucket4j backed by Redis instead of a local in-memory bucket.

Algorithm (fixed window): one key per (user, minute), INCR it, set a 60s TTL on
first write, reject when it exceeds the limit. Simple and good enough here; a
sliding-window/token-bucket would smooth bursts at window edges (noted as a
next step).
"""
from __future__ import annotations

import time

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.config import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def enforce_rate_limit(user: str) -> None:
    """Raise 429 if `user` exceeded the per-minute limit."""
    window = int(time.time()) // 60
    key = f"rl:{user}:{window}"
    redis = get_redis()
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({settings.rate_limit_per_minute}/min)",
        )


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None

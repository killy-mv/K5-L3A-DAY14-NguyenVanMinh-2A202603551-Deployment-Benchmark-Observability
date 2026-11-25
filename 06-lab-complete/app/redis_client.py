"""Lazy Redis connection shared by the security modules."""
import redis
from fastapi import HTTPException

from .config import settings

r = redis.from_url(settings.redis_url, decode_responses=True,
                   socket_connect_timeout=1, socket_timeout=2)


def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except redis.RedisError:
        return False


def unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="Redis unavailable; please retry")

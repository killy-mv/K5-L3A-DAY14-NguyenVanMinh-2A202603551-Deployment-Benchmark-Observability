"""Atomic sliding-window rate limit shared across all workers."""
import hashlib
import uuid

import redis
from fastapi import HTTPException

from .config import settings
from .redis_client import r, unavailable

SLIDING_WINDOW = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
local window = 60000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return math.max(1, math.ceil((tonumber(oldest[2]) + window - now) / 1000))
end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('PEXPIRE', KEYS[1], window)
return 0
"""


def check_rate_limit(key: str) -> None:
    digest = hashlib.sha256(key.encode()).hexdigest()
    try:
        retry = int(r.eval(SLIDING_WINDOW, 1, f"day14:rate:{digest}",
                           settings.rate_limit_per_minute, uuid.uuid4().hex))
    except redis.RedisError:
        raise unavailable() from None
    if retry:
        raise HTTPException(status_code=429, detail="Rate limit exceeded",
                            headers={"Retry-After": str(retry)})

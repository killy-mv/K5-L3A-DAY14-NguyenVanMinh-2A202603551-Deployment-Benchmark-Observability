"""Atomic global budget reservation and reconciliation in integer micro-USD."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

import redis
from fastapi import HTTPException

from .config import settings
from .redis_client import r, unavailable

PRICE_INPUT_PER_1K = Decimal("0.00015")
PRICE_OUTPUT_PER_1K = Decimal("0.0006")
MICRO = Decimal("1000000")
# Upper bound for this lab's short, fixed mock responses.
MAX_MOCK_OUTPUT_TOKENS = 512

RESERVE = """
for i = 1, #KEYS do
    local current = tonumber(redis.call('GET', KEYS[i]) or '0')
    if current + tonumber(ARGV[1]) > tonumber(ARGV[2*i]) then return 0 end
end
for i = 1, #KEYS do
    redis.call('INCRBY', KEYS[i], ARGV[1])
    redis.call('EXPIREAT', KEYS[i], ARGV[2*i+1])
end
return 1
"""
RECONCILE = """
for i = 1, #KEYS do
    if redis.call('EXISTS', KEYS[i]) == 1 then
        redis.call('INCRBY', KEYS[i], ARGV[1])
    end
end
return 1
"""


@dataclass(frozen=True)
class Reservation:
    keys: tuple[str, ...]
    micro_usd: int


def _cost(input_tokens: int, output_tokens: int) -> int:
    usd = (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000
    return int((usd * MICRO).to_integral_value(rounding=ROUND_CEILING))


def _periods():
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    yield f"day14:budget:month:{now:%Y-%m}", settings.monthly_budget_usd, int(next_month.timestamp())
    if settings.daily_budget_usd is not None:
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        yield f"day14:budget:day:{now:%Y-%m-%d}", settings.daily_budget_usd, int(tomorrow.timestamp())


def check_budget(input_tokens: int) -> Reservation:
    amount = _cost(input_tokens, MAX_MOCK_OUTPUT_TOKENS)
    periods = list(_periods())
    keys = tuple(key for key, _, _ in periods)
    args = [amount]
    for _, budget, expires in periods:
        args += [int((budget * MICRO).to_integral_value(rounding=ROUND_FLOOR)), expires]
    try:
        accepted = r.eval(RESERVE, len(keys), *keys, *args)
    except redis.RedisError:
        raise unavailable() from None
    if not accepted:
        raise HTTPException(status_code=402, detail="LLM budget exhausted")
    return Reservation(keys, amount)


def _settle(reservation: Reservation, actual: int) -> None:
    try:
        r.eval(RECONCILE, len(reservation.keys), *reservation.keys, actual - reservation.micro_usd)
    except redis.RedisError:
        # Keep the conservative reservation if Redis cannot reconcile it.
        raise unavailable() from None


def record_cost(reservation: Reservation, input_tokens: int, output_tokens: int) -> float:
    actual = _cost(input_tokens, output_tokens)
    _settle(reservation, actual)
    return float(Decimal(actual) / MICRO)


def release_budget(reservation: Reservation) -> None:
    _settle(reservation, 0)

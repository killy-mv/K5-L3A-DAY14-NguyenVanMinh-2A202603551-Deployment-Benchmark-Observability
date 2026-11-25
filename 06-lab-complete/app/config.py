"""Environment-based configuration; no credentials in source."""
import os
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Settings:
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")))
    monthly_budget_usd: Decimal = field(default_factory=lambda: Decimal(os.getenv("MONTHLY_BUDGET_USD", "10")))
    daily_budget_usd: Decimal | None = field(default_factory=lambda: Decimal(os.environ["DAILY_BUDGET_USD"]) if os.getenv("DAILY_BUDGET_USD") else None)

    def __post_init__(self):
        if not 1 <= self.port <= 65535 or self.rate_limit_per_minute < 1:
            raise ValueError("Invalid port or rate limit")
        for budget in (self.monthly_budget_usd, self.daily_budget_usd):
            if budget is not None and (not budget.is_finite() or budget < 0):
                raise ValueError("Budget must be finite and non-negative")


settings = Settings()

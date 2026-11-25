"""Production agent with authentication, Redis protection and JSON logging."""
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from utils.mock_llm import ask as llm_ask
from .auth import verify_api_key
from .config import settings
from .cost_guard import check_budget, record_cost, release_budget
from .rate_limiter import check_rate_limit
from .redis_client import r, redis_healthy


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "lvl": record.levelname,
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger("day14.agent")
logger.setLevel(logging.INFO)
logger.propagate = False
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.handlers[:] = [handler]
STARTED = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"fields": {"environment": settings.environment}})
    try:
        yield
    finally:
        r.close()
        logger.info("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan,
              docs_url=None if settings.environment == "production" else "/docs")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str | None = Field(default=None, max_length=128)

    @field_validator("question")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value.strip()


@app.middleware("http")
async def log_request(request: Request, call_next):
    start = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        logger.info("request", extra={"fields": {
            "method": request.method, "path": request.url.path,
            "status": status, "ms": round((time.monotonic() - start) * 1000, 2)
        }})


@app.get("/health")
def health():
    return {"status": "ok", "uptime_seconds": round(time.monotonic() - STARTED, 2)}


@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis not available")
    return {"ready": True}


@app.post("/ask")
def ask(body: AskRequest, key: str = Depends(verify_api_key)):
    check_rate_limit(key)
    input_tokens = max(1, len(body.question.split()) * 2)
    reservation = check_budget(input_tokens)
    try:
        answer = llm_ask(body.question)
    except Exception:
        release_budget(reservation)
        logger.error("llm_error")
        raise HTTPException(status_code=502, detail="Agent failed to answer") from None
    output_tokens = max(1, len(answer.split()) * 2)
    record_cost(reservation, input_tokens, output_tokens)
    return {"question": body.question, "answer": answer}

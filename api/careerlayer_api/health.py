import asyncio

from fastapi import APIRouter, Request, Response, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from .settings import get_settings

router = APIRouter(tags=["health"])

_OK = "ok"


@router.get("/health")
@router.get("/health/live")
@router.get("/v1/health")
@router.get("/v1/health/live")
async def liveness(request: Request) -> dict[str, str]:
    return {"status": "alive", "request_id": request.state.request_id}


@router.get("/health/ready")
@router.get("/v1/health/ready")
async def readiness(request: Request, response: Response) -> dict[str, object]:
    timeout = get_settings().dependency_probe_timeout
    postgres, cache = await asyncio.gather(
        _probe_postgres(request.app.state.engine, timeout),
        _probe_redis(request.app.state.redis, timeout),
    )
    checks = {"postgres": postgres, "redis": cache}
    ready = all(outcome == _OK for outcome in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "degraded",
        "checks": checks,
        "request_id": request.state.request_id,
    }


async def _probe_postgres(engine: AsyncEngine, timeout: float) -> str:
    """Returns "ok", or the exception class name so the caller can see which layer failed.

    The name rather than the message: connection errors carry the DSN, and the DSN
    carries the password.
    """
    try:
        async with asyncio.timeout(timeout), engine.connect() as connection:
            await connection.execute(text("select 1"))
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        return type(exc).__name__
    return _OK


async def _probe_redis(client: Redis, timeout: float) -> str:
    try:
        async with asyncio.timeout(timeout):
            await client.ping()
    except (RedisError, OSError, TimeoutError) as exc:
        return type(exc).__name__
    return _OK

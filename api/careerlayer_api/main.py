import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from .health import router as health_router
from .settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    # pool_pre_ping trades one round trip per checkout for not serving a request on a
    # connection Postgres closed while the pool was idle.
    app.state.engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    app.state.redis = Redis.from_url(settings.redis_url)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await app.state.engine.dispose()


app = FastAPI(title="CareerLayer API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def attach_request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Honours an inbound X-Request-Id so a trace survives the hop from the Next.js BFF."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


app.include_router(health_router)

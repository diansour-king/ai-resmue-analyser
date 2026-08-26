import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from . import observability
from .health import router as health_router
from .routes.auth import router as auth_router
from .routes.jobs import router as jobs_router
from .routes.matches import router as matches_router
from .routes.resumes import router as resumes_router
from .settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    observability.configure()
    settings = get_settings()
    # pool_pre_ping trades one round trip per checkout for not serving a request on a
    # connection Postgres closed while the pool was idle.
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.redis = Redis.from_url(settings.redis_url)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()


app = FastAPI(title="CareerLayer API", version="0.2.0", lifespan=lifespan)


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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Give every error one shape, so the frontend has one error component to build.

    A handler that raises HTTPException with a plain string detail still works: it is
    wrapped into the same envelope rather than leaking a bare string the client has to
    special-case.
    """
    # Starlette types detail as str; ours are dicts. Widen before narrowing so the
    # type checker can see both branches are reachable.
    detail: object = exc.detail
    body = detail if isinstance(detail, dict) else {"code": "error", "message": str(detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": body, "request_id": getattr(request.state, "request_id", None)},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Nothing internal crosses this boundary.

    The traceback goes to the log with the request id. What the caller gets back is that id
    and nothing else, because an exception message from this system can contain a storage
    endpoint, a DSN, or a fragment of somebody's resume.
    """
    request_id = getattr(request.state, "request_id", None)
    observability.log(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {"code": "internal", "message": "Something went wrong on our side."},
            "request_id": request_id,
        },
    )


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(resumes_router)
app.include_router(jobs_router)
app.include_router(matches_router)

import time
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Callable
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine, init_db_extensions, Base
from app.api.v1 import v1_router
from app.utils.security import rate_limiter

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("medsure")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: sets up DB extensions and runs startup checks."""
    logger.info("Initializing MedSure Vision backend...")
    await init_db_extensions()
    # In SQLite or testing mode, ensure tables exist automatically
    if "sqlite" in settings.DATABASE_URL:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Production database integrity check: refuse to start if any fixture-flagged alert exists
    async with engine.connect() as conn:
        try:
            res = await conn.execute(
                text(
                    "SELECT count(*) FROM regulatory_alert "
                    "WHERE is_fixture = 1 OR is_demo = 1 "
                    "OR batch_number LIKE 'TEST-%' OR batch_number LIKE 'DL650-RECALL%'"
                )
            )
            fixture_alert_count = res.scalar() or 0
            if fixture_alert_count > 0:
                raise RuntimeError(
                    f"Integrity check failed: {fixture_alert_count} fixture-flagged alerts found in database. "
                    "Production app refuses to start with synthetic/fixture data."
                )
        except RuntimeError:
            raise
        except Exception as e:
            if "no such table" not in str(e).lower():
                logger.warning(f"Startup alert check notice: {e}")

    logger.info("MedSure Vision startup complete.")
    yield
    logger.info("Shutting down MedSure Vision backend...")
    await engine.dispose()


app = FastAPI(
    title="MedSure Vision API",
    description=(
        "Production-grade Indian Medicine Master Database & Verification Backend. "
        "Provides medicine search, GTIN/barcode lookup, OCR packaging analysis, and regulatory alerts."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
origins = (
    settings.ALLOWED_ORIGINS
    if isinstance(settings.ALLOWED_ORIGINS, list)
    else [origin.strip() for origin in str(settings.ALLOWED_ORIGINS).split(",")]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_and_rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """Attaches correlation ID, enforces rate limiting, and logs request lifecycle."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    # Rate limiting (exempt health and documentation endpoints)
    path = request.url.path
    if not (path.startswith("/docs") or path.startswith("/redoc") or path == "/health" or path == "/"):
        client_ip = request.client.host if request.client else "127.0.0.1"
        if not rate_limiter.check(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit of {settings.RATE_LIMIT_PER_MINUTE} requests per minute exceeded.",
                        "details": {"client_ip": client_ip},
                    }
                },
                headers={"X-Correlation-ID": correlation_id},
            )

    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        logger.info(
            f"[{correlation_id}] {request.method} {request.url.path} - {response.status_code} ({duration_ms}ms)"
        )
        return response
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"[{correlation_id}] Request failed after {duration_ms}ms: {exc}", exc_info=True)
        raise exc


# Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": getattr(request.state, "details", {}),
            }
        },
        headers={"X-Correlation-ID": getattr(request.state, "correlation_id", "")},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed for request payload or parameters.",
                "details": {"errors": exc.errors()},
            }
        },
        headers={"X-Correlation-ID": getattr(request.state, "correlation_id", "")},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception processing request: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the request.",
                "details": {"exception": str(exc)} if settings.DEBUG else {},
            }
        },
        headers={"X-Correlation-ID": getattr(request.state, "correlation_id", "")},
    )


# Include API Routers
app.include_router(v1_router, prefix="/api")


@app.get("/", tags=["Health"])
async def root():
    """Service status and meta."""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs",
        "health_check": "/health",
    }


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint validating database connectivity and reporting the real database engine."""
    db_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "database": db_status,
        "database_engine": engine.dialect.name,
        "timestamp": time.time(),
    }

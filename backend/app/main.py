"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log = get_logger("startup")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.warmup_models:  # load models at startup instead of on the first request
        from app.rag.embeddings import get_embedder
        from app.rag.reranker import get_reranker

        get_embedder()
        if settings.reranker_enabled:
            get_reranker()
    log.info(
        "app_started",
        env=settings.env,
        ingestion_mode=settings.ingestion_mode,
        llm_primary=settings.llm_primary,
        llm_fallback=settings.llm_fallback,
        reranker=settings.reranker_enabled,
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(
        title="TechPrep AI API",
        description="Chat with your interview-prep notes and PDFs, with page-level citations.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,  # we use bearer tokens, not cookies
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health.router)
    app.include_router(api_router)
    return app


app = create_app()

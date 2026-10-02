"""Liveness and readiness probes.

/health        -> the process is up (used by Docker/K8s to restart a dead container)
/health/ready  -> dependencies are reachable (used to decide whether to send traffic)
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/ready")
def ready():
    settings = get_settings()
    checks: dict[str, str] = {}

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # report, don't crash the probe
        checks["database"] = f"error: {type(exc).__name__}"

    if settings.ingestion_mode == "celery" and settings.redis_url:
        try:
            import redis

            redis.Redis.from_url(settings.redis_url, socket_timeout=2).ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {type(exc).__name__}"

    from app.rag.embeddings import embedder_loaded

    checks["embedding_model"] = "loaded" if embedder_loaded() else "lazy (loads on first use)"

    healthy = all(not v.startswith("error") for v in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )

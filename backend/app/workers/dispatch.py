"""Decide where document ingestion runs.

- INGESTION_MODE=celery: push a task to Redis; a separate worker process does the work.
- INGESTION_MODE=inline: run after the HTTP response in this process (lite mode, no Redis).

The API returns 202 immediately in both modes; the client polls the document status.
"""

from uuid import UUID

from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


def dispatch_ingestion(document_id: UUID, background: BackgroundTasks | None = None) -> None:
    # Phase 1 placeholder: ingestion pipeline arrives in phase 2.
    log.info("ingestion_queued", document_id=str(document_id), mode=get_settings().ingestion_mode)

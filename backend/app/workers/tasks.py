from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.services.ingestion_service import ingest_document
from app.workers.celery_app import celery_app


@celery_app.task(
    name="documents.ingest",
    autoretry_for=(OperationalError,),  # database blip: retry; bad file: don't
    retry_backoff=True,
    retry_backoff_max=120,
    max_retries=3,
)
def ingest_document_task(document_id: str) -> str | None:
    status = ingest_document(UUID(document_id))
    return status.value if status else None

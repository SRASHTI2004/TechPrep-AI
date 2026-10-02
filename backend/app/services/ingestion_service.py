"""Document ingestion: load → chunk → embed → store. Runs in the Celery worker or inline.

Status lifecycle: pending → processing → ready | failed (with a user-readable error).
"""

from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.document import DocumentStatus
from app.rag.chunking import chunk_document
from app.rag.embeddings import get_embedder
from app.rag.loaders import LoaderError, load_document
from app.repositories.chunks import ChunkRepository
from app.repositories.documents import DocumentRepository

log = get_logger(__name__)


class IngestionError(Exception):
    """Permanent, user-facing failure (bad file). Not retried."""


def ingest_document(document_id: UUID) -> DocumentStatus | None:
    """Ingest one document. Transient DB errors are re-raised so Celery can retry them."""
    settings = get_settings()
    with SessionLocal() as db:
        repo = DocumentRepository(db)
        document = repo.get_unscoped(document_id)
        if document is None:
            log.warning("ingest_missing_document", document_id=str(document_id))
            return None
        document.status = DocumentStatus.PROCESSING
        document.error = None
        db.commit()
        bound = log.bind(document_id=str(document_id), filename=document.filename)

        try:
            loaded = load_document(Path(document.storage_path), document.content_type)
            drafts = chunk_document(
                loaded, settings.chunk_size, settings.chunk_overlap, settings.min_chunk_chars
            )
            if not drafts:
                raise IngestionError(
                    "No text could be extracted. Scanned/image-only PDFs need OCR, "
                    "which is not supported yet."
                )
            embedder = get_embedder()
            embeddings = embedder.embed_documents([d.embedding_text for d in drafts])
            n = ChunkRepository(db).replace_for_document(
                document, drafts, embeddings, embedder.model_name
            )
            document.status = DocumentStatus.READY
            document.num_chunks = n
            document.num_pages = loaded.num_pages
            db.commit()
            bound.info("ingest_done", chunks=n, pages=loaded.num_pages)
            return DocumentStatus.READY
        except OperationalError:
            db.rollback()
            bound.exception("ingest_db_error")
            raise
        except (IngestionError, LoaderError) as exc:
            db.rollback()
            _mark_failed(db, document_id, str(exc))
            bound.warning("ingest_failed", error=str(exc))
            return DocumentStatus.FAILED
        except Exception as exc:
            db.rollback()
            _mark_failed(db, document_id, "Unexpected error while processing this file.")
            bound.exception("ingest_crashed", error=str(exc))
            return DocumentStatus.FAILED


def _mark_failed(db, document_id: UUID, message: str) -> None:
    document = DocumentRepository(db).get_unscoped(document_id)
    if document is not None:
        document.status = DocumentStatus.FAILED
        document.error = message[:1000]
        db.commit()

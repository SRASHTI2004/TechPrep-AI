from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.models.document import DocumentStatus
from app.repositories.documents import DocumentRepository
from app.schemas.document import DocumentList, DocumentOut
from app.services.document_service import DocumentService, DuplicateDocumentError, UploadError
from app.workers.dispatch import dispatch_ingestion

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


@router.post("", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.rate_limit_upload)
def upload_document(
    request: Request,
    file: UploadFile,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
):
    """Store the file and queue it for ingestion. Poll GET /documents/{id} for status."""
    try:
        document = DocumentService(db).create_from_upload(user.id, file.filename, file.file)
    except DuplicateDocumentError as exc:
        raise HTTPException(
            exc.status_code, {"message": str(exc), "document_id": str(exc.existing.id)}
        ) from exc
    except UploadError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    dispatch_ingestion(document.id, background)
    return document


@router.get("", response_model=DocumentList)
def list_documents(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    repo = DocumentRepository(db)
    return DocumentList(
        items=repo.list_for_owner(user.id, limit, offset), total=repo.count_for_owner(user.id)
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: UUID, user: CurrentUser, db: DbSession):
    document = DocumentRepository(db).get_for_owner(document_id, user.id)
    if document is None:  # 404 (not 403) so we don't leak that someone else's id exists
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


@router.post("/{document_id}/reingest", response_model=DocumentOut, status_code=202)
def reingest_document(
    document_id: UUID, user: CurrentUser, db: DbSession, background: BackgroundTasks
):
    """Retry a failed ingestion, or re-chunk after changing chunking settings."""
    document = DocumentRepository(db).get_for_owner(document_id, user.id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if document.status in (DocumentStatus.PENDING, DocumentStatus.PROCESSING):
        raise HTTPException(status.HTTP_409_CONFLICT, "Document is already being processed")
    document.status = DocumentStatus.PENDING
    document.error = None
    db.commit()
    dispatch_ingestion(document.id, background)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, user: CurrentUser, db: DbSession):
    service = DocumentService(db)
    document = service.repo.get_for_owner(document_id, user.id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    service.delete(document)

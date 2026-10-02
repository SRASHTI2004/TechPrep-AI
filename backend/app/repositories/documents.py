"""Document data access. Every read method takes owner_id: there is no "get any document" path."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()
        return document

    def get_for_owner(self, document_id: UUID, owner_id: UUID) -> Document | None:
        return self.db.scalar(
            select(Document).where(Document.id == document_id, Document.owner_id == owner_id)
        )

    def get_by_hash(self, owner_id: UUID, sha256: str) -> Document | None:
        return self.db.scalar(
            select(Document).where(Document.owner_id == owner_id, Document.sha256 == sha256)
        )

    def list_for_owner(self, owner_id: UUID, limit: int = 100, offset: int = 0) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt))

    def count_for_owner(self, owner_id: UUID) -> int:
        stmt = select(func.count()).select_from(Document).where(Document.owner_id == owner_id)
        return self.db.scalar(stmt) or 0

    def delete(self, document: Document) -> None:
        self.db.delete(document)

    # Used only by the ingestion worker, which receives an id it created itself.
    def get_unscoped(self, document_id: UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def count_by_status(self) -> dict[str, int]:
        rows = self.db.execute(select(Document.status, func.count()).group_by(Document.status))
        counts = {s.value: 0 for s in DocumentStatus}
        counts.update({status.value: n for status, n in rows})
        return counts

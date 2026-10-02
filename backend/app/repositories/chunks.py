import hashlib
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.document import Document
from app.rag.chunking import ChunkDraft


class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def replace_for_document(
        self,
        document: Document,
        drafts: list[ChunkDraft],
        embeddings: list[list[float]],
        embedding_model: str,
    ) -> int:
        """Atomically swap a document's chunks (re-ingestion never leaves stale chunks)."""
        self.db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        self.db.add_all(
            Chunk(
                document_id=document.id,
                owner_id=document.owner_id,
                chunk_index=d.chunk_index,
                content=d.content,
                section=d.section,
                page=d.page,
                content_hash=hashlib.sha256(d.content.encode()).hexdigest(),
                embedding=vec,
                embedding_model=embedding_model,
            )
            for d, vec in zip(drafts, embeddings, strict=True)
        )
        self.db.flush()
        return len(drafts)

    def count_for_owner(self, owner_id: UUID) -> int:
        stmt = select(func.count()).select_from(Chunk).where(Chunk.owner_id == owner_id)
        return self.db.scalar(stmt) or 0

    def list_for_document(self, document_id: UUID, owner_id: UUID) -> list[Chunk]:
        stmt = (
            select(Chunk)
            .where(Chunk.document_id == document_id, Chunk.owner_id == owner_id)
            .order_by(Chunk.chunk_index)
        )
        return list(self.db.scalars(stmt))

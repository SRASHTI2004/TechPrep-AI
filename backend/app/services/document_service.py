"""Upload validation, storage and deletion of documents.

Security rules:
- The user's filename is used for display only. Files are stored at
  `<upload_dir>/<owner_id>/<document_id><ext>`, so path traversal ("../../x") is impossible.
- Size is capped while streaming, so a huge upload can't fill memory or disk.
- Content is sniffed (PDF magic bytes, UTF-8 text) instead of trusting the extension.
"""

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.document import Document, DocumentStatus
from app.repositories.documents import DocumentRepository

log = get_logger(__name__)

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}


class UploadError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class DuplicateDocumentError(UploadError):
    def __init__(self, existing: Document):
        super().__init__(f"You already uploaded this file as '{existing.filename}'", 409)
        self.existing = existing


def sanitize_filename(name: str | None) -> str:
    name = Path(name or "document").name  # drop any directory components
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r"[\x00-\x1f\x7f<>:\"/\\|?*]", "_", name).strip(" .")
    return (name or "document")[:255]


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DocumentRepository(db)
        self.settings = get_settings()

    def create_from_upload(
        self, owner_id: UUID, filename: str | None, stream: BinaryIO
    ) -> Document:
        display_name = sanitize_filename(filename)
        ext = Path(display_name).suffix.lower()
        if ext not in ALLOWED_TYPES:
            raise UploadError("Only .pdf, .md and .txt files are supported", 415)

        data = self._read_capped(stream)
        if not data:
            raise UploadError("The file is empty")
        self._check_content(ext, data)

        sha256 = hashlib.sha256(data).hexdigest()
        if existing := self.repo.get_by_hash(owner_id, sha256):
            raise DuplicateDocumentError(existing)

        doc_id = uuid4()
        owner_dir = self.settings.upload_dir / str(owner_id)
        owner_dir.mkdir(parents=True, exist_ok=True)
        storage_path = owner_dir / f"{doc_id}{ext}"
        storage_path.write_bytes(data)

        document = Document(
            id=doc_id,
            owner_id=owner_id,
            filename=display_name,
            storage_path=str(storage_path),
            content_type=ALLOWED_TYPES[ext],
            size_bytes=len(data),
            sha256=sha256,
            status=DocumentStatus.PENDING,
        )
        try:
            self.repo.add(document)
            self.db.commit()
        except Exception:
            self.db.rollback()
            storage_path.unlink(missing_ok=True)
            raise
        log.info("document_uploaded", document_id=str(doc_id), size=len(data), ext=ext)
        return document

    def delete(self, document: Document) -> None:
        path = Path(document.storage_path)
        self.repo.delete(document)  # chunks are removed by ON DELETE CASCADE
        self.db.commit()
        path.unlink(missing_ok=True)
        log.info("document_deleted", document_id=str(document.id))

    def _read_capped(self, stream: BinaryIO) -> bytes:
        limit = self.settings.max_upload_bytes
        buf = bytearray()
        while chunk := stream.read(1024 * 1024):
            buf.extend(chunk)
            if len(buf) > limit:
                raise UploadError(f"File is larger than {self.settings.max_upload_mb} MB", 413)
        return bytes(buf)

    @staticmethod
    def _check_content(ext: str, data: bytes) -> None:
        if ext == ".pdf":
            if not data.startswith(b"%PDF-"):
                raise UploadError("File does not look like a valid PDF")
            return
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UploadError("Text files must be UTF-8 encoded") from exc

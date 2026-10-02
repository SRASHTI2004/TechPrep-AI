"""Admin-only endpoints. Admins see aggregate stats, never other users' document content."""

from fastapi import APIRouter

from app.api.deps import AdminUser, DbSession
from app.repositories.documents import DocumentRepository
from app.repositories.query_logs import QueryLogRepository
from app.repositories.users import UserRepository

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
def stats(_: AdminUser, db: DbSession):
    return {
        "users": UserRepository(db).count(),
        "documents_by_status": DocumentRepository(db).count_by_status(),
        "queries": QueryLogRepository(db).stats(),
    }

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import Role, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def create(self, email: str, hashed_password: str, role: Role = Role.USER) -> User:
        user = User(email=email.lower(), hashed_password=hashed_password, role=role)
        self.db.add(user)
        self.db.flush()
        return user

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(User)) or 0

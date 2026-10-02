from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Role, User
from app.repositories.users import UserRepository


class AuthError(Exception):
    pass


class EmailTakenError(AuthError):
    pass


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, email: str, password: str) -> User:
        if self.users.get_by_email(email):
            raise EmailTakenError("Email already registered")
        admin_email = get_settings().first_admin_email
        role = Role.ADMIN if admin_email and email.lower() == admin_email.lower() else Role.USER
        user = self.users.create(email, hash_password(password), role)
        self.db.commit()
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        # Same error for unknown email and wrong password: don't reveal which accounts exist.
        if not user or not user.is_active or not verify_password(password, user.hashed_password):
            raise AuthError("Incorrect email or password")
        return user

    @staticmethod
    def issue_token(user: User) -> tuple[str, int]:
        return create_access_token(user.id, user.role.value)

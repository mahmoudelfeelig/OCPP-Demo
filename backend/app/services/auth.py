from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.entities import User
from app.repositories.users import UserRepository


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = UserRepository(db).get_by_email(email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def issue_token(user: User) -> str:
    return create_access_token(user.id, user.role.name)


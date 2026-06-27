from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.entities import Role, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).options(joinedload(User.role)).where(User.email == email)
        return self.db.scalar(stmt)

    def get_by_id(self, user_id: str) -> User | None:
        stmt = select(User).options(joinedload(User.role)).where(User.id == user_id)
        return self.db.scalar(stmt)

    def get_role(self, role_name: str) -> Role | None:
        return self.db.scalar(select(Role).where(Role.name == role_name))


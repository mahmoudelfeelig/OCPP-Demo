from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.services.auth import authenticate_user, issue_token

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return LoginResponse(access_token=issue_token(user), email=user.email, role=user.role.name)


@router.get("/me")
async def me(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
    return {"email": current_user.email, "role": current_user.role}

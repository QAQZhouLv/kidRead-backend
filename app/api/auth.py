from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.auth_service import build_login_response, resolve_openid, upsert_user

router = APIRouter(prefix="/api/auth", tags=["auth"])



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AuthLoginRequest(BaseModel):
    code: str | None = None
    dev_openid: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    display_name: str | None = None


@router.post("/login")
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)):
    try:
        openid, unionid, auth_mode = resolve_openid(
            code=payload.code,
            dev_openid=payload.dev_openid,
        )
        user = upsert_user(
            db,
            openid=openid,
            unionid=unionid,
            nickname=payload.nickname,
            avatar_url=payload.avatar_url,
            display_name=payload.display_name,
            auth_mode=auth_mode,
        )
        return build_login_response(user, auth_mode)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

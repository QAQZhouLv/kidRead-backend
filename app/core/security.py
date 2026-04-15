import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict

from fastapi import Header, HTTPException, WebSocket
from sqlalchemy.orm import Session

from app.core.config import ACCESS_TOKEN_EXPIRE_DAYS, TOKEN_SECRET
from app.models.user import User


class AuthError(Exception):
    pass



def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")



def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)



def create_access_token(openid: str) -> str:
    expire_at = int(time.time()) + ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    payload = {
        "openid": openid,
        "exp": expire_at,
    }
    payload_segment = _b64url_encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_segment}.{_b64url_encode(signature)}"



def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError as exc:
        raise AuthError("token 格式不正确") from exc

    expected_signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_signature = _b64url_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise AuthError("token 签名校验失败")

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except Exception as exc:
        raise AuthError("token 内容解析失败") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise AuthError("token 已过期")

    openid = str(payload.get("openid") or "").strip()
    if not openid:
        raise AuthError("token 中缺少 openid")
    return payload



def parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    value = authorization.strip()
    if not value:
        return None
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return value



def get_current_user(
    db: Session,
    authorization: str | None,
) -> User:
    token = parse_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="缺少登录态 token")

    try:
        payload = decode_access_token(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    openid = str(payload["openid"])
    user = db.query(User).filter(User.wx_openid == openid).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或登录态失效")
    return user



def get_current_user_dependency(
    authorization: str | None = Header(default=None),
    db: Session | None = None,
) -> User:
    if db is None:
        raise HTTPException(status_code=500, detail="数据库依赖缺失")
    return get_current_user(db=db, authorization=authorization)



def get_current_user_from_ws(db: Session, websocket: WebSocket) -> User:
    token = websocket.query_params.get("token") or ""
    if not token:
        raise AuthError("缺少登录态 token")

    payload = decode_access_token(token)
    openid = str(payload["openid"])
    user = db.query(User).filter(User.wx_openid == openid).first()
    if not user:
        raise AuthError("用户不存在或登录态失效")
    return user

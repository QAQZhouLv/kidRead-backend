from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

import requests
from sqlalchemy.orm import Session

from app.core.config import DEBUG, WX_APP_ID, WX_APP_SECRET
from app.core.security import create_access_token
from app.models.user import User

WECHAT_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"



def normalize_openid_candidate(value: Optional[str]) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return raw[:255]



def build_dev_openid(dev_openid: Optional[str]) -> str:
    candidate = normalize_openid_candidate(dev_openid)
    if not candidate:
        candidate = "local-default"
    if not candidate.startswith("dev_"):
        candidate = f"dev_{candidate}"
    return candidate[:255]



def exchange_code_for_openid(code: str) -> Tuple[str, str | None, str]:
    if not (WX_APP_ID and WX_APP_SECRET and code):
        raise RuntimeError("未配置微信登录环境或 code 为空")

    response = requests.get(
        WECHAT_CODE2SESSION_URL,
        params={
            "appid": WX_APP_ID,
            "secret": WX_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        },
        timeout=8,
    )
    response.raise_for_status()
    data = response.json()

    openid = normalize_openid_candidate(data.get("openid"))
    unionid = normalize_openid_candidate(data.get("unionid")) or None
    errcode = data.get("errcode")
    errmsg = data.get("errmsg")

    if openid:
        return openid, unionid, "wechat"

    raise RuntimeError(f"微信登录失败: errcode={errcode}, errmsg={errmsg}")



def resolve_openid(code: Optional[str], dev_openid: Optional[str]) -> tuple[str, str | None, str]:
    clean_code = str(code or "").strip()
    if clean_code:
        try:
            return exchange_code_for_openid(clean_code)
        except Exception:
            # 本地开发、开发者工具或未配置 appid/secret 时，回退到虚拟 openid。
            pass

    if not DEBUG and not clean_code:
        raise RuntimeError("当前环境未获取到微信 code，且不允许使用开发 openid")

    return build_dev_openid(dev_openid), None, "dev"



def upsert_user(
    db: Session,
    *,
    openid: str,
    unionid: str | None = None,
    nickname: str | None = None,
    avatar_url: str | None = None,
    display_name: str | None = None,
    auth_mode: str = "dev",
) -> User:
    user = db.query(User).filter(User.wx_openid == openid).first()
    now = datetime.utcnow()

    if not user:
        user = User(
            wx_openid=openid,
            wx_unionid=unionid,
            nickname=(nickname or "").strip() or None,
            avatar_url=(avatar_url or "").strip() or None,
            display_name=(display_name or nickname or "").strip() or None,
            is_demo_user=(auth_mode == "dev") or openid.startswith("dev_"),
            last_login_at=now,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    if unionid and not user.wx_unionid:
        user.wx_unionid = unionid
    if nickname:
        user.nickname = nickname.strip()
    if avatar_url:
        user.avatar_url = avatar_url.strip()
    if display_name:
        user.display_name = display_name.strip()
    elif nickname and not user.display_name:
        user.display_name = nickname.strip()

    user.is_demo_user = (auth_mode == "dev") or openid.startswith("dev_")
    user.last_login_at = now
    user.updated_at = now

    db.commit()
    db.refresh(user)
    return user



def build_login_response(user: User, auth_mode: str) -> dict:
    return {
        "token": create_access_token(user.wx_openid),
        "auth_mode": auth_mode,
        "user": {
            "id": user.id,
            "wx_openid": user.wx_openid,
            "nickname": user.nickname,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "is_demo_user": bool(user.is_demo_user),
        },
    }

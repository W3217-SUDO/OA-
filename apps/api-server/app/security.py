from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .models import User

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def user_role_ids(user: User) -> list[str]:
    """Return a stable, backward-compatible role set for one account."""
    legacy_role = str(user.role or "user").strip() or "user"
    role_ids = [str(value).strip() for value in (user.role_ids or []) if str(value).strip()]
    if legacy_role not in role_ids:
        role_ids.insert(0, legacy_role)
    if "admin" in role_ids:
        return ["admin", *(role for role in role_ids if role != "admin")]
    return list(dict.fromkeys(role_ids)) or ["user"]


def create_token(username: str, role: str, expires_minutes: int | None = None) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or settings.access_token_minutes)
    return jwt.encode({"sub": username, "role": role, "exp": expires}, settings.secret_key, algorithm="HS256")


async def current_identity(request: Request, token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        username = payload["sub"]
    except (jwt.PyJWTError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期") from exc
    user = await db.scalar(select(User).where(User.username == username))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号已停用或不存在")
    if user.must_change_password and request.url.path != f"{settings.api_prefix}/auth/me":
        raise HTTPException(status_code=428, detail="首次登录必须先修改初始密码")
    role_ids = user_role_ids(user)
    return {"username": user.username, "role": role_ids[0], "role_ids": role_ids, "display_name": user.display_name, "department": user.department, "must_change_password": user.must_change_password}

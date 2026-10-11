"""钉钉端内与扫码登录共用的 OA 员工绑定逻辑。"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.formatters import _dingtalk_allowed_display_names
from app.core.permissions import _ensure_unique_dingtalk_user_id, _require_dingtalk_access
from app.models import User
from app.security import verify_password


async def login_verified_employee(ding_user: dict, db: AsyncSession) -> dict | None:
    from app.core.system import _login_response

    users = (await db.scalars(select(User).where(User.is_active.is_(True)))).all()
    matched = [user for user in users if str((user.profile or {}).get("dingtalk_user_id") or "").strip() == ding_user["user_id"]]
    if not matched and ding_user.get("mobile"):
        matched = [user for user in users if str((user.profile or {}).get("mobile") or "").strip() == ding_user["mobile"]]
        if len(matched) == 1:
            matched[0].profile = {**(matched[0].profile or {}), "dingtalk_user_id": ding_user["user_id"]}
    ding_name = str(ding_user.get("name") or "").strip()
    if not matched and ding_name in _dingtalk_allowed_display_names():
        matched = [user for user in users if str(user.display_name or "").strip() == ding_name]
        if len(matched) == 1:
            matched[0].profile = {**(matched[0].profile or {}), "dingtalk_user_id": ding_user["user_id"]}
    if len(matched) != 1:
        return None
    user = matched[0]
    _require_dingtalk_access(user)
    user.last_login_at = datetime.now()
    await db.commit()
    return await _login_response(user, db, require_password_change=False)


async def bind_verified_employee(ding_user: dict, username: str, password: str, db: AsyncSession) -> dict:
    from app.core.system import _login_response

    user = await db.scalar(select(User).where(User.username == username.strip().lower(), User.is_active.is_(True)))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="OA 账号或密码错误")
    _require_dingtalk_access(user)
    profile = {**(user.profile or {}), "dingtalk_user_id": ding_user["user_id"]}
    await _ensure_unique_dingtalk_user_id(profile, db, user.id, user.display_name)
    user.profile = profile
    user.last_login_at = datetime.now()
    await db.commit()
    return await _login_response(user, db)

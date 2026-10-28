"""钉钉端内与扫码登录共用的 OA 员工绑定逻辑。"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.formatters import _dingtalk_allowed_display_names
from app.core.permissions import _ensure_unique_dingtalk_user_id, _profile_dingtalk_login_ids, _require_dingtalk_access
from app.models import User
from app.security import verify_password


async def login_verified_employee(ding_user: dict, db: AsyncSession) -> dict | None:
    from app.core.system import _login_response

    users = (await db.scalars(select(User).where(User.is_active.is_(True)))).all()
    matched = [user for user in users if ding_user["user_id"] in _profile_dingtalk_login_ids(user.profile)]
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
    _remember_dingtalk_name(user, ding_user)
    user.last_login_at = datetime.now()
    await db.commit()
    return await _login_response(user, db, require_password_change=False)


async def bind_verified_employee(ding_user: dict, username: str, password: str, db: AsyncSession) -> dict:
    from app.core.system import _login_response

    user = await db.scalar(select(User).where(User.username == username.strip().lower(), User.is_active.is_(True)))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="OA 账号或密码错误")
    _require_dingtalk_access(user)
    profile = dict(user.profile or {})
    if str(profile.get("dingtalk_user_id") or "").strip() in ("", ding_user["user_id"]):
        profile["dingtalk_user_id"] = ding_user["user_id"]
    else:
        # 共用账号的另一位绑定时追加，不顶掉已有绑定，否则两人会轮流被要求重新绑定。
        profile["dingtalk_login_ids"] = list(dict.fromkeys([*(profile.get("dingtalk_login_ids") or []), ding_user["user_id"]]))
    await _ensure_unique_dingtalk_user_id({"dingtalk_user_id": ding_user["user_id"]}, db, user.id, user.display_name)
    user.profile = profile
    _remember_dingtalk_name(user, ding_user)
    user.last_login_at = datetime.now()
    await db.commit()
    return await _login_response(user, db)


def _remember_dingtalk_name(user: User, ding_user: dict) -> None:
    """记下钉钉姓名，员工账号里列出多个绑定时能看出是谁。"""
    name = str(ding_user.get("name") or "").strip()
    names = dict((user.profile or {}).get("dingtalk_names") or {})
    if name and names.get(ding_user["user_id"]) != name:
        user.profile = {**(user.profile or {}), "dingtalk_names": {**names, ding_user["user_id"]: name}}


def remove_dingtalk_binding(user: User, ding_user_id: str, actor: str) -> None:
    """解除一个钉钉身份：主身份被解除时由下一个附加身份接替接收通知；解除记录留在资料里（逻辑删除），改动另有数据留痕。"""
    profile = dict(user.profile or {})
    remaining = [value for value in _profile_dingtalk_login_ids(profile) if value != ding_user_id]
    if len(remaining) == len(_profile_dingtalk_login_ids(profile)):
        raise HTTPException(status_code=404, detail="该账号没有绑定这个钉钉身份")
    if remaining:
        profile["dingtalk_user_id"] = remaining[0]
    else:
        profile.pop("dingtalk_user_id", None)
    if remaining[1:]:
        profile["dingtalk_login_ids"] = remaining[1:]
    else:
        profile.pop("dingtalk_login_ids", None)
    name = str((profile.get("dingtalk_names") or {}).get(ding_user_id) or "")
    profile["dingtalk_unbound"] = [*(profile.get("dingtalk_unbound") or []), {
        "user_id": ding_user_id, "name": name, "by": actor, "at": datetime.now().isoformat(timespec="seconds"),
    }]
    user.profile = profile


async def dingtalk_bindings(user: User) -> list[dict]:
    from app.dingtalk import dingtalk_client

    names = (user.profile or {}).get("dingtalk_names") or {}
    items = []
    for index, ding_user_id in enumerate(_profile_dingtalk_login_ids(user.profile)):
        name = str(names.get(ding_user_id) or "")
        if not name and dingtalk_client.configured:
            try:
                name = await dingtalk_client.user_name(ding_user_id)
            except Exception:  # 查不到姓名不影响列出绑定
                name = ""
        items.append({"user_id": ding_user_id, "name": name, "primary": index == 0})
    return items

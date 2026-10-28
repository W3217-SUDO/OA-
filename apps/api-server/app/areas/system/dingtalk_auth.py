"""钉钉端内与扫码登录共用的 OA 员工绑定逻辑。"""

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.formatters import _dingtalk_allowed_display_names
from app.core.permissions import _ensure_unique_dingtalk_user_id, _profile_dingtalk_login_ids, _require_dingtalk_access
from app.config import settings
from app.models import User
from app.security import verify_password


CHOOSE_TICKET_SECONDS = 600


def choose_ticket(ding_user_id: str) -> str:
    """钉钉免登码只能用一次；选账号、登录其他账号时凭这个短时票据证明钉钉身份。"""
    now = datetime.now(timezone.utc)
    return jwt.encode({"user_id": ding_user_id, "iss": "oa-dingtalk-choose", "aud": "dingtalk-choose", "iat": now,
                       "exp": now + timedelta(seconds=CHOOSE_TICKET_SECONDS), "jti": secrets.token_urlsafe(16)},
                      settings.secret_key, algorithm="HS256")


def verify_choose_ticket(value: str) -> str:
    try:
        claims = jwt.decode(value, settings.secret_key, algorithms=["HS256"], audience="dingtalk-choose", issuer="oa-dingtalk-choose",
                            options={"require": ["exp", "iat", "jti", "aud", "iss"]})
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=400, detail="钉钉登录已过期，请从钉钉工作台重新打开") from exc
    user_id = claims.get("user_id")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=400, detail="钉钉身份无效，请从钉钉工作台重新打开")
    return user_id


def _add_dingtalk_binding(user: User, ding_user_id: str) -> None:
    """一个钉钉可绑定多个 OA 账号、一个账号也可绑定多个钉钉；已有主身份时追加，不顶掉别人。"""
    profile = dict(user.profile or {})
    if str(profile.get("dingtalk_user_id") or "").strip() in ("", ding_user_id):
        profile["dingtalk_user_id"] = ding_user_id
    else:
        profile["dingtalk_login_ids"] = list(dict.fromkeys([*(profile.get("dingtalk_login_ids") or []), ding_user_id]))
    user.profile = profile


async def bound_employees(ding_user: dict, db: AsyncSession) -> list[User]:
    users = (await db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.id))).all()
    matched = [user for user in users if ding_user["user_id"] in _profile_dingtalk_login_ids(user.profile)]
    if not matched and ding_user.get("mobile"):
        matched = [user for user in users if str((user.profile or {}).get("mobile") or "").strip() == ding_user["mobile"]]
        if len(matched) == 1:
            _add_dingtalk_binding(matched[0], ding_user["user_id"])
        else:
            matched = []
    ding_name = str(ding_user.get("name") or "").strip()
    if not matched and ding_name in _dingtalk_allowed_display_names():
        matched = [user for user in users if str(user.display_name or "").strip() == ding_name]
        if len(matched) == 1:
            _add_dingtalk_binding(matched[0], ding_user["user_id"])
        else:
            matched = []
    allowed = _dingtalk_allowed_display_names()
    permitted = [user for user in matched if not allowed or str(user.display_name or "").strip() in allowed]
    if matched and not permitted:
        _require_dingtalk_access(matched[0])  # 绑定的账号都没开通钉钉登录：提示“未开通”而不是“未绑定”
    return permitted


async def _account_options(users: list[User], db: AsyncSession) -> list[dict]:
    from app.models import RolePermission

    role_names = {item.role: item.display_name for item in (await db.scalars(select(RolePermission))).all()}
    return [{"username": user.username, "display_name": user.display_name or user.username, "department": user.department or "",
             "role": role_names.get(user.role, "")} for user in users]


async def login_bound_employee(user: User, ding_user: dict, db: AsyncSession) -> dict:
    from app.core.system import _login_response

    _require_dingtalk_access(user)
    _remember_dingtalk_name(user, ding_user)
    user.last_login_at = datetime.now()
    await db.commit()
    return await _login_response(user, db, require_password_change=False)


async def login_verified_employee(ding_user: dict, db: AsyncSession, *, preferred: str = "", choose: bool = False,
                                  allow_choose: bool = False) -> dict | None:
    """钉钉免登。绑定一个账号直接进；绑定多个时进上次用的账号，退出后或没有上次记录时让用户选账号。"""
    matched = await bound_employees(ding_user, db)
    if not matched:
        return None
    preferred_user = next((user for user in matched if user.username == preferred.strip().lower()), None)
    if allow_choose and (choose or (len(matched) > 1 and preferred_user is None)):
        await db.commit()
        return {"choose_account": True, "ticket": choose_ticket(ding_user["user_id"]), "accounts": await _account_options(matched, db)}
    if preferred_user is None:
        # 扫码登录等不弹选择的入口：进最近登录过的账号。
        preferred_user = max(matched, key=lambda user: user.last_login_at.timestamp() if user.last_login_at else 0)
    return await login_bound_employee(preferred_user, ding_user, db)


async def login_chosen_employee(ticket: str, username: str, db: AsyncSession) -> dict:
    ding_user = {"user_id": verify_choose_ticket(ticket)}
    user = next((item for item in await bound_employees(ding_user, db) if item.username == username.strip().lower()), None)
    if user is None:
        raise HTTPException(status_code=403, detail="该钉钉没有绑定这个账号")
    return await login_bound_employee(user, ding_user, db)


async def bind_verified_employee(ding_user: dict, username: str, password: str, db: AsyncSession) -> dict:
    from app.core.system import _login_response

    user = await db.scalar(select(User).where(User.username == username.strip().lower(), User.is_active.is_(True)))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="OA 账号或密码错误")
    _require_dingtalk_access(user)
    await _ensure_unique_dingtalk_user_id({"dingtalk_user_id": ding_user["user_id"]}, db, user.id, user.display_name)
    _add_dingtalk_binding(user, ding_user["user_id"])
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

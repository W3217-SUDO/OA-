"""进程内“账号 → 姓名”对照：给附件上传人、记录负责人等统一补姓名。

账号约百条，每个工作进程缓存一份，登录身份校验时按需刷新（最长 60 秒），
改了姓名约一分钟内全系统生效。找不到账号的老数据显示原用户名，不再显示占位文字。
"""

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

REFRESH_SECONDS = 60
_names: dict[str, str] = {}
_loaded_at = 0.0


async def refresh_person_names(db: AsyncSession, *, force: bool = False) -> None:
    global _names, _loaded_at
    if not force and time.monotonic() - _loaded_at < REFRESH_SECONDS:
        return
    rows = (await db.execute(select(User.username, User.display_name))).all()
    _names = {str(username).strip().lower(): str(name or "").strip() for username, name in rows if str(username or "").strip()}
    _loaded_at = time.monotonic()


def person_name(username: object) -> str:
    """账号对应的姓名；没有账号或未填姓名时返回原用户名，空值返回空串。"""
    key = str(username or "").strip()
    if not key:
        return ""
    if key == "system":
        return "系统"
    return _names.get(key.lower()) or key

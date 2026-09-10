from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .models import BusinessRecord, FileAttachment, User

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    if encoded.startswith("legacy-md5$"):
        legacy_digest = encoded.removeprefix("legacy-md5$").strip().lower()
        if len(legacy_digest) != 32 or any(char not in "0123456789abcdef" for char in legacy_digest):
            return False
        current_digest = hashlib.md5(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(current_digest, legacy_digest)
    try:
        return password_hash.verify(password, encoded)
    except Exception:
        return False


def password_needs_rehash(encoded: str) -> bool:
    """Return whether a successfully verified transitional hash must be upgraded."""
    return encoded.startswith("legacy-md5$")


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


_PAGE_MENU_PREFIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("/system/menus/navigation", ()),
    ("/system/users", ("@root:hr",)),
    ("/system/security-policy", ("@root:system",)),
    ("/system/configs", ("system-management-config", "@root:system")),
    ("/system/caches", ("system-management-cache", "@root:system")),
    ("/system/menus", ("system-management-menu", "@root:system")),
    ("/system/role-permissions", ("@root:system",)),
    ("/system/roles", ("@root:system",)),
    ("/system/role", ("@root:system",)),
    ("/system/permissions", ("@root:system",)),
    ("/system/parameter-categories", ("system-parameters", "@root:system")),
    ("/system/parameter-relations", ("system-parameters", "@root:system")),
    ("/system/parameter", ("system-parameters", "@root:system")),
    ("/system/parameters", ("system-parameters", "@root:system")),
    ("/law-firms", ("system-law-firms", "@root:system")),
    ("/hr/employees", ("hr-all", "hr-new", "@root:hr")),
    ("/hr/departments", ("hr-departments", "@root:hr")),
    ("/hr/job-roles", ("hr-roles", "@root:hr")),
    ("/hr", ("@root:hr",)),
    ("/customers", ("@root:customer",)),
    ("/customer-portal", ("@root:customer",)),
    ("/contracts", ("@root:contract",)),
    ("/contract-payment-applications", ("@root:finance", "@root:platform-finance", "@root:contract")),
    ("/receivables", ("@root:contract", "@root:finance", "@root:platform-finance")),
    ("/cases", ("@root:case",)),
    ("/case-litigant-candidates", ("@root:case",)),
    ("/case-spaces", ("@root:case", "@root:agent-center")),
    ("/hearings", ("@root:case",)),
    ("/ipr", ("@root:ipr",)),
    ("/investigations", ("@root:investigation",)),
    ("/clues", ("@root:investigation",)),
    ("/notaries", ("@root:investigation",)),
    ("/evidence", ("@root:investigation", "@root:warehouse")),
    ("/documents", ("@root:documents",)),
    ("/official-outgoing", ("@root:documents",)),
    ("/agent/documents", ("@root:documents", "@root:agent-center")),
    ("/agent", ("@root:agent-center", "@root:documents")),
    ("/communications", ("user-communications", "@root:user-center")),
    ("/notifications", ("user-messages", "@root:user-center")),
    ("/users/directory", ("@root:user-center",)),
    ("/people/options", (
        "@root:user-center", "@root:hr", "@root:task", "@root:case",
        "@root:contract", "@root:finance", "@root:ipr", "@root:investigation",
    )),
    ("/seals", ("@root:seal",)),
    ("/tasks", ("@root:task",)),
    ("/vip-tasks", ("@root:task",)),
    ("/affairs-records", ("@root:task",)),
    ("/finance", ("@root:finance", "@root:platform-finance")),
    ("/platform-finance", ("@root:platform-finance",)),
    ("/warehouse", ("@root:warehouse",)),
    ("/WMS/", ("@root:warehouse",)),
    ("/reports", ("@root:reports",)),
    ("/legacy-history/attachments", (
        "@root:documents", "@root:contract", "@root:case", "@root:customer",
        "@root:ipr", "@root:investigation", "@root:seal", "@root:task",
    )),
    ("/templates", ("@root:documents", "@root:agent-center", "@root:task")),
    ("/audit/events", ("@root:system",)),
    ("/system/", ("@root:system",)),
    ("/hr/", ("@root:hr",)),
    ("/customers/", ("@root:customer",)),
    ("/contracts/", ("@root:contract",)),
    ("/receivables/", ("@root:contract", "@root:finance", "@root:platform-finance")),
    ("/cases/", ("@root:case",)),
    ("/case-spaces/", ("@root:case", "@root:agent-center")),
    ("/hearings/", ("@root:case",)),
    ("/ipr/", ("@root:ipr",)),
    ("/investigations/", ("@root:investigation",)),
    ("/documents/", ("@root:documents",)),
    ("/official-outgoing/", ("@root:documents",)),
    ("/seals/", ("@root:seal",)),
    ("/finance/", ("@root:finance", "@root:platform-finance")),
    ("/platform-finance/", ("@root:platform-finance",)),
    ("/warehouse/", ("@root:warehouse",)),
    ("/legacy-history/attachments/", (
        "@root:documents", "@root:contract", "@root:case", "@root:customer",
        "@root:ipr", "@root:investigation", "@root:seal", "@root:task",
    )),
    ("/templates/", ("@root:documents", "@root:agent-center", "@root:task")),
    ("/reports/", ("@root:reports",)),
)

_MODULE_MENU_ROOTS: dict[str, tuple[str, ...]] = {
    "customer": ("customer",),
    "contract": ("contract",),
    "case": ("case",),
    "ipr_case": ("ipr",),
    "ipr_official_file": ("ipr",),
    "task": ("task",),
    "investigation": ("investigation",),
    "clue": ("investigation",),
    "notary": ("investigation",),
    "evidence": ("investigation",),
    "document": ("documents",),
    "seal": ("seal",),
    "hr": ("hr",),
    "warehouse": ("warehouse",),
    "report": ("reports",),
    "finance": ("finance", "platform-finance"),
    "invoice": ("finance", "platform-finance"),
    "refund": ("finance", "platform-finance"),
    "finance_package": ("finance", "platform-finance"),
    "finance_settlement": ("finance", "platform-finance"),
    "finance_archive_settlement": ("finance", "platform-finance"),
    "contract_payment": ("finance", "platform-finance", "contract"),
}


def _relative_api_path(path: str) -> str:
    prefix = settings.api_prefix.rstrip("/")
    if prefix and path.startswith(prefix):
        return path[len(prefix):] or "/"
    return path


def _route_prefix_match(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


async def _page_menu_candidates(request: Request, db: AsyncSession) -> tuple[str, ...]:
    """Resolve the menu family for the current protected API request.

    Generic record and attachment routes do not carry a page key, so resolve
    their persisted business module before applying the same page capability.
    """
    path = _relative_api_path(request.url.path)
    if path == "/records" or path.startswith("/records/"):
        module = str(request.query_params.get("module") or "").strip()
        if not module:
            match = re.search(r"/records/(\d+)", path)
            if match:
                record = await db.get(BusinessRecord, int(match.group(1)))
                module = str(record.module if record else "").strip()
        roots = _MODULE_MENU_ROOTS.get(module, ())
        return tuple(f"@root:{root}" for root in roots)
    if path == "/attachments" or path.startswith("/attachments/"):
        match = re.search(r"/attachments/(\d+)", path)
        if match:
            attachment = await db.get(FileAttachment, int(match.group(1)))
            if attachment and attachment.record_id:
                record = await db.get(BusinessRecord, attachment.record_id)
                roots = _MODULE_MENU_ROOTS.get(str(record.module if record else "").strip(), ())
                if roots:
                    return tuple(f"@root:{root}" for root in roots)
        return (
            "@root:customer", "@root:contract", "@root:case", "@root:ipr",
            "@root:investigation", "@root:documents", "@root:seal",
            "@root:task", "@root:finance", "@root:platform-finance",
            "@root:hr", "@root:warehouse", "@root:reports",
        )
    for prefix, candidates in sorted(_PAGE_MENU_PREFIXES, key=lambda item: len(item[0]), reverse=True):
        if _route_prefix_match(path, prefix):
            return candidates
    return ()


def _menu_candidate_granted(menu_keys: set[str], candidate: str) -> bool:
    if candidate.startswith("@root:"):
        root = candidate.removeprefix("@root:")
        return any(key == root or key.startswith(f"{root}-") for key in menu_keys)
    return candidate in menu_keys


async def _page_menu_authorized(request: Request, db: AsyncSession, menu_keys: list[str]) -> bool:
    candidates = await _page_menu_candidates(request, db)
    if not candidates:
        return False
    granted = {str(key).strip() for key in menu_keys if str(key).strip()}
    return any(_menu_candidate_granted(granted, candidate) for candidate in candidates)


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
    profile = user.profile or {}
    # Permission resolution lives with the main application because it also
    # applies assigned HR roles and per-user overrides.  The import is delayed
    # until request time to avoid the startup import cycle (main imports this
    # dependency module).
    from .main import _user_permission_payload

    permission = await _user_permission_payload(user, db)
    page_capability = await _page_menu_authorized(request, db, permission.get("menu_keys") or [])
    effective_role_ids = ["admin", *role_ids] if page_capability and "admin" not in role_ids else role_ids
    effective_action_keys = ["*"] if page_capability else permission.get("action_keys") or []
    return {
        "username": user.username,
        "role": "admin" if page_capability else role_ids[0],
        "role_ids": effective_role_ids,
        "display_name": user.display_name,
        "department": user.department,
        "permission_role": profile.get("permission_role") or "",
        "staff_role": profile.get("staff_role") or "",
        "position": profile.get("position") or "",
        "must_change_password": user.must_change_password,
        "menu_keys": permission.get("menu_keys") or [],
        "action_keys": effective_action_keys,
        "data_scope": permission.get("data_scope"),
        "_actual_role": role_ids[0],
        "_actual_role_ids": role_ids,
        "_page_menu_capability": page_capability,
        "_request_path": request.url.path,
    }

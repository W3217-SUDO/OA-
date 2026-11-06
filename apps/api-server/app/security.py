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


_BANK_FLOW_LINE_MENUS = (
    "finance-receipts-bank-flow", "platform-finance-overview-bank-flow",
    *(f"{area}-{bank}" for area in ("finance-receipts", "platform-finance-overview") for bank in ("icbc", "citic", "boc", "cmb", "gdicbc")),
)
_PAGE_MENU_PREFIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("/system/menus/navigation", ()),
    ("/system/users", ("@root:hr",)),
    ("/system/security-policy", ("@root:system",)),
    ("/system/configs", ("system-management-config", "@root:system")),
    ("/system/dashboard-portals", ("system-parameters-dashboard-portals", "system-parameters", "@root:system")),
    ("/system/task-scopes/automatic-task", ("system-parameters-automatic-task", "@root:system")),
    ("/system/task-scopes/overdue-penalty", ("system-parameters-overdue-penalty", "@root:system")),
    ("/system/caches", ("system-management-cache", "@root:system")),
    ("/system/recycle-bin", ("system-management-recycle", "@root:system")),
    ("/system/change-logs", ("system-management-changes", "@root:system")),
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
    ("/hr/departments", ("hr-departments", "hr-department-new", "@root:hr")),
    ("/hr/job-roles", ("hr-roles", "@root:hr")),
    ("/hr/seal-approval-settings", ("hr-seal-approval", "@root:hr")),
    ("/hr", ("@root:hr",)),
    ("/customers", ("@root:customer",)),
    ("/party-library", ("@root:party",)),
    ("/parties", ("@root:party",)),
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
    # 新上传流水在“银行原始流水”和回款(工行/中信/中行/招商)四个页面都能看、导入、删除（279951）。
    *((path, _BANK_FLOW_LINE_MENUS) for path in ("/finance/bank-flows/lines", "/finance/bank-flows/generate", "/finance/bank-flows/delete")),
    ("/finance/bank-flows", ("finance-receipts-bank-flow", "finance-receipts-gdicbc", "platform-finance-overview-gdicbc", "platform-finance-overview-bank-flow")),
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


# 页面在用的读取一律按“用户所在页面”授权：页面里顺带读别的中心数据（下拉选项、参数关系等）时，
# 按接口路径去对另一个中心的菜单，会出现“能看见菜单和功能、点进去说没权限”。前端每个请求带上当前页面，
# 账号持有该页面就放行该页发出的读取；写操作仍按接口所属页面判断，系统管理、人事、审计、登录和令牌不随页面放开。
PAGE_HEADER = "x-oa-page"
_PAGE_KEY_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,95}")
_PAGE_READ_METHODS = frozenset({"GET", "HEAD"})
_PAGE_READ_PROTECTED_PREFIXES = ("/system", "/hr", "/audit", "/auth", "/law-firms", "/agent-tools")
_PAGE_READ_SHARED_PREFIXES = ("/system/parameter-relations", "/system/parameters", "/system/parameter")


def _page_header_candidates(request: Request) -> tuple[str, ...]:
    if request.method not in _PAGE_READ_METHODS:
        return ()
    page = str(request.headers.get(PAGE_HEADER) or "").strip()
    path = _relative_api_path(request.url.path)
    protected = any(_route_prefix_match(path, prefix) for prefix in _PAGE_READ_PROTECTED_PREFIXES)
    if protected and not any(_route_prefix_match(path, prefix) for prefix in _PAGE_READ_SHARED_PREFIXES):
        return ()
    if "-detail-" in page:
        # 详情页（case-detail-<id>-<编号> 等）不是菜单项，按所属中心判断；编号部分可能是编码后的中文，不参与。
        prefix = page.split("-detail-", 1)[0]
        return (f"@root:{prefix.split('-', 1)[0]}",) if _PAGE_KEY_PATTERN.fullmatch(prefix) else ()
    return (page,) if _PAGE_KEY_PATTERN.fullmatch(page) else ()


def _menu_candidate_granted(menu_keys: set[str], candidate: str) -> bool:
    if candidate.startswith("@root:"):
        root = candidate.removeprefix("@root:")
        return any(key == root or key.startswith(f"{root}-") for key in menu_keys)
    return candidate in menu_keys


async def _page_menu_authorized(request: Request, db: AsyncSession, menu_keys: list[str]) -> bool:
    candidates = (*(await _page_menu_candidates(request, db)), *_page_header_candidates(request))
    if not candidates:
        return False
    granted = {str(key).strip() for key in menu_keys if str(key).strip()}
    return any(_menu_candidate_granted(granted, candidate) for candidate in candidates)


async def _page_access_decision(request: Request, db: AsyncSession, menu_keys: list[str], *, external: bool = False) -> tuple[bool, bool]:
    """决定本次请求的页面能力：(是否有页面能力, 数据是否按账号真实范围)。

    页面能力只回答“能不能进这个中心的页面、用它的功能”，不等于能看全所数据：
    - 页面头只放行页面所属中心的读取；跨中心只留参数和下拉，下拉里的业务数据按真实范围。
    - 在该中心只持有个人页面（我的、新建等）的账号：导出整体按真实身份，写接口的记录可见性按真实范围。
    开关关掉时完全退回旧判断（见 app/core/data_scope_gate.py）。权限数据有问题也只影响能看到什么，不挡登录。
    """
    from app.core.data_scope_gate import (
        center_has_work_page, external_read_pending, gate_enabled, header_read_kind, is_export_path,
    )
    if not await gate_enabled(db):
        return await _page_menu_authorized(request, db, menu_keys), False
    path = _relative_api_path(request.url.path)
    path_candidates = await _page_menu_candidates(request, db)
    header_candidates = _page_header_candidates(request)
    granted = {str(key).strip() for key in menu_keys if str(key).strip()}
    external_actual = external and not external_read_pending(path, path_candidates)
    if any(_menu_candidate_granted(granted, candidate) for candidate in path_candidates):
        if external_actual:  # 外部账号在本中心也只有真实范围，和老系统“我的”页面一致
            return not is_export_path(path), True
        if center_has_work_page(granted, path_candidates):
            return True, False
        if request.method in _PAGE_READ_METHODS and not is_export_path(path):
            return True, False  # 本中心页面的读取，第 1 步不变；范围表定了再收
        return not is_export_path(path), True
    if not any(_menu_candidate_granted(granted, candidate) for candidate in header_candidates):
        return False, False
    kind = header_read_kind(path, header_candidates, path_candidates)
    if is_export_path(path):
        kind = "deny"
    if external_actual and kind == "allow" and path_candidates and not _is_cross_center_option(path):
        kind = "scoped"
    return kind != "deny", kind == "scoped"


def _is_cross_center_option(path: str) -> bool:
    from app.core.data_scope_gate import is_cross_center_option
    return is_cross_center_option(path)


def _actual_role_only_path(path: str) -> bool:
    from app.core.data_scope_gate import is_actual_role_path
    return is_actual_role_path(path)


def _note_page_scope_shadow(request: Request, username: str, role: str, menu_keys: list[str]) -> None:
    from app.core.data_scope_gate import center_has_work_page, is_personal_page, note_shadow_elevation, page_center
    page = str(request.headers.get(PAGE_HEADER) or "").strip()[:96]
    route = getattr(request.scope.get("route"), "path", "") or request.url.path
    center = page_center(page) if page else ""
    note_shadow_elevation(
        username, role, page, request.method, route,
        personal_page=bool(page) and is_personal_page(page),
        work_center=bool(center) and center_has_work_page({str(key) for key in menu_keys}, (f"@root:{center}",)),
    )


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
    from app.core.soft_delete import set_actor
    from app.core import change_log
    from app.core.person_names import refresh_person_names
    await refresh_person_names(db)  # 本进程的账号姓名对照，最长 60 秒刷新一次
    set_actor(user.username)  # 本次请求里的删除和变更记录操作人
    if change_log.source_var.get() == "system":  # MCP / 智能体发起的内部请求已带来源，这里不覆盖
        change_log.set_source("web")
    role_ids = user_role_ids(user)
    profile = user.profile or {}
    # Permission resolution lives with the main application because it also
    # applies assigned HR roles and per-user overrides.  The import is delayed
    # until request time to avoid the startup import cycle (main imports this
    # dependency module).
    from .main import _user_permission_payload

    permission = await _user_permission_payload(user, db)
    from app.core.data_scope_gate import is_external_customer_export, is_external_role
    external = "admin" not in role_ids and is_external_role(profile.get("permission_role"))
    if external and is_external_customer_export(_relative_api_path(request.url.path), request.query_params.get("module")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号不能导出客户")
    page_capability, page_scope_actual = await _page_access_decision(request, db, permission.get("menu_keys") or [], external=external)
    if page_capability and not page_scope_actual and "admin" not in role_ids:
        _note_page_scope_shadow(request, user.username, role_ids[0], permission.get("menu_keys") or [])
    # 个人页面账号写自己范围内的记录时功能照旧（给页面=功能全有），只有记录可见性按真实范围；
    # 跨中心读取和任务这类本来就按参与人判断的接口，不提升成管理员。
    elevated = page_capability and not (page_scope_actual and (
        external or request.method in _PAGE_READ_METHODS or _actual_role_only_path(_relative_api_path(request.url.path))))
    effective_role_ids = ["admin", *role_ids] if elevated and "admin" not in role_ids else role_ids
    effective_action_keys = ["*"] if page_capability and not external else permission.get("action_keys") or []
    return {
        "username": user.username,
        "role": "admin" if elevated else role_ids[0],
        "role_ids": effective_role_ids,
        "display_name": user.display_name,
        "department": user.department,
        "permission_role": profile.get("permission_role") or "",
        "staff_role": profile.get("staff_role") or "",
        "position": profile.get("position") or "",
        "must_change_password": user.must_change_password,
        "menu_keys": permission.get("menu_keys") or [],
        "action_keys": effective_action_keys,
        "_user_action_keys": permission["user_action_keys"],
        "data_scope": permission.get("data_scope"),
        "_actual_role": role_ids[0],
        "_actual_role_ids": role_ids,
        "_page_menu_capability": page_capability,
        # 页面能力照常（菜单、动作门槛），但数据范围按账号真实范围，见 _record_scope_conditions。
        "_page_scope_actual": page_scope_actual,
        "_external_account": external,
        # 发起请求的页面（前端 X-OA-Page），详情读取按“从哪个有权页面点进来”判断时用。
        "_request_page": next((page for page in _page_header_candidates(request) if not page.startswith("@")), ""),
        "_request_path": request.url.path,
        "_request_method": request.method,
    }

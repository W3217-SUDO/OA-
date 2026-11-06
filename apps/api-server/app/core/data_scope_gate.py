"""页面能力和数据范围的第一道分界：堵住“持有任一页面就能读写全所数据”。

判断都只影响业务接口能看到、能改什么，不参与登录；开关写在系统配置里，
不用发版，约一分钟内可退回旧判断：key = permissions.data_scope_gate，value = off。
"""

import logging
import re
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemConfig

logger = logging.getLogger(__name__)
GATE_CONFIG_KEY = "permissions.data_scope_gate"
_REFRESH_SECONDS = 60
_enabled = True
_loaded_at = float("-inf")

# 个人页面：只办本人事务。其他页面（全所、部门、审核、管理、查询……）算工作页面，第 1 步行为不变。
_PERSONAL_PAGE = re.compile(r"(^|-)(new|mine|my)(-|$)")
_PERSONAL_PAGES = frozenset({
    "customer-shared", "customer-recent-contact", "customer-recent-update", "customer-conflict",
    "customer-recycle", "customer-public",
    "case-archive-refused", "case-archive-loss-refused",
    "contract-archive", "contract-recycle",
    "finance-internal-detail",
    "party-company-info", "party-recycle",
})

# 名字带 new 但办的是全所事务：财务登记到账。
_WORK_PAGES_NAMED_NEW = frozenset({"finance-receipts-new", "platform-finance-overview-new", "ipr-finance-receipts-new"})

_PUBLIC_CENTERS = frozenset({"agent-center", "user-center", "dashboard"})

_EXPORT_PATH = re.compile(r"(^|/|-)(export|handover-export|print-export|export-excel|export-selected|print-word|download-zip)(/|-|$)")

# 个人页面账号写这些接口时按真实角色：任务按参与人判断，模板、当事人库重建、登记到账是管理动作。
_ACTUAL_ROLE_WRITE_PREFIXES = (
    "/tasks", "/vip-tasks", "/affairs-records", "/templates", "/party-library", "/finance/incoming-payments",
)

# 跨中心读取：参数和下拉保留。这些接口不返回业务记录明细，页面能力照旧。
_CROSS_CENTER_OPTIONS = (
    "/system/parameter-relations", "/system/parameters", "/system/parameter",
    "/warehouse/catalog", "/seals/assets", "/people/options", "/users/directory",
    "/investigations/evidence-storage-options", "/investigations/assignment-supervisor",
    "/investigations/action-capabilities", "/cases/action-capabilities", "/cases/phases",
    "/agent/skills", "/tasks/unread-messages", "/notifications",
    "/customers/reference-options", "/cases/reference-options",
)
_CROSS_CENTER_OPTION_PATTERNS = (re.compile(r"^/finance/fees/\d+/payment-types$"),)
# 跨中心读取：下拉里是业务数据，只给账号真实范围内的。
_CROSS_CENTER_SCOPED = ("/tasks/case-options", "/tasks/customer-options", "/cases/eligible-contracts")
_CROSS_CENTER_SCOPED_EXACT = ("/records", "/customers")

# 这些接口不在页面前缀表里，页面头只放行所属中心；未列出的公共接口（工作台、问题反馈等）不变。
_UNLISTED_ROUTE_CENTERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("/legacy-ls-history", ("case",)),
    ("/legacy-case-task-history", ("case", "task")),
    ("/legacy-ipr-history", ("ipr",)),
    ("/legacy-contract-history", ("contract",)),
    ("/legacy-seal-records", ("seal",)),
    ("/case-word-templates", ("case", "agent-center")),
    ("/hearing-sms", ("case",)),
    ("/conflict-reviews", ("case", "contract", "ipr", "customer", "seal", "investigation")),
    ("/conflict-rules", ("customer",)),
    ("/company-library", ("party", "customer")),
    ("/company-lookup", ("customer", "party")),
    ("/agent-admin", ("agent-center",)),
    ("/external-credentials", ("system",)),
    ("/data-query", ("reports", "system")),
)


async def gate_enabled(db: AsyncSession) -> bool:
    """每个工作进程最长 60 秒读一次开关。"""
    global _enabled, _loaded_at
    if time.monotonic() - _loaded_at >= _REFRESH_SECONDS:
        value = await db.scalar(select(SystemConfig.value).where(SystemConfig.key == GATE_CONFIG_KEY))
        _enabled = str(value or "").strip().lower() != "off"
        _loaded_at = time.monotonic()
    return _enabled


def reset_gate_cache() -> None:
    global _enabled, _loaded_at
    _enabled, _loaded_at = True, float("-inf")


def is_personal_page(key: str) -> bool:
    if key.startswith("hr-") or key in _WORK_PAGES_NAMED_NEW:
        return False
    return key in _PERSONAL_PAGES or bool(_PERSONAL_PAGE.search(key))


def page_center(page: str) -> str:
    base = page.removeprefix("@root:").split("-detail-", 1)[0]
    for center in ("platform-finance", "agent-center", "user-center"):
        if base == center or base.startswith(f"{center}-"):
            return center
    return base.split("-", 1)[0]


def center_has_work_page(menu_keys: set[str], candidates: tuple[str, ...]) -> bool:
    """账号在这些中心里是否持有个人页面以外的页面。人人都有的公共中心不算。"""
    for candidate in candidates:
        if candidate.startswith("@root:"):
            root = candidate.removeprefix("@root:")
            if root in _PUBLIC_CENTERS:
                continue
            if any((key == root or key.startswith(f"{root}-")) and not is_personal_page(key) for key in menu_keys):
                return True
        elif candidate in menu_keys and not is_personal_page(candidate):
            return True
    return False


def is_actual_role_path(path: str) -> bool:
    return any(_prefix_match(path, prefix) for prefix in _ACTUAL_ROLE_WRITE_PREFIXES)


def is_export_path(path: str) -> bool:
    return bool(_EXPORT_PATH.search(path))


def _prefix_match(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def header_read_kind(path: str, header_candidates: tuple[str, ...], path_candidates: tuple[str, ...]) -> str:
    """页面头发起的读取怎么处理：allow 不变、scoped 能读但按真实范围、deny 不放行。"""
    centers = {page_center(page) for page in header_candidates}
    if any(_prefix_match(path, prefix) for prefix in _CROSS_CENTER_OPTIONS) or any(rule.match(path) for rule in _CROSS_CENTER_OPTION_PATTERNS):
        return "allow"
    if any(_prefix_match(path, prefix) for prefix in _CROSS_CENTER_SCOPED) or path in _CROSS_CENTER_SCOPED_EXACT:
        return "scoped"
    if path_candidates:
        return "allow" if centers & {page_center(candidate) for candidate in path_candidates} else "deny"
    if path.startswith("/records") or path.startswith("/attachments"):
        return "scoped"
    for prefix, owners in _UNLISTED_ROUTE_CENTERS:
        if _prefix_match(path, prefix):
            return "allow" if centers & set(owners) else "deny"
    return "allow"


# 只记录不拦截：页面能力让账号越过真实数据范围的请求记一笔，跑几天后拿来定“菜单→数据范围”表。
_SHADOW_WINDOW_SECONDS = 3600
_SHADOW_MAX_KEYS = 20000
_shadow_seen: set[tuple[str, str, str, str]] = set()
_shadow_window_started = float("-inf")


def note_shadow_elevation(username: str, role: str, page: str, method: str, route: str, *, personal_page: bool, work_center: bool) -> None:
    """同一账号、页面、接口每小时只记一次；这里任何问题都不能影响请求本身。"""
    global _shadow_window_started
    try:
        now = time.monotonic()
        if now - _shadow_window_started >= _SHADOW_WINDOW_SECONDS:
            _shadow_seen.clear()
            _shadow_window_started = now
        key = (username, page, method, route)
        if key in _shadow_seen or len(_shadow_seen) >= _SHADOW_MAX_KEYS:
            return
        _shadow_seen.add(key)
        logger.warning("page-scope-shadow user=%s role=%s page=%s personal_page=%s work_center=%s method=%s route=%s",
                    username, role, page, personal_page, work_center, method, route)
    except Exception:  # noqa: BLE001 - 记录失败不影响业务
        logger.debug("page-scope-shadow skipped", exc_info=True)

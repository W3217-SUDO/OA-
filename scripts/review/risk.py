"""按改动文件判定审查风险档位：低、中、高。只给建议，不拦截任何推送和发布。"""

from __future__ import annotations

import re

TIERS = ("low", "medium", "high")
TIER_NAMES = {"low": "低风险", "medium": "中风险", "high": "高风险"}
TIER_REQUIREMENTS = {
    "low": "开发 + 工具层",
    "medium": "工具层 + 独立审查 + 相关测试",
    "high": "验收场景 + 独立测试 + 前后接口对比 + 独立审查 + 人工拍板（技术和数据：陶威；业务规则：陶国南）",
}

API = r"apps/api-server/app/"
WEB = r"apps/admin-web/src/"
# 按文件名判，不靠目录：财务逻辑散在 core、ipr、legal、contract 和前端各处。
ANY_DIR = r"(?:.*/)?"
PY_MONEY = r"[^/]*(?:financ|invoice|payment|receipt|refund|settlement|bank_|incoming_|commission|allocation|(?:^|_)fees?(?:_|\.))[^/]*$"
WEB_MONEY = r"[^/]*(?:[Ff]inanc|[Ii]nvoice|[Pp]ayment|[Rr]eceipt|[Rr]efund|[Ss]ettlement|[Cc]ommission|[Ff]ees?(?=[A-Z._]))[^/]*$"
HIGH_RULES = (
    ("权限", (
        API + r"security\.py$", API + r"agent_permissions\.py$", API + r"agent_mcp/auth\.py$",
        API + r"areas/system/dingtalk_auth\.py$",
        API + r"core/[^/]*(permission|data_scope|department_visibility|_scope|_access)[^/]*\.py$",
        API + r"areas/capability_market/mcp_access\.py$", API + r"core/system\.py$",
        API + r"areas/system/router\.py$", API + r"areas/hr/router\.py$", API + r"core/constants\.py$",
        API + r"data_models/identity\.py$", WEB + ANY_DIR + r"[^/]*([Pp]ermission|roleAction|[Aa]ccessGuard)[^/]*$",
    )),
    ("财务", (
        API + r"areas/finance/", API + ANY_DIR + r"fees\.py$", API + r"areas/contract/router\.py$",
        API + ANY_DIR + PY_MONEY, WEB + r"finance/", WEB + ANY_DIR + WEB_MONEY,
        API + r"areas/legal/router\.py$", API + r"areas/legal/case_space\.py$", API + r"core/(cases|internal_requests|crm|projections)\.py$",
        WEB + r"legal/CaseCenterPage\.tsx$", WEB + r"contract/services/queriesActions\.tsx$",
    )),
    ("数据写入", (
        API + r"core/soft_delete[^/]*\.py$", API + r"database\.py$", API + r"models[^/]*\.py$", API + r"data_models/",
        API + r"core/attachment_deletion\.py$", API + r"areas/system/recycle_bin\.py$",
        API + ANY_DIR + r"[^/]*(_delete|_deletions?|_merge|backfill|_repair|_import|record_import)[^/]*\.py$",
        r"scripts/(import|migrate|fix|repair|restore|align|promote|backfill|recover|reconcile|rebuild)[^/]*$", r"scripts/hz_snapshot_alignment/",
        r"apps/api-server/scripts/",  # 一次性数据脚本，大多直接写生产数据
    )),
    ("数据库结构", (
        API + r"core/startup_migrations\.py$", API + r"core/schema_alignment\.py$", API + r"core/[^/]*_migration\.py$",
        API + r"legacy_schema", r".*\.sql$",
    )),
    ("同步", (
        r"scripts/hd_sync/", r"scripts/hd_live_sync\.py$", r"scripts/hz_", r"scripts/sync_", API + r"core/legacy_sync\.py$",
        API + r"core/attachment_oss_sync\.py$", API + r"core/hz_",
    )),
    ("发布和质量门", (
        r"\.github/", r"\.githooks/", r"scripts/quality_gate\.py$", r"scripts/install-(quality-hook|review-tools)\.sh$",
        r"scripts/(native|runtime|verify_)[^/]*$", r"scripts/review/", r"requirements[^/]*$", r"pyproject\.toml$",
        r"apps/api-server/requirements", r"apps/api-server/tests/suite_manifest\.json$", r"apps/api-server/tests/run_regression\.py$",
        r"deploy/", r"compose[^/]*\.yml$", r"docker-compose[^/]*\.yml$", r"docs/skills/oa-fast-deploy/scripts/",
    )),
)
# aws 下的 receipt 是收文回执，不是财务收据。
NOT_MONEY = re.compile(r"(?:apps/api-server/app/areas/aws|apps/admin-web/src/aws)/[^/]*[Rr]eceipt")
LOW_PATTERNS = (r"docs/", r".*\.md$", r".*\.css$", r"tests/", r"apps/[^/]+/tests/", r".*\.(png|jpe?g|gif|svg|ico|docx|xlsx)$")
# 路径判不出来时靠改动行兜底：直接写库的 SQL，以及 ORM 的新增、删除、批量写。
# 局限：改已查出对象的字段（record.status = ...）是普通赋值，这里抓不到。
RAW_WRITE = re.compile(r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|ALTER\s+TABLE|DROP\s+(TABLE|INDEX|COLUMN)|TRUNCATE)\b", re.I)
ORM_WRITE = re.compile(r"\b(?:db|session)\.(?:add|add_all|delete|merge|bulk_\w+)\(|\bexecute\(\s*(?:update|insert|delete)\(|\b(?:update|insert|delete)\([A-Z]\w+\)")
MANUAL_TRAILER = re.compile(r"^Review-Tier:\s*(low|medium|high)\s*$", re.I | re.M)


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(re.match(pattern, path) for pattern in patterns)


def classify_file(path: str) -> tuple[str, str]:
    """返回 (档位, 原因)。"""
    for category, patterns in HIGH_RULES:
        if category == "财务" and NOT_MONEY.match(path):
            continue
        if _matches(path, patterns):
            return "high", category
    if _matches(path, LOW_PATTERNS):
        return "low", "文档、测试或样式"
    return "medium", "业务代码"


def manual_tier(commit_messages: str) -> str | None:
    """提交说明里的 Review-Tier 取最高的一个。"""
    found = [item.lower() for item in MANUAL_TRAILER.findall(commit_messages)]
    return max(found, key=TIERS.index) if found else None


def classify(files: list[str], added_lines: dict[str, list[str]] | None = None, raise_to: str | None = None) -> dict:
    """人工只能提档，不能降档。"""
    items, raw_writes = [], []
    for path in files:
        tier, reason = classify_file(path)
        if tier != "high" and not _matches(path, LOW_PATTERNS):
            hit = next((line.strip() for line in (added_lines or {}).get(path, [])
                        if RAW_WRITE.search(line) or (path.endswith(".py") and ORM_WRITE.search(line))), None)
            if hit:
                tier, reason = "high", "改动里有写库语句"
                raw_writes.append({"file": path, "line": hit[:120]})
        items.append({"file": path, "tier": tier, "reason": reason})
    computed = max((item["tier"] for item in items), key=TIERS.index, default="low")
    final = max((computed, raise_to or "low"), key=TIERS.index)
    return {
        "tier": final, "name": TIER_NAMES[final], "requirement": TIER_REQUIREMENTS[final], "computed": computed,
        "raised_manually": final != computed,
        "reasons": sorted({item["reason"] for item in items if item["tier"] == computed}),
        "files": items, "raw_writes": raw_writes,
    }

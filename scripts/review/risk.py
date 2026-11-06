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
HIGH_RULES = (
    ("权限", (
        API + r"security\.py$", API + r"agent_permissions\.py$", API + r"agent_mcp/auth\.py$",
        API + r"areas/system/dingtalk_auth\.py$",
        API + r"core/[^/]*(permission|data_scope|department_visibility|_scope)[^/]*\.py$",
        API + r"data_models/identity\.py$", WEB + r".*[Pp]ermission[^/]*$",
    )),
    ("财务", (
        API + r"areas/finance/", API + r"core/[^/]*(finance|invoice|payment|receipt|refund|settlement|bank_|_fee|fee_)[^/]*\.py$",
        WEB + r"finance/",
    )),
    ("数据写入", (
        API + r"core/soft_delete[^/]*\.py$", API + r"database\.py$", API + r"models[^/]*\.py$", API + r"data_models/",
        API + r"core/attachment_deletion\.py$", API + r"areas/system/recycle_bin\.py$",
        r"scripts/(import|migrate|fix|repair|restore|align)[^/]*$", r"scripts/hz_snapshot_alignment/",
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
        r"scripts/(native|runtime|verify_)[^/]*$", r"scripts/review/(?!baseline\.json$)", r"requirements[^/]*$", r"pyproject\.toml$",
        r"apps/api-server/requirements", r"apps/api-server/tests/suite_manifest\.json$", r"apps/api-server/tests/run_regression\.py$",
        r"deploy/", r"compose[^/]*\.yml$", r"docker-compose[^/]*\.yml$", r"docs/skills/oa-fast-deploy/scripts/",
    )),
)
LOW_PATTERNS = (r"scripts/review/baseline\.json$", r"docs/", r".*\.md$", r".*\.css$", r"tests/", r"apps/[^/]+/tests/", r".*\.(png|jpe?g|gif|svg|ico|docx|xlsx)$")
# 改动行里出现这些写法视为批量写数据或改结构，路径判不出来时靠它兜底。
RAW_WRITE = re.compile(r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|ALTER\s+TABLE|DROP\s+(TABLE|INDEX|COLUMN)|TRUNCATE)\b", re.I)
MANUAL_TRAILER = re.compile(r"^Review-Tier:\s*(low|medium|high)\s*$", re.I | re.M)


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(re.match(pattern, path) for pattern in patterns)


def classify_file(path: str) -> tuple[str, str]:
    """返回 (档位, 原因)。"""
    for category, patterns in HIGH_RULES:
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
            hit = next((line.strip() for line in (added_lines or {}).get(path, []) if RAW_WRITE.search(line)), None)
            if hit:
                tier, reason = "high", "改动里有直接写库语句"
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

"""目录检索的意图排序；不参与授权或工具可调用性判定。"""

import re

from app.agent_mcp.operation_guidance import get_operation_guidance
from app.agent_mcp.tool_groups import business_intent_groups, classify_tool
from app.config import settings


_INTENTS = (
    (("新增", "新建", "创建", "录一笔", "登记", "打钱了", "收到一笔款", "收款入账"), {"create", "add", "register"}),
    (("下载", "download"), {"download"}),
    (("查看", "查询", "搜索"), {"get", "list", "search", "query"}),
    (("上传", "upload"), {"upload"}),
    (("导入", "import"), {"import"}),
    (("修改", "编辑", "更新", "update", "edit"), {"patch", "update", "edit", "maintain", "save"}),
    (("核准", "批准", "审批", "审核"), {"approve", "review"}),
    (("付款", "支出"), {"pay", "payment", "payments", "writeoff"}),
    (("统计", "多少件", "几件", "多少个", "数量", "总数"), {"statistics", "counts", "count", "analytics"}),
)


def semantic_score(tool, query: str) -> int:
    """只用端点、路径、标题和专项正向用途打分，避免限制语句反向命中。"""
    endpoint = tool._route.endpoint.__name__.lower()
    path = tool.path.lower()
    short_path = path.removeprefix(settings.api_prefix.lower())
    if query in {tool.name.lower(), endpoint, tool._route.name.lower(), path, short_path,
                 f"{tool.method.lower()} {path}", f"{tool.method.lower()} {short_path}"}:
        return 1_000_000
    guidance = get_operation_guidance(tool._route, tool.method)
    words = set(re.split(r"[^a-z0-9]+", f"{endpoint} {path}"))
    positive = " ".join((tool.title, guidance["purpose"], *guidance["search_terms"])).lower()
    score = 0
    intent_groups = business_intent_groups(query)
    if intent_groups:
        score += 120 if classify_tool(tool._route, tool.method)[0] in intent_groups else -30
    if query in {"文件", "file", "附件", "attachment", "上传附件"} and endpoint == "upload_attachment":
        score += 160
    if "案件" in query and any(term in query for term in ("核准", "批准")) and endpoint == "review_case_creation":
        score += 160
    if any(term in query for term in ("修改", "编辑", "更新", "update", "edit")):
        if tool.method in {"PATCH", "PUT"}:
            score += 70
        elif not tool.is_write:
            score -= 65
    for expressions, markers in _INTENTS:
        if any(expression in query for expression in expressions):
            score += 65 if words.intersection(markers) else -15
    incoming = bool(words.intersection({"incoming", "receivable", "receivables", "arrival"}))
    if "16" in intent_groups:
        score += 100 if incoming else -35
    if "19" in intent_groups and incoming:
        score -= 150
    if "19" in intent_groups and endpoint == "list_internal_payment_packages":
        score += 100
    if "06" in intent_groups and any(term in query for term in ("多少", "几件", "统计", "数量")):
        score += 180 if endpoint == "case_statistics" else 0
    if "15" in intent_groups:
        score += 75 if words.intersection({"fee", "fees"}) else -15
        if query in {"官费", "诉讼费"} and endpoint == "create_finance_fee":
            score += 160
    if any(term in query for term in ("案件", "案子")):
        score += 45 if words.intersection({"case", "cases"}) else -15
    if any(term in query for term in ("律所", "律师事务所")):
        score += 75 if "law" in words and words.intersection({"firm", "firms"}) else -15
    if "客户" in query:
        score += 65 if words.intersection({"customer", "customers"}) else -15
        # 客户主档与联系人、层级申请等子业务分开排序，不改变参数或原接口。
        customer_path = short_path.strip("/").split("/")
        if customer_path[0] == "customers" and len(customer_path) <= 2:
            if any(term in query for term in ("新增", "新建", "创建")) and endpoint == "create_customer":
                score += 180
            if any(term in query for term in ("修改", "编辑", "更新")) and endpoint == "patch_customer":
                score += 180
    if any(term in query for term in ("承办", "经办", "主办", "律师手上")):
        # 仅关联检索表达，不把三种业务角色宣称为同一字段或自动改写参数。
        properties = tool.input_schema.get("properties", {})
        fields = {name for group in properties.values() if isinstance(group, dict)
                  for name in group.get("properties", {})}
        score += 35 if fields.intersection({"handler", "handling_lawyer", "handling_lawyers", "owner"}) else 0
        if not any(term in query for term in ("新增", "修改", "指派", "分配", "删除")):
            score += 90 if endpoint in {"search_ordinary_cases", "search_counsel_cases"} else 0
    explicit_action = any(term in query for term in (
        "新增", "新建", "创建", "录一笔", "登记", "下载", "导出", "上传", "导入", "删除", "移除",
        "修改", "编辑", "更新", "取消", "撤回", "回退", "提交", "审批", "审核", "核准", "批准", "分配", "认领",
        "create", "add", "download", "export", "upload", "import", "delete", "update", "cancel", "approve",
    ))
    if not explicit_action:
        score += 30 if not tool.is_write and words.intersection({"list", "search", "query"}) else 0
        score -= 35 if words.intersection({"export", "cancel", "rollback", "delete", "revoke"}) else 0
    score += sum(25 for term in guidance["search_terms"] if term in query)
    if query in positive:
        score += 20
    return score

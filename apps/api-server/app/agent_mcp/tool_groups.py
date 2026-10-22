"""工具主组由真实路由确定；未知路由显式阻断，不归入通用兜底组。"""

import re
from collections import Counter

from fastapi import HTTPException

from app.config import settings


GROUPS = {
    "01": ("工作台待办", "查看工作台汇总和个人待处理队列", "工作台 待办 dashboard queues"),
    "02": ("人员基础选项", "查询人员目录及业务录入所需基础选项", "人员 账号 律师 经办 承办 主办 选项 people users options"),
    "03": ("客户", "查询和维护客户、联系人、负责人及共享关系", "客户 联系人 customer contacts"),
    "04": ("律所", "查询和维护律所档案、联系人及执照", "律所 律师事务所 law firms"),
    "05": ("合同含利益冲突", "合同查询、审批、变更及利益冲突审查", "合同 利益冲突 contract conflicts"),
    "06": ("案件查询统计", "按权限查询案件、案情详情及阶段数量统计", "案件 查询 搜索 统计 总数 数量 多少件 承办 经办 主办 case search statistics"),
    "07": ("案件办理", "维护案件基础资料、当事人、分派及办理进度", "案件 办理 新增 修改 分派 当事人 case litigant progress"),
    "08": ("知产", "办理知识产权案件、官文、年费和预警", "知产 知识产权 专利 商标 官文 ipr patent"),
    "09": ("开庭", "查询和维护开庭安排、出庭律师及短信", "开庭 出庭 hearing court"),
    "10": ("归档", "案件归档查询、准备检查、审批及撤销归档", "归档 结案 archive unarchive close"),
    "11": ("文档附件", "查询、上传、下载、编辑业务文档和附件", "文件 文档 附件 上传 下载 导入 upload attachment file document import"),
    "12": ("任务协作", "任务指派、交接、开始完成及协作沟通", "任务 协作 交接 沟通 task communication"),
    "13": ("调查线索", "调查记录、任务分配及线索关联管理", "调查 线索 investigation clue"),
    "14": ("取证公证", "维护取证资料、公证及证物存放选项", "取证 公证 evidence notary"),
    "15": ("费用登记", "登记和维护案件费用、费用通知及费用提交检查", "费用 登记 草稿 案件费用 fee expenses"),
    "16": ("回款认领", "登记银行到账、认领客户并分配回款", "回款 到账 收入 认领 分派 incoming payment arrival"),
    "17": ("应收台账", "查询和维护应收计划、合同台账与应收汇总", "应收 台账 receivable ledger"),
    "18": ("结算提成", "查询和办理结算、提成分配及内部费用结算", "结算 提成 内部费用 settlement commission"),
    "19": ("请款付款", "请款申请、付款包、付款审批及支付核销", "请款 付款 支出 支付 核销 payment package writeoff"),
    "20": ("开票", "开票申请、发票查询及原业务审批", "开票 发票 invoice"),
    "21": ("退费对账", "退费申请、对账及财务交易流水", "退费 退款 对账 流水 refund reconciliation transaction"),
    "22": ("用印收发文", "用印申请、印章管理及官方收发文", "用印 印章 发文 收文 seal official outgoing"),
    "23": ("人事组织", "员工档案、组织部门及人事业务管理", "人事 员工 部门 组织 hr employee department"),
    "24": ("仓库", "仓库证物、库位及出入库管理", "仓库 证物 库位 入库 出库 warehouse wms"),
    "25": ("报表平台辅助", "按子组查询报表、通知反馈、系统参数或智能文书技能", "报表 通知 反馈 系统 参数 智能 文书 技能 report notification system agent"),
}

# 按业务区分：个人令牌的连接地址可以只选若干业务（?biz=case,finance），只加载并只允许调用所选业务的接口。
BUSINESS_BUNDLES = {
    "customer": ("客户与合同", ("02", "03", "04", "05")),
    "case": ("案件", ("02", "06", "07", "09", "10", "11")),
    "ipr": ("知识产权", ("02", "08", "11")),
    "task": ("任务协作", ("02", "12")),
    "investigation": ("调查取证", ("02", "13", "14")),
    "finance": ("财务", ("15", "16", "17", "18", "19", "20", "21")),
    "seal": ("用印收发文", ("22",)),
    "hr": ("人事组织", ("23",)),
    "warehouse": ("仓库", ("24",)),
    "workbench": ("工作台与报表", ("01", "25")),
}


def resolve_business_scope(biz: str | None, groups: str | None) -> frozenset[str] | None:
    """把连接地址里的 biz（业务名）和 groups（分组编号）解析成分组编号集合；都没给返回 None（只给入口工具）。"""
    selected: set[str] = set()
    for key in [item.strip() for item in (biz or "").split(",") if item.strip()]:
        if key not in BUSINESS_BUNDLES:
            raise HTTPException(400, f"未知业务 {key}，可选：{', '.join(BUSINESS_BUNDLES)}")
        selected.update(BUSINESS_BUNDLES[key][1])
    for group_id in [item.strip() for item in (groups or "").split(",") if item.strip()]:
        if group_id not in GROUPS:
            raise HTTPException(400, f"未知分组 {group_id}")
        selected.add(group_id)
    return frozenset(selected) if selected else None


SUBGROUPS = {
    "reporting": ("报表", "报表 财务汇总 reports summary"),
    "notifications_feedback": ("通知反馈", "通知 反馈 notifications feedback"),
    "system_parameters": ("系统参数", "系统 参数 菜单 权限 通用记录 审计 搜索 system parameters records audit search"),
    "ai_documents_skills": ("智能文书技能", "智能 文书 模板 技能 agent templates capability"),
}

# 仅提示工作流可能需要再发现的组，不复制工具或授予跨组调用权限。
WORKFLOW_GROUPS = {
    "05": ("03", "04", "06", "17", "19", "20", "22"),
    "07": ("02", "05", "09", "10", "11", "12", "13", "15"),
    "08": ("03", "04", "11", "15", "16", "19", "20"),
    "15": ("02", "05", "06", "16", "17", "19", "20"),
    "16": ("03", "15", "17", "18"),
    "18": ("06", "15", "16", "19", "23"),
}


def business_intent_groups(query: str) -> set[str]:
    """仅识别业务方向的口语同义词，不推断金额、费用分类编号或付款状态。"""
    groups = set()
    if any(term in query for term in ("费用", "律师费", "代理费", "官费", "诉讼费")):
        groups.add("15")
    if any(term in query for term in ("回款", "到账", "收入", "客户打钱", "客户打款", "收到一笔款", "收款", "入账")):
        groups.add("16")
    if any(term in query for term in ("付款", "支出", "请款", "支付", "供应商打款", "付出去", "付一笔", "给供应商", "打款给")):
        groups.add("19")
    if any(term in query for term in ("案件", "案子")) and any(term in query for term in ("查", "多少", "几件", "统计", "数量", "手上")):
        groups.add("06")
    return groups


def require_group(group_id: str, subgroup_id: str | None = None) -> None:
    if not isinstance(group_id, str) or group_id not in GROUPS:
        raise HTTPException(422, "未知业务工具组，请先发现工具组")
    if subgroup_id is not None and (group_id != "25" or not isinstance(subgroup_id, str) or subgroup_id not in SUBGROUPS):
        raise HTTPException(422, "未知子组，只有第 25 组支持已公布的子组")


def classify_tool(route, method: str) -> tuple[str, str | None]:
    path = route.path.removeprefix(settings.api_prefix).strip("/")
    parts = path.lower().split("/")
    root = parts[0]
    segments = set(parts)
    if root in {"dashboard"}:
        return "01", None
    if root == "data-query":
        return "25", "reporting"
    if root in {"people", "users"} or path.lower() == "system/users":
        return "02", None
    if root in {"warehouse", "wms"}:
        return "24", None
    if root in {"seals", "official-outgoing", "documents"}:
        return "22", None
    if root in {"hearings", "hearing-sms"}:
        return "09", None
    if root == "hr":
        return "23", None
    if root in {"notaries", "evidence"} or (root == "investigations" and segments.intersection({"evidence", "notaries", "evidence-storage-options"})):
        return "14", None
    if root == "investigations":
        return "13", None
    if root in {"tasks", "vip-tasks", "communications", "legacy-case-task-history"}:
        return "12", None
    if root in {"attachments", "legacy-history"}:
        return "11", None
    if root in {"ipr", "legacy-ipr-history"}:
        return "08", None
    if root == "law-firms":
        return "04", None
    if root in {"conflict-reviews", "conflict-rules", "legacy-contract-history"} or path == "customers/conflicts":
        return "05", None
    if root in {"customers", "parties", "party-library"}:
        return "03", None
    if root == "receivables":
        return "17", None
    if root == "contract-payment-applications":
        return "19", None
    if root == "contracts":
        for markers, group in (
            ({"attachments"}, "11"), ({"incoming-payments"}, "16"), ({"receivables"}, "17"),
            ({"invoice-candidates"}, "20"), ({"payment-candidates", "payment-types", "payment-applications"}, "19"),
        ):
            if segments.intersection(markers):
                return group, None
        return "05", None
    if root in {"cases", "case-spaces", "case-litigant-candidates", "legacy-ls-history"}:
        for markers, group in (
            ({"attachments", "documents", "document-folders", "ai-space", "invoice-files", "files"}, "11"),
            ({"archive", "archive-readiness", "unarchive", "close"}, "10"),
            ({"tasks"}, "12"), ({"clues", "clue-candidates"}, "13"), ({"notary-info"}, "14"),
            ({"hearing-lawyer", "court-info"}, "09"),
            ({"commissions", "commission-preview", "settlement-amount"}, "18"),
            ({"assisted-fees", "batch-fees", "fee-contracts"}, "15"),
        ):
            if segments.intersection(markers):
                return group, None
        query_routes = {"search", "statistics", "stage-statistics", "summary", "export", "pending-execution", "execution-status", "special-records"}
        if segments.intersection(query_routes) or (method == "GET" and (len(parts) <= 2 or root in {"case-spaces", "legacy-ls-history"})):
            return "06", None
        if segments.intersection({"reference-options", "eligible-contracts"}):
            return "02", None
        return "07", None
    if root == "finance":
        section = path.lower().removeprefix("finance/").partition("/")[0]
        mapping = {
            "incoming-payments": "16", "customer-options": "16", "ar-summary": "17", "contract-ledger": "17",
            "fees": "15", "case-fees": "15", "fee-informs": "15", "jar-fees": "15", "receipt-files": "15",
            "internal-fees": "18", "internal-review-requests": "18", "internal-applications": "18",
            "archive-settlements": "18", "general-settlements": "18", "settlements": "18",
            "payment-applications": "19", "payment-packages": "19", "payment-source": "19",
            "payment-types": "19", "payment-workflow": "19", "legacy-payment-history": "19",
            "invoice-context": "20", "invoices": "20", "refunds": "21", "reconciliations": "21",
            "transactions": "21", "legacy-history": "21",
        }
        if section in mapping:
            return mapping[section], None
        if path.lower() in {"finance/projection/fees", "finance/projection/transactions"}:
            return ("15" if path.lower().endswith("/fees") else "21"), None
        if section == "summary":
            return "25", "reporting"
    platform = {
        "reports": "reporting", "notifications": "notifications_feedback", "feedback": "notifications_feedback",
        "system": "system_parameters", "records": "system_parameters", "audit": "system_parameters", "search": "system_parameters",
        "agent": "ai_documents_skills", "agent-admin": "ai_documents_skills", "templates": "ai_documents_skills", "capability-market": "ai_documents_skills",
    }
    if root in platform:
        return "25", platform[root]
    raise ValueError(f"业务工具尚未分组：{method} {route.path} ({route.name})")


def _score(query: str, text: str) -> int:
    terms = re.findall(r"[a-z0-9_-]+|[\u4e00-\u9fff]{2,}", query.lower())
    phrases = {term[i:i + 2] for term in terms if re.fullmatch(r"[\u4e00-\u9fff]+", term) for i in range(len(term) - 1)}
    return sum(10 for term in terms if term in text.lower()) + sum(2 for term in phrases if term in text)


def group_summaries(tools, query: str | None = None) -> list[dict]:
    if query is not None and (not isinstance(query, str) or not query.strip()):
        raise HTTPException(422, "组查询 query 必须为非空字符串")
    counts = Counter(tool.group_id for tool in tools)
    subcounts = Counter(tool.subgroup_id for tool in tools if tool.group_id == "25")
    result = []
    intents = business_intent_groups(query) if query else set()
    for group_id, (name, purpose, keywords) in GROUPS.items():
        score = _score(query, f"{group_id} {name} {purpose} {keywords}") if query else 0
        if query and group_id == "25":
            score += sum(_score(query, f"{key} {title} {words}") for key, (title, words) in SUBGROUPS.items())
        if group_id in intents:
            score += 200
        if query and not score:
            continue
        item = {"group_id": group_id, "name": name, "purpose": purpose, "tool_count": counts[group_id]}
        if group_id in WORKFLOW_GROUPS:
            item["related_group_ids"] = list(WORKFLOW_GROUPS[group_id])
        if group_id == "25":
            item["subgroups"] = [
                {"subgroup_id": key, "name": title, "tool_count": subcounts[key]}
                for key, (title, keywords) in SUBGROUPS.items()
                if not query or query.strip() == "25" or _score(query, f"{key} {title} {keywords}")
            ]
        result.append((score, group_id, item))
    return [item for _, _, item in sorted(result, key=lambda entry: (-entry[0], entry[1]))]

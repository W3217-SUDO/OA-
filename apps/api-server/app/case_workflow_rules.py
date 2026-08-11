from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


MANUAL_VERSION = "2026-08"
MANUAL_NAME = "知识产权案件标准化操作手册"

PHASES = [
    {"code": "document-preparation", "name": "文书准备", "target_days": 60, "warning_days": 90},
    {"code": "customer-seal", "name": "客户盖章", "target_days": 30, "warning_days": 60},
    {"code": "waiting-filing", "name": "等待立案", "target_days": None, "warning_days": None},
    {"code": "supplement-evidence", "name": "补充取证", "target_days": None, "warning_days": None},
    {"code": "filing", "name": "提交立案", "target_days": 30, "warning_days": 30},
    {"code": "first-instance", "name": "一审阶段", "target_days": None, "warning_days": None},
    {"code": "second-instance", "name": "二审阶段", "target_days": None, "warning_days": None},
    {"code": "retrial", "name": "再审阶段", "target_days": None, "warning_days": None},
    {"code": "enforcement", "name": "执行阶段", "target_days": 60, "warning_days": 120},
    {"code": "archive", "name": "结算归档", "target_days": 30, "warning_days": 30},
]

MATERIALS = [
    ("authorization", "授权委托书", True, ["授权委托书"]),
    ("complaint", "起诉状", True, ["起诉状", "诉状"]),
    ("license", "原告营业执照", True, ["营业执照"]),
    ("identity", "法定代表人身份证明", True, ["身份证明"]),
    ("law-firm-letter", "律师事务所函", True, ["所函", "律师事务所函"]),
    ("lawyer-license", "律师证复印件", True, ["律师证"]),
    ("defendant-profile", "被告主体信息", True, ["被告主体", "企业信用", "工商内档"]),
    ("evidence-index", "证据目录", True, ["证据目录"]),
    ("evidence", "完整证据材料", True, ["证据材料", "公证书", "时间戳"]),
    ("preservation", "财产保全申请书", False, ["财产保全申请"]),
    ("investigation-order", "调查令申请书", False, ["调查令申请"]),
    ("evidence-preservation", "证据保全申请书", False, ["证据保全申请"]),
]

ROLE_TASKS = {
    "document-preparation": [
        ("文书", "核对卷宗、公证书、发票和系统信息，制作并上传起诉材料"),
        ("主办律师", "确定诉讼方案、证据方向并审核定稿"),
        ("分案人员", "补齐档案袋、公证书及缺失的前端材料"),
    ],
    "customer-seal": [
        ("文书", "登记用印材料并跟踪盖章回收"),
        ("品管", "超过60个工作日未回收时跟进客户"),
        ("主办律师", "处理客户拒绝盖章或核心沟通事项"),
    ],
    "waiting-filing": [
        ("文书", "记录等待原因并建立跟进任务"),
        ("主办律师", "处理管辖、主体或其他法律判断事项"),
    ],
    "supplement-evidence": [
        ("调查员", "按任务要求补充或补正证据"),
        ("文书", "核查补正结果并更新系统阶段"),
        ("主办律师", "确认补证方向与证据可用性"),
    ],
    "filing": [
        ("文书", "提交立案、登记材料与快递信息并跟进受理"),
        ("主办律师", "签署材料并处理立案异常"),
        ("财务", "按缴费通知完成诉讼费缴纳"),
    ],
    "first-instance": [
        ("文书", "监控举证、开庭和收文期限，准备庭审材料"),
        ("开庭律师", "核对原件、出庭并反馈庭审结果"),
        ("主办律师", "处理诉讼策略和客户核心沟通"),
    ],
    "second-instance": [
        ("文书", "登记二审信息并跟踪材料和排期"),
        ("主办律师", "确定二审方案并审核材料"),
    ],
    "retrial": [
        ("文书", "登记再审节点并跟踪法院流程"),
        ("主办律师", "判断再审条件、方案和客户决定"),
    ],
    "enforcement": [
        ("文书", "准备执行材料、建立跟进任务并更新执行进度"),
        ("经办律师", "判决生效后1个月内协商执行方案，2个月内申请执行"),
        ("财务", "核对执行回款、退费及票据"),
    ],
    "archive": [
        ("文书", "核对到账、退费、结算材料并在结案后30天内归档"),
        ("开庭律师", "审核卷宗并签署归档材料"),
        ("品管", "核对客户回款和对账状态"),
        ("财务", "完成结算、开票及到账确认"),
    ],
}

AGENT_RULES = [
    "只使用当前账号有权访问的案件空间数据，不得臆测缺失事实。",
    "区分已确认事实、缺失信息、期限风险和处理建议。",
    "不得自行推算未提供起算日的法定期限；起算依据不足时必须提示人工确认。",
    "期限临近、材料缺失和阶段停滞必须标注风险等级及责任岗位。",
    "任何新增任务、提醒、材料变更、阶段更新和审批都必须先形成待审批操作。",
    "不得替代主办律师作出诉讼策略、上诉、执行或客户核心沟通决定。",
]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _parse_date(value: Any) -> date | None:
    raw = _text(value)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw[:10]).date()
    except ValueError:
        return None


def _phase_code(case: dict[str, Any]) -> str:
    data = case.get("data") or {}
    raw = " ".join(
        _text(value)
        for value in (data.get("current_phase"), data.get("case_phase"), data.get("phase"), case.get("status"))
        if _text(value)
    )
    aliases = [
        ("archive", ("归档", "结案", "已结")),
        ("enforcement", ("执行", "终本")),
        ("retrial", ("再审",)),
        ("second-instance", ("二审", "上诉")),
        ("first-instance", ("一审", "审理", "开庭")),
        ("supplement-evidence", ("补充取证", "补证")),
        ("waiting-filing", ("等待立案", "待立案")),
        ("filing", ("提交立案", "立案中", "已立案")),
        ("customer-seal", ("客户盖章", "盖章", "用印")),
        ("document-preparation", ("文书", "材料", "草稿", "办理中", "新案")),
    ]
    return next((code for code, names in aliases if any(name in raw for name in names)), "document-preparation")


def _risk(deadline: date, today: date) -> tuple[str, int]:
    days = (deadline - today).days
    if days < 0:
        return "overdue", days
    if days <= 3:
        return "critical", days
    if days <= 7:
        return "high", days
    if days <= 30:
        return "medium", days
    return "normal", days


def _deadline_item(*, code: str, title: str, deadline: date, today: date, source: str, owner_role: str) -> dict[str, Any]:
    risk, days = _risk(deadline, today)
    return {
        "code": code,
        "title": title,
        "deadline": deadline.isoformat(),
        "risk": risk,
        "days_remaining": days,
        "source": source,
        "owner_role": owner_role,
    }


def _deadline_guidance(snapshot: dict[str, Any], today: date) -> tuple[list[dict[str, Any]], list[str]]:
    result: list[dict[str, Any]] = []
    missing_inputs: list[str] = []
    for item in snapshot.get("deadlines") or []:
        due = _parse_date(item.get("deadline"))
        if due:
            result.append(_deadline_item(
                code=f"existing:{item.get('type', 'deadline')}:{item.get('id', '')}",
                title=_text(item.get("title")) or _text(item.get("type")) or "案件期限",
                deadline=due,
                today=today,
                source="案件空间现有期限",
                owner_role="案件负责人",
            ))
    case = snapshot.get("case") or {}
    data = case.get("data") or {}
    preservation_expiry = _parse_date(data.get("preservation_expiry") or data.get("asset_preservation_expiry"))
    if preservation_expiry:
        result.append(_deadline_item(
            code="preservation-renewal",
            title="启动保全续保准备",
            deadline=preservation_expiry - timedelta(days=90),
            today=today,
            source="保全到期日前3个月",
            owner_role="文书、主办律师",
        ))
    else:
        missing_inputs.append("保全到期日（存在保全时必填）")
    judgment_effective = _parse_date(data.get("judgment_effective_date") or data.get("effective_date"))
    if judgment_effective:
        result.extend([
            _deadline_item(code="enforcement-plan", title="形成执行方案", deadline=judgment_effective + timedelta(days=30), today=today, source="判决生效后1个月", owner_role="文书、经办律师"),
            _deadline_item(code="enforcement-filing", title="申请强制执行", deadline=judgment_effective + timedelta(days=60), today=today, source="手册内部管理期限", owner_role="文书、经办律师"),
            _deadline_item(code="enforcement-legal-limit", title="强制执行法定期限边界", deadline=judgment_effective + timedelta(days=730), today=today, source="手册记载的2年法定期限，需律师复核起算", owner_role="主办律师"),
        ])
    else:
        missing_inputs.append("裁判生效日期（进入执行阶段时必填）")
    closed_at = _parse_date(data.get("closed_at") or data.get("settled_at"))
    if closed_at:
        result.append(_deadline_item(code="archive-30-days", title="完成结算归档", deadline=closed_at + timedelta(days=30), today=today, source="结案后30天", owner_role="文书"))
    result.sort(key=lambda item: (item["deadline"], item["title"]))
    return result, missing_inputs


def _material_guidance(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    searchable = [f"{_text(item.get('name') or item.get('original_name'))} {_text(item.get('category'))}".casefold() for item in documents]
    result = []
    for code, name, required, keywords in MATERIALS:
        matches = [index for index, value in enumerate(searchable) if any(keyword.casefold() in value for keyword in keywords)]
        result.append({
            "code": code,
            "name": name,
            "required": required,
            "status": "uploaded" if matches else "missing" if required else "optional",
            "matched_document_count": len(matches),
        })
    return result


def _role_guidance(snapshot: dict[str, Any], phase_code: str) -> list[dict[str, Any]]:
    people = snapshot.get("people") or []
    tasks = snapshot.get("tasks") or []
    people_by_role = {str(item.get("role")): _text(item.get("name")) for item in people}
    task_titles = [_text(item.get("title")) for item in tasks]
    result = []
    for role, task in ROLE_TASKS.get(phase_code, ROLE_TASKS["document-preparation"]):
        owner = people_by_role.get(role, "")
        completed = any(keyword in title for title in task_titles for keyword in task.split("、")[:1] if keyword)
        result.append({"role": role, "owner_name": owner, "task": task, "assignment_status": "assigned" if owner else "unassigned", "task_status": "matched" if completed else "pending"})
    return result


def build_case_workflow_guide(snapshot: dict[str, Any], reference_date: date | None = None) -> dict[str, Any]:
    today = reference_date or date.today()
    case = snapshot.get("case") or {}
    phase_code = _phase_code(case)
    current_index = next(index for index, phase in enumerate(PHASES) if phase["code"] == phase_code)
    phase_items = [
        {
            **phase,
            "state": "completed" if index < current_index else "current" if index == current_index else "pending",
        }
        for index, phase in enumerate(PHASES)
    ]
    deadlines, missing_inputs = _deadline_guidance(snapshot, today)
    materials = _material_guidance(snapshot.get("documents") or [])
    required_materials = [item for item in materials if item["required"]]
    completed_required = len([item for item in required_materials if item["status"] == "uploaded"])
    return {
        "schema_version": "1.0",
        "manual": {"name": MANUAL_NAME, "version": MANUAL_VERSION},
        "generated_at": datetime.now().astimezone().isoformat(),
        "current_phase": next(item for item in phase_items if item["state"] == "current"),
        "phases": phase_items,
        "deadlines": deadlines,
        "deadline_missing_inputs": missing_inputs,
        "materials": materials,
        "material_progress": {"completed": completed_required, "required": len(required_materials)},
        "role_tasks": _role_guidance(snapshot, phase_code),
        "agent_rules": AGENT_RULES,
        "risk_summary": {
            "overdue": len([item for item in deadlines if item["risk"] == "overdue"]),
            "critical": len([item for item in deadlines if item["risk"] == "critical"]),
            "missing_required_materials": len([item for item in materials if item["status"] == "missing"]),
            "unassigned_roles": len([item for item in _role_guidance(snapshot, phase_code) if item["assignment_status"] == "unassigned"]),
        },
    }

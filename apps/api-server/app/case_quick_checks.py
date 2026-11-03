"""案件智能体“归纳案件情况 / 优先待办事项”的检查（陶国南 11-03 12:50，501222）。

系统先按固定规则把检查结果算好放进案件空间（case_check），智能体照此汇报，不靠模型自己推断：
a. 案件要素是否齐全，阶段和已上传文书是否对得上；
b. 紧急、多次延期的案件任务；案件日志和流转 60 日内没有记录的，提醒“案件 N 日未有状态变化”（思法汇成 11-03 12:59）；
c. 合同、委托书、律师费、发票（框架合作合同前期不提醒建费用，判决后提醒执行或催收）；
d. 律师证扫描件不是必备项，只在提交法院的阶段提醒一并提交。
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.case_workflow_rules import _phase_code

FRAMEWORK_CONTRACT_TYPE = "框架合作合同"
URGENT_DAYS = 3          # 已逾期或 3 天内到期算紧急
STALE_DAYS = 60          # 案件日志和流转 60 日内没有记录算长时间未处理
POSTPONE_LIMIT = 3       # 延期 3 次及以上算多次延期
DONE_STATUSES = {"已完成", "完成", "已关闭", "关闭", "已作废", "作废", "已取消", "取消", "已拒绝", "拒绝"}
JUDGMENT_DOCS = ("判决书", "裁定书", "调解书")
FILING_DOCS = ("受理通知书", "传票", "应诉通知书", "举证通知书")
EARLY_PHASES = {"document-preparation", "customer-seal", "waiting-filing", "supplement-evidence"}
COURT_PHASES = {"filing", "first-instance", "second-instance", "retrial", "enforcement"}
AFTER_JUDGMENT_PHASES = {"second-instance", "retrial", "enforcement", "archive"}


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "、".join(_text(item) for item in value if _text(item))
    return "" if value is None else str(value).strip()


def _field(record: dict, *keys: str) -> Any:
    data = record.get("data") or {}
    for key in keys:
        for source in (record, data):
            value = source.get(key) if isinstance(source, dict) else None
            if value not in (None, "", [], {}):
                return value
    return None


def _date(value: Any) -> date | None:
    raw = _text(value)[:10]
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def _doc_names(documents: list[dict]) -> list[str]:
    return [_text(item.get("name") or item.get("original_name") or item.get("filename") or item.get("title")) for item in documents]


def _missing_fields(case: dict, people: list[dict]) -> list[str]:
    roles = {_text(item.get("role")) for item in people if _text(item.get("name"))}
    checks = [
        ("案件当事人", _field(case, "plaintiff", "plaintiffs", "defendant", "defendants", "parties")),
        ("案由", _field(case, "cause_or_charge", "cause")),
        ("经办律师", "经办律师" in roles or _field(case, "handling_lawyers", "handling_lawyer_usernames")),
        ("开庭律师", "开庭律师" in roles or _field(case, "hearing_lawyer", "court_lawyer")),
        ("律师助理", "律师助理" in roles or _field(case, "assistant", "assistant_username", "case_assistant")),
        ("法院信息", _field(case, "court", "first_court_name", "first_instance_court", "court_name")),
        ("法院案号", _field(case, "court_case_no", "first_court_case_no", "first_instance_case_no")),
    ]
    return [name for name, value in checks if not value]


def _stage_mismatch(phase: str, phase_name: str, names: list[str]) -> list[str]:
    joined = " ".join(names)
    result = []
    judgment = next((word for word in JUDGMENT_DOCS if word in joined), "")
    if judgment and phase in EARLY_PHASES | {"filing"}:
        result.append(f"已上传{judgment}，但案件阶段还是“{phase_name}”，请核对并更新阶段")
    elif judgment and phase == "first-instance":
        result.append(f"已上传{judgment}，阶段仍是“一审”，如已判决请更新阶段（上诉、执行或结案）")
    filing = next((word for word in FILING_DOCS if word in joined), "")
    if not judgment and filing and phase in EARLY_PHASES:
        result.append(f"已上传{filing}，说明法院已受理，但案件阶段还是“{phase_name}”，请核对并更新阶段")
    return result


def _task_flags(tasks: list[dict], postpones: dict[int, int], today: date) -> dict[str, list[dict]]:
    urgent, postponed = [], []
    for task in tasks:
        status = _text(_field(task, "status"))
        if status in DONE_STATUSES:
            continue
        item = {"id": task.get("id"), "title": _text(_field(task, "title")), "owner": _text(_field(task, "owner_name", "owner")),
                "deadline": _text(_field(task, "deadline"))[:10], "status": status}
        deadline = _date(item["deadline"])
        if deadline and (deadline - today).days <= URGENT_DAYS:
            urgent.append({**item, "overdue_days": max(0, (today - deadline).days)})
        count = postpones.get(task.get("id"), 0)
        if count >= POSTPONE_LIMIT:
            postponed.append({**item, "postpone_count": count})
    return {"urgent": urgent, "postponed": postponed}


def _billing(context: dict, phase: str, names: list[str]) -> list[str]:
    contracts = context.get("contracts") or []
    finances = context.get("finances") or {}
    fees = finances.get("fees") or []
    invoices = finances.get("invoices") or []
    joined = " ".join(names)
    framework = any(_text(_field(item, "contract_type")) == FRAMEWORK_CONTRACT_TYPE for item in contracts)
    judged = any(word in joined for word in JUDGMENT_DOCS) or phase in AFTER_JUDGMENT_PHASES
    result = []
    if not contracts:
        result.append("没有关联合同，请确认是否已签订合同")
    if "委托书" not in joined:
        result.append("没有上传授权委托书")
    lawyer_fees = [item for item in fees if any(word in _text(_field(item, "fee_type", "base_fee_type", "title")) for word in ("代理费", "律师费"))]
    if framework and not judged:
        pass  # 框架合作合同属于后期结算，前期不提醒新建费用。
    elif not lawyer_fees:
        result.append("还没有新建律师费（代理费）")
    if lawyer_fees and not invoices and not (framework and not judged):
        result.append("律师费已新建，还没有开具发票")
    if judged:
        result.append("已判决：请及时申请执行；符合收费条件的及时催收律师费" if framework else "已判决：请及时申请执行，并核对律师费是否收齐")
    return result


def _lawyer_license(phase: str, names: list[str]) -> list[str]:
    if phase in COURT_PHASES and "律师证" not in " ".join(names):
        return ["提交法院（立案、开庭）时请把律师证一并提交法院"]
    return []


def _case_idle(case: dict, case_last_activity: str | None, today: date) -> dict | None:
    last = _date(case_last_activity) or _date(_field(case, "created_at"))
    if not last or (today - last).days < STALE_DAYS:
        return None
    days = (today - last).days
    return {"idle_days": days, "last_activity": last.isoformat(), "message": f"案件 {days} 日未有状态变化"}


def build_case_check(context: dict, *, postpones: dict[int, int] | None = None, case_last_activity: str | None = None,
                     today: date | None = None) -> dict:
    today = today or date.today()
    case = context.get("case") or {}
    phase = _phase_code(case)
    phase_name = (context.get("standard_workflow") or {}).get("current_phase", {}).get("name") or phase
    names = _doc_names(context.get("documents") or [])
    result = {
        "generated_on": today.isoformat(),
        "rules": {"urgent_days": URGENT_DAYS, "stale_days": STALE_DAYS, "postpone_limit": POSTPONE_LIMIT},
        "a_case_elements": {"missing": _missing_fields(case, context.get("people") or []),
                            "stage_document_mismatch": _stage_mismatch(phase, phase_name, names)},
        "b_tasks": {**_task_flags(context.get("tasks") or [], postpones or {}, today),
                    "case_idle": _case_idle(case, case_last_activity, today)},
        "c_contract_and_fees": _billing(context, phase, names),
        "d_lawyer_license": _lawyer_license(phase, names),
    }
    elements, tasks = result["a_case_elements"], result["b_tasks"]
    result["issue_count"] = (len(elements["missing"]) + len(elements["stage_document_mismatch"]) + len(tasks["urgent"])
                             + len(tasks["postponed"]) + (1 if tasks["case_idle"] else 0)
                             + len(result["c_contract_and_fees"]) + len(result["d_lawyer_license"]))
    return result


QUICK_COMMAND_RULES = (
    "用户发“归纳案件情况”时，只汇报案件空间里 case_check 查到的问题（陶国南 11-03 13:37：只说发现的问题，没有问题就是好事）："
    "a 案件要素缺哪些（逐项列出并提醒补齐），阶段与文书不合逻辑的提醒更新；"
    "b 紧急任务（逾期或 3 天内到期）提醒尽快处理，case_idle 不为空时按其 message 提醒“案件 N 日未有状态变化”，多次延期（3 次及以上）的任务提醒按时真实完成、不要一再拖延；"
    "c 合同、委托书、律师费、发票的问题（框架合作合同前期不提醒建费用，判决后提醒执行或催收）；"
    "d 律师证只在提交法院时提醒。"
    "列表为空、查过没问题的项一律不写，不要写“无”“阶段与文书匹配”“合同齐全”之类；"
    "issue_count 为 0 时只回一句“未发现需要处理的问题”。"
    "用户发“优先待办事项”时，只从 case_check 里挑最重要的 5 件以内，按 1、2、3、4、5 依次一句话列出，不展开解释。"
)

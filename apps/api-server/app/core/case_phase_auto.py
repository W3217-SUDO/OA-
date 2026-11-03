"""民事案件每天凌晨自动改阶段（旧系统 P_Legal_Case_AutoUpdate，陶威 11-02 同意，由新系统自己跑）。

只针对民事（旧 CaseTypeId 110）、有效的案件：
1. 一审法定届满日是今天 → 一审庭后待判（101018）；
2. 二审法定届满日是今天 → 二审庭后待判（102016）；
3. 再审法定届满日是今天 → 再审庭后待判（103014）；
4. 当前是新案（101002）且进入该阶段已满 30 天 → 新案待分配（101010）。
按旧作业顺序依次判断，后面的规则命中会覆盖前面的。改阶段不发通知、不触发阶段规则，操作人记 system。
旧作业里注释掉的两条（归档审核核销改 106012、按变更时间改新案待分配）不做。
"""
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import or_, select

from app.models import BusinessRecord, SystemConfig, SystemParameter, WorkflowEvent

BEIJING = timezone(timedelta(hours=8))
RUN_AFTER = time(0, 30)
RUN_MARKER_KEY = "case_phase_auto_last_run"
OPERATOR = "system"
FIRST_DONE, SECOND_DONE, RETRIAL_DONE = 101018, 102016, 103014
NEW_CASE, NEW_CASE_UNASSIGNED = 101002, 101010
NEW_CASE_WAIT_DAYS = 30
# 11-03 暂停第 4 条：生产 101002 是“审核公证书”，旧系统作业并没有把满 30 天的这些案件改走（HZMS2600367 8-7 起一直在），
# 照这条会把 6 件审核公证书误改成新案待分配。旧作业真实条件确认前不改，只跑法定届满日三条。
NEW_CASE_RULE_ENABLED = False
LAWFUL_DAY_RULES = (
    (("first_instance_lawful_day", "first_intance_lawful_day"), FIRST_DONE, "一审法定届满日到期"),
    (("second_instance_lawful_day", "second_intance_lawful_day"), SECOND_DONE, "二审法定届满日到期"),
    (("last_instance_lawful_day", "last_intance_lawful_day"), RETRIAL_DONE, "再审法定届满日到期"),
)
INACTIVE_STATUSES = {"已合并", "已删除"}


def _day(value):
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text[:10]) if len(text) >= 10 else None
    except ValueError:
        return None


def _civil(record):
    data = record.data or {}
    return str(data.get("case_type_id") or "") == "110" or str(data.get("case_type") or "") in {"民事争议", "民事案件"}


def _active(record):
    data = record.data or {}
    return (record.status not in INACTIVE_STATUSES and data.get("is_active") is not False
            and str(data.get("IsActived") or "T") != "F")


def _entered_at(record, data):
    """进入当前阶段的时间：新系统的 phase_changed_at，迁移案件回退到旧阶段记录，再不行用建案时间。"""
    for key in ("phase_changed_at", "legacy_phase_created_at", "case_phase_created_at"):
        value = _day(data.get(key))
        if value:
            return value
    return record.created_at.astimezone(BEIJING).date() if record.created_at else None


def target_phase(record, today):
    """按旧作业顺序算出今天该改到的阶段；不用改就返回 None。"""
    data = record.data or {}
    current = int(data.get("case_phase_id") or 0)
    target, reason = None, ""
    for keys, phase_id, rule in LAWFUL_DAY_RULES:
        if any(_day(data.get(key)) == today for key in keys) and (target or current) != phase_id:
            target, reason = phase_id, rule
    if target is None and NEW_CASE_RULE_ENABLED and current == NEW_CASE:
        entered = _entered_at(record, data)
        if entered and (today - entered).days >= NEW_CASE_WAIT_DAYS:
            target, reason = NEW_CASE_UNASSIGNED, f"新案满 {NEW_CASE_WAIT_DAYS} 天"
    return (target, reason) if target and target != current else (None, "")


async def _legacy_phase(phase_id, db):
    """案件 data.case_phase_id 存的是旧系统阶段号（101018），对应系统参数 code=旧阶段号的那条（id 另编，如 172）；
    民事的优先。找不到返回 None，这一件跳过，不影响其他案件。"""
    rows = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "case_phase", SystemParameter.code == str(phase_id), SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.id))).all()
    return next((row for row in rows if str((row.extra or {}).get("case_type") or "") in {"民事争议", "民事案件"}), rows[0] if rows else None)


async def apply_civil_case_phase_rules(db, *, now=None, force=False):
    """每天凌晨 0:30 后跑一次；同一天已经跑过就不再跑。返回改了几件。"""
    import logging

    from app.core.constants import CASE_PHASE_STATUS_BY_CODE

    now = (now or datetime.now(BEIJING)).astimezone(BEIJING)
    today = now.date()
    if not force and now.time() < RUN_AFTER:
        return 0
    marker = await db.scalar(select(SystemConfig).where(SystemConfig.key == RUN_MARKER_KEY).with_for_update())
    if not force and marker is not None and (marker.value or {}).get("date") == today.isoformat():
        return 0
    lawful_keys = [key for keys, _, _ in LAWFUL_DAY_RULES for key in keys]
    candidates = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        or_(*(BusinessRecord.data[key].as_string().startswith(today.isoformat()) for key in lawful_keys),
            *([BusinessRecord.data["case_phase_id"].as_string() == str(NEW_CASE)] if NEW_CASE_RULE_ENABLED else [])),
    ))).all()
    phases, changed = {}, 0
    for record in candidates:
        if not _civil(record) or not _active(record):
            continue
        target, reason = target_phase(record, today)
        if target is None:
            continue
        if target not in phases:
            phases[target] = await _legacy_phase(target, db)
        phase = phases[target]
        if phase is None:
            logging.getLogger(__name__).warning("民事案件自动改阶段：系统参数里没有阶段 %s，案件 %s 跳过", target, record.serial_no)
            continue
        previous = record.status
        # 和沪知同步、旧系统一致：case_phase_id 记旧阶段号，系统参数 id 记在 case_phase_parameter_id（11-03 修，原来按参数 id 查不到整轮失败）。
        record.status = CASE_PHASE_STATUS_BY_CODE.get(phase.code, phase.name)
        record.data = {**(record.data or {}), "case_phase_id": target, "case_phase_parameter_id": phase.id,
                       "case_phase_name": phase.name, "phase_changed_at": now.isoformat(timespec="seconds")}
        db.add(WorkflowEvent(record_id=record.id, action="自动修改案件阶段", from_status=previous,
                             to_status=record.status, operator=OPERATOR, comment=f"{phase.name}（{target}）｜{reason}"))
        changed += 1
    value = {"date": today.isoformat(), "changed": changed, "ran_at": now.isoformat(timespec="seconds")}
    if marker is None:
        db.add(SystemConfig(key=RUN_MARKER_KEY, label="民事案件自动改阶段", group="后台任务", value=value,
                            description="每天凌晨跑一次，记录最近一次的日期和改动件数"))
    else:
        marker.value = value
    return changed

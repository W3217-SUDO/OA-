"""案件阶段“预期停留天数”（陶国南 11-03 14:01，501222）。

天数存在系统参数“案件阶段”每行的 extra.expected_days，管理员在“系统参数 › 案件阶段”里可改，空着就不提醒。
这里只是上线时按陶国南给的天数预先填一次：按阶段名对所有案件类型生效，已经填过（含管理员清空过）的不覆盖。
"""
from sqlalchemy import select
from sqlalchemy.engine import Connection

MIGRATION_REVISION = "case_phase_expected_days_v1"
EXPECTED_DAYS_KEY = "expected_days"
INITIAL_EXPECTED_DAYS = {
    "等待公证书": 30, "审核公证书": 20, "新案待分配": 60, "文书准备": 60, "客户盖章": 60,
    "提交立案": 90,
    "一审立案受理": 90, "一审准备开庭": 90, "一审通知开庭": 90, "一审再次开庭": 90,
    "一审庭后待判": 120, "二审庭后待判": 120, "再审庭后待判": 120, "仲裁庭后待判": 120,
    "一审等待上诉": 15, "一审上诉准备": 15,
    "一审待执行": 30, "二审待执行": 30, "再审待执行": 30,
    "一审和解结案": 60, "一审判决结案": 60, "二审和解结案": 60, "二审判决结案": 60,
    "再审和解结案": 60, "再审判决结案": 60, "执行结案": 60,
}


def expected_days(extra: dict | None) -> int | None:
    """读出某阶段的预期天数；没填、填错都当作不提醒。"""
    value = (extra or {}).get(EXPECTED_DAYS_KEY)
    if isinstance(value, bool):
        return None
    try:
        days = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return days if days > 0 else None


def upgrade_case_phase_expected_days(connection: Connection) -> int:
    """返回填入的阶段条数；可重复执行。"""
    from app.models import SystemParameter

    table = SystemParameter.__table__
    rows = connection.execute(select(table.c.id, table.c.name, table.c.extra).where(table.c.category == "case_phase")).all()
    changed = 0
    for row_id, name, extra in rows:
        days = INITIAL_EXPECTED_DAYS.get(str(name or "").strip())
        if days is None or EXPECTED_DAYS_KEY in (extra or {}):
            continue
        connection.execute(table.update().where(table.c.id == row_id).values(extra={**(extra or {}), EXPECTED_DAYS_KEY: days}))
        changed += 1
    return changed

"""BUG20261102013（陶国南 11-02 20:42 定）：案件任务只能发给本案人员；删除案件前案件里不能还有费用和未完成任务。"""
from sqlalchemy import String, cast, or_, select

from app.core.dependencies import AsyncSession, BusinessRecord, HTTPException, User

# 本案人员：案件里登记的人（经办律师、开庭律师、律师助理、案源人、客户管理人、调查员、案件团队、老系统参与人；
# 知识产权案件是代理人、撰稿人、处理人、提交人、案件管理人等）。
CASE_MEMBER_FIELDS = (
    "case_lawyer", "lawyer", "lawyer_username", "handling_lawyer_usernames", "handling_lawyers",
    "hearing_lawyer", "hearing_lawyer_username", "court_lawyer", "court_lawyer_username",
    "assistant", "assistant_username", "assistant_usernames",
    "source_person", "source_person_username", "source_owner", "business_owner",
    "customer_manager", "customer_managers", "investigator", "investigator_username", "case_team_usernames",
    # 知识产权案件
    "agent", "procurator", "writer", "copywriter", "submitter", "officer", "case_manager",
)
SEPARATORS = ("，", ",", ";", "；", "、", "|", " ")
CLOSED_TASK_STATUSES = {"已完成", "已验收", "已停止", "已撤回", "已取消"}
VOID_FEE_STATUSES = {"已作废", "已删除"}


def _names(value) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [name for item in value for name in _names(item)]
    if isinstance(value, dict):
        return _names(value.get("username") or value.get("staff_name") or value.get("name"))
    raw = str(value or "")
    for separator in SEPARATORS:
        raw = raw.replace(separator, ",")
    return [part.strip() for part in raw.split(",") if part.strip()]


def case_member_usernames(case_record: BusinessRecord) -> set[str]:
    data = case_record.data or {}
    names = set(_names(case_record.owner))
    for field in CASE_MEMBER_FIELDS:
        names.update(_names(data.get(field)))
    names.update(_names(data.get("legacy_participants")))
    return {name.lower() for name in names}


async def _case_records_of_task(task_data: dict, db: AsyncSession) -> list[BusinessRecord]:
    ids = {int(value) for value in [task_data.get("case_record_id"), task_data.get("case_id"), *(task_data.get("case_ids") or [])]
           if str(value or "").isdigit()}
    nos = {str(value).strip() for value in [task_data.get("case_no"), *(task_data.get("case_nos") or [])] if str(value or "").strip()}
    if not ids and not nos:
        return []
    conditions = []
    if ids:
        conditions.append(BusinessRecord.id.in_(ids))
    if nos:
        conditions.append(BusinessRecord.serial_no.in_(nos))
    return list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(("case", "ipr_case")), or_(*conditions),
    ))).all())


async def require_case_task_members(usernames, db: AsyncSession, *, case_records=None, task_data=None) -> None:
    """案件任务的负责人、协作人、接收人必须是本案人员（关联多个案件时，是其中任一案件的人员即可）。"""
    if case_records is None:
        case_records = await _case_records_of_task(task_data or {}, db)
    case_records = [record for record in case_records if record is not None]
    usernames = [name for name in dict.fromkeys(usernames) if name]
    if not case_records or not usernames:
        return
    members = set().union(*(case_member_usernames(record) for record in case_records))
    outsiders = [name for name in usernames if name.lower() not in members]
    if not outsiders:
        return
    people = {user.username: user.display_name or user.username for user in (await db.scalars(
        select(User).where(User.username.in_(outsiders)))).all()}
    case_nos = "、".join(record.serial_no for record in case_records)
    raise HTTPException(422, f"{'、'.join(people.get(name, name) for name in outsiders)} 不是案件 {case_nos} 的本案人员"
                             "（案件里登记的经办律师、开庭律师、律师助理、案源人、客户管理人、调查员等），"
                             "不能发案件任务；请改发事务性任务。")


def _text(value):
    # 编号在 JSON 里可能是数字也可能是字符串，统一按文本比。
    return cast(value.as_string(), String)


async def require_case_deletable(record: BusinessRecord, db: AsyncSession) -> None:
    """删除案件前：案件里还有费用、或有未完成（未完成、未停止、未撤回）的任务，就不能删，列出要先处理的。"""
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        or_(_text(BusinessRecord.data["case_id"]) == str(record.id), BusinessRecord.data["case_no"].as_string() == record.serial_no),
        BusinessRecord.status.not_in(VOID_FEE_STATUSES),
    ).order_by(BusinessRecord.id))).all())
    tasks = [task for task in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", BusinessRecord.status.not_in(CLOSED_TASK_STATUSES),
        or_(_text(BusinessRecord.data["case_id"]) == str(record.id),
            _text(BusinessRecord.data["case_record_id"]) == str(record.id),
            BusinessRecord.data["case_no"].as_string() == record.serial_no,
            BusinessRecord.data["case_nos"].as_string().contains(f'"{record.serial_no}"')),
    ).order_by(BusinessRecord.id))).all()]
    if not fees and not tasks:
        return
    parts = []
    if fees:
        parts.append(f"{len(fees)} 笔费用（请先删除）：" + "、".join(f"{fee.serial_no}（{fee.status}）" for fee in fees[:10])
                     + ("等" if len(fees) > 10 else ""))
    if tasks:
        parts.append(f"{len(tasks)} 个未完成任务（请先处理完成、停止或撤回）：" + "、".join(f"{task.serial_no}（{task.status}）" for task in tasks[:10])
                     + ("等" if len(tasks) > 10 else ""))
    raise HTTPException(409, f"案件 {record.serial_no} 还有 " + "；".join(parts) + "。处理完再删除案件。")

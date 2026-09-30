"""按权威客户关系限定线索审核范围，列表和单条操作使用同一条件。"""
import json

from fastapi import HTTPException
from sqlalchemy import and_, case, false, func, or_, select
from sqlalchemy.orm import aliased

from app.models import BusinessRecord, User


def _reference(record, *keys, numeric=False):
    values = [func.nullif(record.data[key].as_integer() if numeric else record.data[key].as_string(), 0 if numeric else "") for key in keys]
    return func.coalesce(*values) if len(values) > 1 else values[0]


def _customer_relations():
    record, task, parent, contract, customer = [aliased(BusinessRecord) for _ in range(5)]
    parent_id = case(
        (record.module == "investigation", record.id),
        else_=func.coalesce(
            _reference(record, "investigation_record_id", numeric=True),
            _reference(task, "investigation_record_id", numeric=True),
            case((task.module == "investigation", task.id)),
        ),
    )
    sources = [parent, task, record]
    contract_id = func.coalesce(*[_reference(item, "contract_record_id", "contract_id", numeric=True) for item in sources])
    contract_no = func.coalesce(*[_reference(item, "contract_no") for item in sources])
    customer_sources = [parent, task, contract, record]
    customer_id = func.coalesce(*[_reference(item, "customer_record_id", "customer_id", numeric=True) for item in customer_sources])
    customer_no = func.coalesce(*[_reference(item, "customer_no") for item in customer_sources])
    statement = (
        select(record.id.label("record_id"), customer.id.label("customer_id"))
        .select_from(record)
        .outerjoin(task, and_(task.id == _reference(record, "source_task_id", numeric=True), task.module.in_(["task", "investigation"])))
        .outerjoin(parent, and_(parent.id == parent_id, parent.module == "investigation"))
        .outerjoin(contract, and_(contract.module == "contract", or_(contract.id == contract_id, and_(contract_id.is_(None), contract.serial_no == contract_no))))
        .join(customer, and_(customer.module == "customer", or_(customer.id == customer_id, and_(customer_id.is_(None), customer.serial_no == customer_no))))
    )
    return statement, record, customer


async def clue_audit_condition(identity, db, *, include_job_permission=True):
    from app.core.permissions import _system_user_role_ids, _user_has_job_permission

    user = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
    if not user:
        return false()
    if "admin" in _system_user_role_ids(user) or (include_job_permission and await _user_has_job_permission(user, "线索审批", db)):
        return BusinessRecord.module == "clue"
    statement, record, customer = _customer_relations()
    managers = customer.data["customer_managers"].as_string()
    member = or_(
        managers.contains(json.dumps(user.username, ensure_ascii=False), autoescape=True),
        and_(or_(managers.is_(None), managers.in_(["", "[]"])), customer.owner == user.username),
    )
    ids = statement.with_only_columns(record.id).where(record.module == "clue", member)
    return and_(BusinessRecord.module == "clue", BusinessRecord.id.in_(ids))


async def ensure_clue_audit_record(record_id, identity, db, *, include_job_permission=True):
    from app.core.permissions import _require_record_module_menu

    await _require_record_module_menu("clue", identity, db, action="查看")
    record = await db.get(BusinessRecord, record_id)
    if not record or record.module != "clue":
        raise HTTPException(status_code=404, detail="业务记录不存在")
    allowed = await db.scalar(select(BusinessRecord.id).where(
        BusinessRecord.id == record_id,
        await clue_audit_condition(identity, db, include_job_permission=include_job_permission),
    ))
    if not allowed:
        raise HTTPException(status_code=403, detail="当前账号不是该客户的品牌管理人或线索审批人员")
    return record


async def investigation_customer_data(source, db):
    from app.core.contracts import _contract_person_values
    statement, record, customer = _customer_relations()
    customer_id = await db.scalar(statement.with_only_columns(customer.id).where(record.id == source.id))
    if not customer_id:
        return {"customer_id": None, "customer_record_id": None, "customer_no": "", "customer_managers": [], "customer_manager": ""}
    linked = await db.get(BusinessRecord, customer_id)
    managers = _contract_person_values((linked.data or {}).get("customer_managers") or [linked.owner])
    return {"customer_id": linked.id, "customer_record_id": linked.id, "customer_no": linked.serial_no,
            "customer_managers": managers, "customer_manager": "、".join(managers)}

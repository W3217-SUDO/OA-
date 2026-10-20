"""按权威客户关系限定线索审核范围，列表和单条操作使用同一条件。"""
import json

from fastapi import HTTPException
from sqlalchemy import and_, case, false, func, or_, select
from sqlalchemy.orm import aliased

from app.core.json_relation_query import scalar_in_values
from app.models import BusinessRecord, User


def _reference(record, *keys, numeric=False):
    values = [func.nullif(record.data[key].as_integer() if numeric else record.data[key].as_string(), 0 if numeric else "") for key in keys]
    return func.coalesce(*values) if len(values) > 1 else values[0]


def _relation_parts():
    """线索→任务→调查→合同的公共连接，以及从中解析出的客户记录编号表达式。

    返回 (record, joined, resolved_customer_id)：joined(*columns) 生成已带上述连接的查询；
    resolved_customer_id 是该线索对应的客户记录编号（有编号用编号，没有则按客户案号查一次）。
    """
    record, task, parent, contract = [aliased(BusinessRecord) for _ in range(4)]
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
    # 原先用 `customer.id = 编号 OR (编号为空 AND customer.serial_no = 案号)` 连接，OR 条件加上从 JSON 现算的键，
    # 数据库只能逐对比较（上万线索×上万客户要跑数分钟）。serial_no 全表唯一，所以改为先解析出目标记录编号：
    # 有编号就用编号，没有就按案号查一次（走唯一索引），再按编号等值比较，匹配结果与原先一致。
    contract_by_no, customer_by_no = aliased(BusinessRecord), aliased(BusinessRecord)
    resolved_contract_id = func.coalesce(contract_id, select(contract_by_no.id).where(
        contract_by_no.module == "contract", contract_by_no.serial_no == contract_no).scalar_subquery())
    resolved_customer_id = func.coalesce(customer_id, select(customer_by_no.id).where(
        customer_by_no.module == "customer", customer_by_no.serial_no == customer_no).scalar_subquery())

    def joined(*columns):
        return (
            select(*columns)
            .select_from(record)
            .outerjoin(task, and_(task.id == _reference(record, "source_task_id", numeric=True), task.module.in_(["task", "investigation"])))
            .outerjoin(parent, and_(parent.id == parent_id, parent.module == "investigation"))
            .outerjoin(contract, and_(contract.module == "contract", contract.id == resolved_contract_id))
        )

    return record, joined, resolved_customer_id


def _customer_relations():
    record, joined, resolved_customer_id = _relation_parts()
    customer = aliased(BusinessRecord)
    statement = joined(record.id.label("record_id"), customer.id.label("customer_id")).join(
        customer, and_(customer.module == "customer", customer.id == resolved_customer_id))
    return statement, record, customer


def _manager_member(customer_data_managers, customer_owner, username):
    """客户经理列表包含该用户；列表为空时按客户负责人（与原有可见范围规则一致）。"""
    return or_(
        customer_data_managers.contains(json.dumps(username, ensure_ascii=False), autoescape=True),
        and_(or_(customer_data_managers.is_(None), customer_data_managers.in_(["", "[]"])), customer_owner == username),
    )


async def clue_audit_condition(identity, db, *, include_job_permission=True, record_ids=None):
    """线索审核可见范围。

    record_ids 只传调用方正在判断的那几条线索（单条校验、最多 100 条的权限查询）：此时只对这几条线索求客户并判断
    经理关系，不必先扫描全部客户。不传则返回整体可见范围（列表、导出），两种写法的判定规则完全一致。
    """
    from app.core.permissions import _system_user_role_ids, _user_has_job_permission

    user = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
    if not user:
        return false()
    if "admin" in _system_user_role_ids(user) or (include_job_permission and await _user_has_job_permission(user, "线索审批", db)):
        return BusinessRecord.module == "clue"
    if record_ids is not None:
        candidate_ids = {int(value) for value in record_ids}
        if not candidate_ids:
            return false()
        statement, record, customer = _customer_relations()
        member = _manager_member(customer.data["customer_managers"].as_string(), customer.owner, user.username)
        ids = statement.with_only_columns(record.id).where(
            record.module == "clue", scalar_in_values(record.id, candidate_ids), member)
        return and_(BusinessRecord.module == "clue", BusinessRecord.id.in_(ids))
    # 先单独查出该用户管理的客户，再把这个小集合交给线索关联查询。若把客户经理条件放进整条
    # 线索→任务→调查→合同→客户的连接里，数据库无法预估符合条件的客户有多少，不同用户会选出
    # 差别极大的执行计划（同一账号换个写法可从 0.3 秒变成 60 秒）。
    visible_customer_ids = list((await db.scalars(select(BusinessRecord.id).where(
        BusinessRecord.module == "customer",
        _manager_member(BusinessRecord.data["customer_managers"].as_string(), BusinessRecord.owner, user.username),
    ))).all())
    if not visible_customer_ids:
        return false()
    # 可见客户是上一步从客户表查出的真实记录，不必再连接客户表：直接在线索一侧按解析出的客户编号筛选，
    # 每条线索只计算一次表达式，避免「线索×可见客户」的逐对过滤（规划器会把这种连接的行数估成 1 行）。
    record, joined, resolved_customer_id = _relation_parts()
    ids = joined(record.id).where(record.module == "clue", scalar_in_values(resolved_customer_id, visible_customer_ids))
    return and_(BusinessRecord.module == "clue", BusinessRecord.id.in_(ids))


async def ensure_clue_audit_record(record_id, identity, db, *, include_job_permission=True):
    from app.core.permissions import _require_record_module_menu

    await _require_record_module_menu("clue", identity, db, action="查看")
    record = await db.get(BusinessRecord, record_id)
    if not record or record.module != "clue":
        raise HTTPException(status_code=404, detail="业务记录不存在")
    allowed = await db.scalar(select(BusinessRecord.id).where(
        BusinessRecord.id == record_id,
        await clue_audit_condition(identity, db, include_job_permission=include_job_permission, record_ids=[record_id]),
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

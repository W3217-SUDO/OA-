"""管理员回收站：查看已逻辑删除的数据（谁、何时删的）并恢复。系统不提供任何物理清除入口。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import soft_delete
from app.core.permissions import _require_actual_system_admin
from app.database import get_db
from app.security import current_identity

router = APIRouter(prefix=settings.api_prefix + "/system/recycle-bin", tags=["回收站"])

TABLE_LABELS = {
    "business_records": "业务记录（案件/客户/合同/财务等）", "file_attachments": "附件", "users": "系统用户", "departments": "部门",
    "job_roles": "岗位", "law_firms": "律所档案", "law_firm_contacts": "律所联系人", "system_parameters": "系统参数", "system_menus": "系统菜单",
    "document_templates": "文档模板", "communication_logs": "沟通记录", "case_events": "案件事件", "hearing_schedules": "开庭安排",
    "case_assisted_fees": "案件辅助费用", "finance_transactions": "财务流水", "incoming_payments": "到款", "receivable_plans": "应收计划",
    "reconciliation_batches": "对账批次", "contract_objects": "合同对象", "contract_payment_lines": "合同付款行", "seal_assets": "印章资产",
    "vip_tasks": "VIP 任务", "vip_task_nodes": "VIP 任务节点", "vip_task_messages": "VIP 任务消息", "hr_subrecords": "人事子记录",
    "investigation_evidences": "调查取证", "warehouses": "仓库", "warehouse_storage_locations": "库位", "parties": "当事人",
    "agent_documents": "智能文档", "official_outgoing_documents": "公文发文",
}
RECORD_MODULES = {
    "case": "案件", "customer": "客户", "contract": "合同", "finance": "财务", "task": "任务", "investigation": "调查",
    "seal": "用印", "hr": "人事", "bug_feedback": "问题反馈", "ipr_case": "知识产权案件", "warehouse": "证物库",
}
_TITLE_CANDIDATES = ("title", "name", "original_name", "serial_no", "code", "username", "job_no", "batch_no", "receipt_no",
                     "official_no", "key", "subject", "action", "content", "description")


def _admin(identity: dict) -> None:
    _require_actual_system_admin(identity)


def _table(name: str):
    cls = soft_delete.soft_tables().get(name)
    if cls is None:
        raise HTTPException(404, "该数据类型不支持回收站")
    return cls.__table__


def _title_column(table):
    return next((table.c[name] for name in _TITLE_CANDIDATES if name in table.c), None)


class RestoreInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table: str = Field(min_length=1, max_length=64)
    ids: list[int] = Field(min_length=1, max_length=200)


@router.get("/tables")
async def recycle_tables(identity=Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _admin(identity)
    items = []
    for name, cls in sorted(soft_delete.soft_tables().items()):
        table = cls.__table__
        count = await db.scalar(select(func.count()).select_from(table).where(table.c.deleted_at.is_not(None)).execution_options(include_deleted=True))
        if count:
            items.append({"table": name, "label": TABLE_LABELS.get(name, name), "count": count})
    return {"items": items}


@router.get("")
async def recycle_list(
    table: str = Query(..., max_length=64), keyword: str = Query("", max_length=100),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    identity=Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    _admin(identity)
    target = _table(table)
    title = _title_column(target)
    conditions = [target.c.deleted_at.is_not(None)]
    keyword = keyword.strip()
    if keyword:
        searchable = [target.c[name] for name in ("title", "name", "original_name", "serial_no", "code", "username") if name in target.c]
        if searchable:
            conditions.append(or_(*(column.icontains(keyword, autoescape=True) for column in searchable)))
    options = {"include_deleted": True}
    total = await db.scalar(select(func.count()).select_from(target).where(*conditions).execution_options(**options))
    columns = [target.c.id, target.c.deleted_at, target.c.deleted_by]
    for name in ("module", "serial_no", "status"):
        if name in target.c:
            columns.append(target.c[name])
    if title is not None and title not in columns:
        columns.append(title)
    rows = (await db.execute(select(*columns).where(*conditions).order_by(target.c.deleted_at.desc(), target.c.id.desc())
                             .offset((page - 1) * page_size).limit(page_size).execution_options(**options))).mappings().all()
    items = []
    for row in rows:
        module = row.get("module")
        items.append({
            "id": row["id"], "title": str(row[title.name]) if title is not None and row.get(title.name) is not None else f"#{row['id']}",
            "serial_no": row.get("serial_no"), "module": RECORD_MODULES.get(module, module) if module else None, "status": row.get("status"),
            "deleted_at": row["deleted_at"], "deleted_by": row["deleted_by"],
        })
    return {"items": items, "total": total or 0, "page": page, "page_size": page_size, "label": TABLE_LABELS.get(table, table)}


@router.post("/restore")
async def recycle_restore(body: RestoreInput, identity=Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _admin(identity)
    _table(body.table)
    soft_delete.set_actor(identity["username"])
    try:
        restored = await db.run_sync(lambda session: soft_delete.restore_rows(session, body.table, body.ids))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "恢复失败：编号、账号或名称已被现有数据占用，请先处理冲突的数据") from None
    return {"restored": restored}

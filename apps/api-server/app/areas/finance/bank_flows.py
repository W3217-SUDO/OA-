"""银行原始流水（只读）：按旧系统 财务中心 › 回款管理 › 回款(工行/中行/国定工行/招行) 的流水列表，直接读迁移镜像表。

旧系统上传银行文件后写入这四张流水表，“导入”把选中的流水生成到账单并把状态改成 2（已导入），
“删除”把 IsActived 改成 F，列表只显示 IsActived='T' 的流水。这里同样默认只列未删除的流水，可勾选包含已删除的。

新上传的流水（陶国南 11-01 定两步）写在共用的 bank_statement_lines 表：/finance/bank-flows/lines 列表，
勾选后 /generate 生成到账单、/delete 逻辑删除。镜像表只读。
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import MetaData, Table, func, inspect, select

from app.core.dependencies import AsyncSession, Depends, current_identity, get_db, settings
from app.core.finance_centers import finance_center_identity
from app.legacy_schema import LEGACY_METADATA
from app.models import BankStatementLine, IncomingPayment

router = APIRouter()

# 列名对应旧系统页面（FAM/AR/*List 的 cshtml 与 FAM.GDICBC.js 的行渲染）。
BANK_FLOW_SOURCES = {
    "icbc": {
        "label": "工行", "table": "FAM_AR_Payment_ICBC", "date": "CashedDate", "amount": "CashedAmount",
        "payer_name": "Payer_BankName", "payer_account": "Payer_BankNo",
        "columns": [
            ("ICBC_BankNo", "管家卡卡号"), ("ICBC_BankName", "管家卡卡名称"), ("Payer_BankNo", "对方账号"),
            ("Payer_BankName", "对方户名"), ("CashedAmount", "金额"), ("PaymentModeName", "收付款标志"),
            ("CashedDate", "收付款日期"), ("ICBC_SiteNo", "渠道"), ("VoucherNo", "流水号"), ("Remark", "备注"),
            ("VoucherType", "摘要"),
        ],
    },
    "cmb": {
        "label": "招行", "table": "FAM_AR_Payment_CMB", "date": "TransactionDate", "amount": "TradeAmount",
        "payer_name": "Payer_Name", "payer_account": "Payer_Account_No",
        "columns": [
            ("TransactionType", "交易类型"), ("TransactionDate", "交易日期"), ("Payer_Account_No", "付款人账号"),
            ("Payer_Name", "付款人名称"), ("TradeAmount", "交易金额"), ("TransactionNo", "交易流水号"),
            ("Reference", "摘要"), ("Purpose", "用途"), ("Remark", "交易附言"), ("Remarks", "备注"),
        ],
    },
    "boc": {
        "label": "中行", "table": "FAM_AR_Payment_BOC", "date": "TransactionDate", "amount": "TradeAmount",
        "payer_name": "Payer_Name", "payer_account": "Payer_Account_No",
        "columns": [
            ("TransactionType", "交易类型"), ("TransactionDate", "交易日期"), ("Payer_Account_No", "付款人账号"),
            ("Payer_Name", "付款人名称"), ("TradeAmount", "交易金额"), ("TransactionNo", "交易流水号"),
            ("Reference", "摘要"), ("Purpose", "用途"), ("Remark", "交易附言"), ("Remarks", "备注"),
        ],
    },
    "gdicbc": {
        "label": "国定工行", "table": "FAM_AR_Payment_GDICBC", "date": "CashedDate", "amount": "CashedAmount",
        "payer_name": "Payer_Name", "payer_account": "Payer_BankNo",
        "columns": [
            ("ICBC_BankNo", "本方账号"), ("CashedDate", "交易时间"), ("PaymentModeName", "交易类型"),
            ("CashedAmount", "贷方发生额"), ("Payer_BankNo", "对方账号"), ("KeyWords", "摘要"), ("Usage", "用途"),
            ("Payer_Name", "对方户名"), ("Remark", "个性化信息"),
        ],
    },
}
BANK_FLOW_STATUS = {1: "未导入", 2: "已导入"}
BANK_FLOW_GROUP = {10: "律所", 20: "平台"}


def _text(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S").removesuffix(" 00:00:00")
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return str(value).strip()


_REFLECTED = MetaData()


async def _flow_table(db: AsyncSession, name: str) -> Table | None:
    """镜像表清单里有的直接用；招行表等清单里没有、迁移时另建的，从库里读表结构。"""
    if not await db.run_sync(lambda sync: inspect(sync.connection()).has_table(name)):
        return None
    if name in LEGACY_METADATA.tables:
        return LEGACY_METADATA.tables[name]
    if name not in _REFLECTED.tables:
        await db.run_sync(lambda sync: Table(name, _REFLECTED, autoload_with=sync.connection()))
    return _REFLECTED.tables[name]


@router.get(f"{settings.api_prefix}/finance/bank-flows")
async def list_bank_flows(
    bank: str = Query("gdicbc", pattern="^(icbc|cmb|boc|gdicbc)$"),
    payer_name: str = Query(""),
    payer_account: str = Query(""),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status_filter: str = Query("", alias="status", pattern="^(|1|2)$"),
    include_deleted: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    source = BANK_FLOW_SOURCES[bank]
    table = await _flow_table(db, source["table"])
    if table is None:
        raise HTTPException(status_code=404, detail="银行流水镜像表不存在")
    conditions = []
    if not include_deleted:
        conditions.append(table.c.IsActived == "T")
    if payer_name.strip():
        conditions.append(table.c[source["payer_name"]].ilike(f"%{payer_name.strip()}%"))
    if payer_account.strip():
        conditions.append(table.c[source["payer_account"]].ilike(f"%{payer_account.strip()}%"))
    if date_from:
        conditions.append(table.c[source["date"]] >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        conditions.append(table.c[source["date"]] < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    if status_filter:
        conditions.append(table.c.Status == int(status_filter))
    total = await db.scalar(select(func.count()).select_from(table).where(*conditions)) or 0
    amount = await db.scalar(select(func.coalesce(func.sum(table.c[source["amount"]]), 0)).where(*conditions)) or 0
    rows = (await db.execute(
        select(table).where(*conditions).order_by(table.c[source["date"]].desc(), table.c.PaymentId.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).mappings().all()
    items = []
    for row in rows:
        item = {"id": row["PaymentId"]}
        item.update({key: _text(row[key]) for key, _label in source["columns"]})
        deleted = str(row["IsActived"] or "").strip().upper() != "T"
        item["status"] = "已删除" if deleted else BANK_FLOW_STATUS.get(row["Status"], str(row["Status"] or ""))
        item["group"] = BANK_FLOW_GROUP.get(row["GroupId"], "") if "GroupId" in row else ""
        item["file_name"] = _text(row["FileName"])
        item["operator"] = _text(row["Operator"])
        item["created_at"] = _text(row["CreateTime"])
        items.append(item)
    return {
        "bank": bank,
        "label": source["label"],
        "columns": [{"key": key, "label": label} for key, label in source["columns"]],
        "banks": [{"key": key, "label": value["label"]} for key, value in BANK_FLOW_SOURCES.items()],
        "items": items,
        "total": int(total),
        "amount": float(amount),
        "page": page,
        "page_size": page_size,
    }



# —— 新上传流水（两步：上传→流水→勾选生成到账单）——
LINE_BANK_NAMES = {"icbc": "工行", "citic": "中信", "boc": "中行", "cmb": "招商"}
LINE_SCOPE_NAMES = {"firm": "律所", "platform": "平台"}
FLOW_MENU = {"firm": "finance-receipts-bank-flow", "platform": "platform-finance-overview-bank-flow"}


class BankFlowSelection(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


async def _require_flow_menu(identity: dict, db: AsyncSession) -> None:
    """生成到账单、删除流水要有本中心“银行原始流水”页面（给了页面 = 功能全有）。"""
    if identity.get("role") == "admin":
        return
    from app.core.permissions import _permission_payload_for_identity
    menus = set((await _permission_payload_for_identity(identity, db)).get("menu_keys") or [])
    if FLOW_MENU.get(identity["_finance_scope"]) not in menus:
        raise HTTPException(status_code=403, detail="当前账号没有“银行原始流水”页面权限")


def _line_dict(line: BankStatementLine) -> dict:
    return {
        "id": line.id, "bank": line.bank, "bank_label": LINE_BANK_NAMES.get(line.bank, line.bank),
        "finance_scope": line.finance_scope, "group": LINE_SCOPE_NAMES.get(line.finance_scope, ""),
        "received_date": str(line.received_date), "amount": float(line.amount or 0),
        "payer_name": line.payer_name, "payer_account": line.payer_account or "",
        "bank_reference": line.bank_reference or "", "remark": line.remark or "",
        "status": "已删除" if line.deleted_at else line.status, "receipt_no": line.receipt_no or "",
        "incoming_payment_id": line.incoming_payment_id, "file_name": line.file_name or "", "row_no": line.row_no,
        "operator": line.uploaded_by, "created_at": _text(line.created_at.replace(tzinfo=None)) if line.created_at else "",
        "imported_by": line.imported_by or "", "imported_at": _text(line.imported_at.replace(tzinfo=None)) if line.imported_at else "",
    }


@router.get(f"{settings.api_prefix}/finance/bank-flows/lines")
async def list_bank_flow_lines(
    bank: str = Query("", pattern="^(|icbc|citic|boc|cmb)$"),
    payer_name: str = Query(""),
    payer_account: str = Query(""),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status_filter: str = Query("未导入", alias="status", pattern="^(|未导入|已导入|已删除)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    identity: dict = Depends(finance_center_identity),
    db: AsyncSession = Depends(get_db),
):
    conditions = [BankStatementLine.finance_scope == identity["_finance_scope"]]
    if bank:
        conditions.append(BankStatementLine.bank == bank)
    if payer_name.strip():
        conditions.append(BankStatementLine.payer_name.ilike(f"%{payer_name.strip()}%"))
    if payer_account.strip():
        conditions.append(BankStatementLine.payer_account.ilike(f"%{payer_account.strip()}%"))
    if date_from:
        conditions.append(BankStatementLine.received_date >= date_from)
    if date_to:
        conditions.append(BankStatementLine.received_date <= date_to)
    include_deleted = status_filter == "已删除"
    if include_deleted:
        conditions.append(BankStatementLine.deleted_at.is_not(None))
    elif status_filter:
        conditions.append(BankStatementLine.status == status_filter)
    options = {"include_deleted": True} if include_deleted else {}
    total = await db.scalar(select(func.count()).select_from(BankStatementLine).where(*conditions).execution_options(**options)) or 0
    amount = await db.scalar(select(func.coalesce(func.sum(BankStatementLine.amount), 0)).where(*conditions).execution_options(**options)) or 0
    lines = (await db.scalars(
        select(BankStatementLine).where(*conditions)
        .order_by(BankStatementLine.received_date.desc(), BankStatementLine.id.desc())
        .offset((page - 1) * page_size).limit(page_size).execution_options(**options)
    )).all()
    return {"items": [_line_dict(line) for line in lines], "total": int(total), "amount": float(amount), "page": page, "page_size": page_size,
            "banks": [{"key": key, "label": label} for key, label in LINE_BANK_NAMES.items()]}


async def _selected_lines(body: BankFlowSelection, identity: dict, db: AsyncSession) -> list[BankStatementLine]:
    ids = sorted(set(body.ids))
    lines = list((await db.scalars(
        select(BankStatementLine).where(BankStatementLine.id.in_(ids)).with_for_update()
    )).all())
    found = {line.id for line in lines}
    if found != set(ids) or any(line.finance_scope != identity["_finance_scope"] for line in lines):
        raise HTTPException(status_code=409, detail="部分流水不存在、已删除或不属于当前财务中心，请刷新后重试")
    imported = [line for line in lines if line.status != "未导入"]
    if imported:
        raise HTTPException(status_code=409, detail=f"有 {len(imported)} 条流水已经导入，请只勾选“未导入”的流水")
    return lines


@router.post(f"{settings.api_prefix}/finance/bank-flows/generate")
async def generate_incoming_from_bank_flows(body: BankFlowSelection, identity: dict = Depends(finance_center_identity), db: AsyncSession = Depends(get_db)):
    """勾选的未导入流水逐条生成到账单（待认领），整批一起成功或一起失败；流水改为已导入并记到账单号。"""
    await _require_flow_menu(identity, db)
    lines = await _selected_lines(body, identity, db)
    references = {line.bank_reference for line in lines if line.bank_reference}
    if references:
        taken = set((await db.scalars(select(IncomingPayment.bank_reference).where(IncomingPayment.bank_reference.in_(references)))).all())
        if taken:
            raise HTTPException(status_code=409, detail=f"银行流水号已经有到账单：{'、'.join(sorted(taken)[:5])}")
    identities = {line.import_identity for line in lines if line.import_identity}
    if identities:
        taken = set((await db.scalars(select(IncomingPayment.receipt_no).where(IncomingPayment.receipt_no.in_(identities)))).all())
        if taken:
            raise HTTPException(status_code=409, detail="部分工行流水已经生成过到账单，请刷新后重试")
    now = datetime.now()
    created = []
    for index, line in enumerate(lines):
        payment = IncomingPayment(
            source_kind="bank_import", finance_scope=line.finance_scope,
            receipt_no=line.import_identity or f"HK{now:%Y%m%d%H%M%S%f}{index:03d}",
            received_date=line.received_date, amount=line.amount, payer_name=line.payer_name,
            bank_reference=line.bank_reference or None, status="待认领",
            bank_source=LINE_BANK_NAMES.get(line.bank, ""), operator=identity["username"],
            remark="；".join(part for part in [
                line.remark or "", f"对方账号 {line.payer_account}" if line.payer_account else "",
                f"由银行原始流水生成（{line.file_name or '上传文件'} 第{line.row_no}行）",
            ] if part),
        )
        db.add(payment)
        await db.flush()
        line.status, line.incoming_payment_id, line.receipt_no = "已导入", payment.id, payment.receipt_no
        line.imported_by, line.imported_at = identity["username"], now
        created.append(payment.receipt_no)
    await db.commit()
    return {"created": len(created), "receipt_nos": created}


@router.post(f"{settings.api_prefix}/finance/bank-flows/delete")
async def delete_bank_flows(body: BankFlowSelection, identity: dict = Depends(finance_center_identity), db: AsyncSession = Depends(get_db)):
    """只删未导入的流水，逻辑删除（可在“已删除”里查到）。"""
    await _require_flow_menu(identity, db)
    lines = await _selected_lines(body, identity, db)
    for line in lines:
        await db.delete(line)
    await db.commit()
    return {"deleted": len(lines)}

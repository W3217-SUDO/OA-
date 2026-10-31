"""银行原始流水（只读）：按旧系统 财务中心 › 回款管理 › 回款(工行/中行/国定工行/招行) 的流水列表，直接读迁移镜像表。

旧系统上传银行文件后写入这四张流水表，“导入”把选中的流水生成到账单并把状态改成 2（已导入），
“删除”把 IsActived 改成 F，列表只显示 IsActived='T' 的流水。这里同样默认只列未删除的流水，可勾选包含已删除的。
上传银行文件、从流水生成到账单两项暂不做，本接口不写任何数据。
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, inspect, select

from app.core.dependencies import AsyncSession, Depends, current_identity, get_db, settings
from app.legacy_schema import LEGACY_METADATA

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


async def _table_present(db: AsyncSession, name: str) -> bool:
    return await db.run_sync(lambda sync: inspect(sync.connection()).has_table(name))


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
    if not await _table_present(db, source["table"]):
        raise HTTPException(status_code=404, detail="银行流水镜像表不存在")
    table = LEGACY_METADATA.tables[source["table"]]
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


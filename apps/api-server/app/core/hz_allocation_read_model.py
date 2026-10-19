"""已验证 HZ 回款分配摘要的只读投影。"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Table, text

from app.database import Base


TABLE_NAME = "hz_incoming_allocation_read_models"

hz_allocation_read_models = Table(
    TABLE_NAME,
    Base.metadata,
    Column("payment_id", Integer, ForeignKey("incoming_payments.id", ondelete="CASCADE"), primary_key=True),
    Column("allocation_revision", String(64), nullable=False),
    Column("allocated_amount", Numeric(20, 2), nullable=False),
    Column("assigned_official_fee", Numeric(20, 2), nullable=True),
    Column("assigned_agency_fee", Numeric(20, 2), nullable=True),
    Column("assigned_other_fee", Numeric(20, 2), nullable=True),
    Column("verified", Boolean, nullable=False, server_default=text("TRUE")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)


def valid_summary(payment) -> dict | None:
    """只接受与当前 allocations 修订号和总金额一致的摘要。"""
    from app.core.incoming_local_amounts import current_hz_summary

    if payment.source_kind != "hz_crm_20260930":
        return None
    summary = payment.local_allocation_summary
    values = current_hz_summary(payment)
    if summary is None or values is None:
        return None
    return {
        "payment_id": payment.id,
        "allocation_revision": str(summary["allocation_revision"]),
        "allocated_amount": payment.allocated_amount,
        **values,
    }


async def sync_hz_allocation_read_model(payment, db) -> None:
    """在同一事务中同步一条已验证摘要；无效摘要只删除旧投影。"""
    from sqlalchemy import delete, insert

    values = valid_summary(payment)
    await db.execute(delete(hz_allocation_read_models).where(
        hz_allocation_read_models.c.payment_id == payment.id,
    ))
    if values is not None:
        await db.execute(insert(hz_allocation_read_models).values(**values))


async def backfill_hz_allocation_read_model(db, *, batch_size: int = 100) -> dict:
    """只读重算历史 HZ allocations，并回填通过校验的摘要投影。"""
    from sqlalchemy import delete, insert
    from app.core.finance_centers import incoming_source_statement
    from app.models import IncomingPayment
    from app.core.finance import _incoming_payment_legacy_summary
    from app.core.incoming_local_amounts import stamp_hz_allocation_summary

    payments = list((await db.scalars(incoming_source_statement().where(
        IncomingPayment.source_kind == "hz_crm_20260930",
    ).order_by(IncomingPayment.id))).all())
    verified = 0
    rejected = 0
    legacy_baseline_used = 0
    for offset in range(0, len(payments), batch_size):
        for payment in payments[offset:offset + batch_size]:
            summary = await stamp_hz_allocation_summary(payment, db, persist=False)
            await db.execute(delete(hz_allocation_read_models).where(
                hz_allocation_read_models.c.payment_id == payment.id,
            ))
            legacy = _incoming_payment_legacy_summary(payment)
            if not summary or any(legacy.get(field) is None for field in (
                "assigned_official_fee", "assigned_agency_fee", "assigned_other_fee",
            )):
                rejected += 1
                continue
            if any(summary.get(field) != legacy.get(field) for field in (
                "assigned_official_fee", "assigned_agency_fee", "assigned_other_fee",
            )):
                legacy_baseline_used += 1
            summary = {**summary, **{field: legacy[field] for field in (
                "assigned_official_fee", "assigned_agency_fee", "assigned_other_fee",
            )}}
            await db.execute(insert(hz_allocation_read_models).values(
                payment_id=payment.id,
                allocation_revision=summary["allocation_revision"],
                allocated_amount=summary["allocated_amount"],
                assigned_official_fee=summary["assigned_official_fee"],
                assigned_agency_fee=summary["assigned_agency_fee"],
                assigned_other_fee=summary["assigned_other_fee"],
                verified=True,
            ))
            verified += 1
        await db.commit()
    return {
        "scanned": len(payments), "verified": verified, "rejected": rejected,
        "recomputed_matches": verified - legacy_baseline_used,
        "legacy_baseline_used": legacy_baseline_used,
    }

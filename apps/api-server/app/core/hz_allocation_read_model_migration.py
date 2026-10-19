"""创建 HZ 回款分配摘要读模型，不修改原始回款或分配明细。"""

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.hz_allocation_read_model import TABLE_NAME, hz_allocation_read_models


MIGRATION_REVISION = "hz_incoming_allocation_read_model_v1"


def upgrade_hz_allocation_read_model(connection: Connection) -> None:
    if connection.dialect.name != "postgresql":
        hz_allocation_read_models.create(connection, checkfirst=True)
        return
    hz_allocation_read_models.create(connection, checkfirst=True)
    connection.execute(text(f"""
        INSERT INTO {TABLE_NAME}(
            payment_id, allocation_revision, allocated_amount,
            assigned_official_fee, assigned_agency_fee, assigned_other_fee, verified
        )
        SELECT id,
               local_allocation_summary->>'allocation_revision',
               allocated_amount,
               NULLIF(local_allocation_summary->>'assigned_official_fee', '')::numeric,
               NULLIF(local_allocation_summary->>'assigned_agency_fee', '')::numeric,
               NULLIF(local_allocation_summary->>'assigned_other_fee', '')::numeric,
               TRUE
        FROM incoming_payments
        WHERE source_kind = 'hz_crm_20260930'
          AND local_allocation_summary->>'version' = '1'
          AND local_allocation_summary->>'allocation_revision' IS NOT NULL
          AND NULLIF(local_allocation_summary->>'allocated_amount', '')::numeric = allocated_amount
          AND local_allocation_summary->>'assigned_official_fee' IS NOT NULL
          AND local_allocation_summary->>'assigned_agency_fee' IS NOT NULL
          AND local_allocation_summary->>'assigned_other_fee' IS NOT NULL
        ON CONFLICT (payment_id) DO UPDATE SET
            allocation_revision = EXCLUDED.allocation_revision,
            allocated_amount = EXCLUDED.allocated_amount,
            assigned_official_fee = EXCLUDED.assigned_official_fee,
            assigned_agency_fee = EXCLUDED.assigned_agency_fee,
            assigned_other_fee = EXCLUDED.assigned_other_fee,
            verified = TRUE,
            updated_at = CURRENT_TIMESTAMP
    """))
    connection.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{TABLE_NAME}_verified ON {TABLE_NAME}(verified, payment_id)"))
    connection.execute(text(f"ANALYZE {TABLE_NAME}"))

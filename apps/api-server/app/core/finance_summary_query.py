"""金额统计使用的只读费用字段，不包含完整历史业务快照。"""
from app.core.record_projection_query import read_record_projections


FEE_SUMMARY_FIELDS = (
    "amount", "paid_amount", "cashed_amount", "received_amount",
    "refund_amount", "refund_requested_amount", "refunded_amount",
    "case_id", "case_record_id", "case_no", "case_title", "case_type", "case_stage",
    "contract_id", "contract_record_id", "contract_no", "contract_object_id",
    "fee_type", "fee_type_name", "case_fee_type_name", "expense_subtype",
    "fee_type_id", "fee_type_code", "legacy_fee_type_code", "expense_scope",
    "legacy_case_fee_id", "legacy_fee_id", "source_fee_id", "commission_type",
    "commission_lifecycle", "is_refund", "writeoff_status", "payment_status",
    "document_no", "paid_date", "payment_date", "cashed_date", "receipt_date",
    "paid_organization", "payee", "payer_name", "received_payer_name", "deadline",
    "assistant", "lawyer_assistant", "hearing_lawyer", "investigator",
    "court_case_no", "certificate_no", "notary_no", "court_name", "court",
    "plaintiff", "opponent", "applicant", "payment_applied_by", "commission_created_by", "handler",
)


async def read_fee_summaries(db, conditions):
    return await read_record_projections(db, conditions, FEE_SUMMARY_FIELDS)

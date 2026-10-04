"""事务内维护的精简查询数据；原业务记录仍是唯一写入来源。"""
from sqlalchemy import JSON, Column, ForeignKey, Integer, Table, event, select

from app.database import Base
from app.models import BusinessRecord


# 新增字段需同时增加迁移修订，不能只扩展读取端的字段集合。
READ_MODEL_FIELDS = frozenset((
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
    "source_person_username", "source_person", "business_owner", "assistant_username",
    "court_lawyer_username", "case_team_usernames", "handling_lawyer_usernames", "legacy_participants",
    "case_phase_name", "case_phase", "business_stage", "contract_body", "signed_at",
    "source", "task_end_time", "TaskEndTime", "case_ids", "case_nos",
    "auto_task_type", "trigger_source_id", "fee_record_id", "original_payment_no",
    "first_court_hearing_date", "second_court_hearing_date",
    "retrial_court_hearing_date", "execution_court_hearing_date", "hearing_date", "next_hearing_date",
    "hearing_time", "next_hearing_time", "handling_lawyers", "courtroom",
    "first_court_name", "first_instance_court", "first_court_courtroom",
    "second_court_name", "second_instance_court", "second_court_courtroom",
    "retrial_court_name", "retrial_court_courtroom", "execution_court_name", "execution_court_courtroom",
    "archive_submitter", "archive_reviewer", "archive_internal_reviewer", "archive_reject_reason",
))
READ_MODEL_LEGACY_FIELDS = frozenset(("CasePhaseName",))
record_read_models = Table(
    "business_record_read_models", Base.metadata,
    Column("record_id", Integer, ForeignKey("business_records.id", ondelete="CASCADE"), primary_key=True),
    Column("data", JSON, nullable=False),
)


@event.listens_for(record_read_models, "after_create")
def initialize_record_read_model(_target, connection, **_kwargs):
    # 完整建库和独立版本升级共用同步规则，不允许只建空查询表。
    from app.core.record_read_model_migration import initialize_record_read_model_schema
    initialize_record_read_model_schema(connection)


def uses_record_read_model(db, keys, legacy_fields=()):
    return (db.get_bind().dialect.name == "postgresql"
            and set(keys) <= READ_MODEL_FIELDS
            and set(legacy_fields) <= READ_MODEL_LEGACY_FIELDS)


def record_json_source(db, keys):
    if not uses_record_read_model(db, keys):
        return BusinessRecord.data
    return select(record_read_models.c.data).where(
        record_read_models.c.record_id == BusinessRecord.id,
    ).correlate(BusinessRecord).scalar_subquery()

"""HZ 三项分配金额共用原费用类别及原有效性证据，不依赖显示名称。"""

from sqlalchemy import JSON, Numeric, String, and_, case, cast, func, literal, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.orm import aliased

from app.models import LegacyFinanceAllocation, LegacyFinanceRecord, SystemParameter


ASSIGNED_FIELDS = ("assigned_official_fee", "assigned_agency_fee", "assigned_other_fee")


class _AllocationBaseline(GenericFunction):
    type = JSON()
    inherit_cache = True


@compiles(_AllocationBaseline)
def _sqlite_baseline(element, compiler, **kwargs):
    return "json_group_array(json_array(%s))" % ", ".join(compiler.process(part, **kwargs) for part in element.clauses)


@compiles(_AllocationBaseline, "postgresql")
def _postgres_baseline(element, compiler, **kwargs):
    return "json_agg(json_build_array(%s))" % ", ".join(compiler.process(part, **kwargs) for part in element.clauses)


def source_text(payload, key):
    return cast(payload[key].as_string(), String)


def attach_source_fee_type(statement, fee, head):
    dictionary = aliased(LegacyFinanceRecord)
    parameter = aliased(SystemParameter)
    database = source_text(head.source_payload, "_source_database")
    fee_type_id = source_text(fee.source_payload, "CaseFeeTypeId")
    dictionary_id = case((database.is_not(None), database + literal(":") + fee_type_id), else_=fee_type_id)
    parameter_source = and_(SystemParameter.extra["source_table"].as_string() == "BAS_Case_FeeType",
                           SystemParameter.extra["migration_source"].as_string() == "hz_crm_20260930")
    unique_parameters = select(func.max(SystemParameter.id)).where(
        SystemParameter.category == "fee_type", parameter_source,
    ).group_by(SystemParameter.code).having(func.count() == 1)
    statement = statement.outerjoin(dictionary, and_(
        dictionary.source_table == "BAS_Case_FeeType", dictionary.legacy_id == dictionary_id,
        source_text(dictionary.source_payload, "FeeTypeId") == fee_type_id,
        source_text(dictionary.source_payload, "_source_database").is_not_distinct_from(database),
    )).outerjoin(parameter, and_(database.is_(None), parameter.id.in_(unique_parameters),
        parameter.code == fee_type_id,
        source_text(parameter.extra["legacy_record"], "FeeTypeId") == fee_type_id))
    # 老批次没有原字典行；只使用迁移字典保留的真实 TypeId，不以中文名称补类别。
    type_id = case((dictionary.id.is_not(None), source_text(dictionary.source_payload, "TypeId")),
                   (database.is_(None), source_text(parameter.extra["legacy_record"], "TypeId")))
    name = case((dictionary.id.is_not(None), dictionary.source_payload["FeeTypeName"].as_string()),
                (database.is_(None), parameter.name))
    return statement, type_id, name


def fee_kind_from_type_id(type_id):
    non_digits = type_id
    for digit in "0123456789":
        non_digits = func.replace(non_digits, digit, "")
    valid_type = and_(type_id != "", non_digits == "", func.replace(type_id, "0", "") != "")
    return case((type_id == "1", "official"), (type_id == "2", "agency"), (type_id == "3", "other"),
                (valid_type, "excluded"))


def source_fee_kind(type_id, line, fee):
    obj_active = source_text(line.source_payload, "IsActived")
    fee_active = source_text(fee.source_payload, "IsActived")
    return case(
        (obj_active == "F", "excluded"),
        (and_(obj_active == "T", fee_active == "F"), "excluded"),
        (and_(obj_active == "T", fee_active == "T", line.is_active.is_(True), fee.is_active.is_(True)),
         fee_kind_from_type_id(type_id)),
    )


def source_allocation_relation(line, head):
    database = source_text(head.source_payload, "_source_database")
    sequence = source_text(line.source_payload, "SeqId")
    legacy_key = case((database.is_not(None), database + literal(":") + sequence), else_=sequence)
    return and_(line.parent_source_table == "FAM_AR_Payment", line.parent_legacy_id == head.legacy_id,
        source_text(line.source_payload, "PaymentId") == source_text(head.source_payload, "PaymentId"),
        source_text(line.source_payload, "CaseFeeId") == line.legacy_case_fee_id,
        line.legacy_key == legacy_key,
        source_text(line.source_payload, "_source_database").is_not_distinct_from(database))


def legacy_assigned_amounts():
    head = aliased(LegacyFinanceRecord)
    fee = aliased(LegacyFinanceRecord)
    line = aliased(LegacyFinanceAllocation)
    database = source_text(head.source_payload, "_source_database")
    fee_id = case((database.is_not(None), database + literal(":") + line.legacy_case_fee_id),
                  else_=line.legacy_case_fee_id)
    statement = select(head.id.label("header_id")).select_from(head).outerjoin(line, and_(
        line.legacy_finance_record_id == head.id, line.source_table == "FAM_AR_Payment_Object",
    )).outerjoin(fee, and_(fee.source_table == "FAM_AR_CaseFee", fee.legacy_id == fee_id,
        source_text(fee.source_payload, "CaseFeeId") == line.legacy_case_fee_id,
        source_text(fee.source_payload, "_source_database").is_not_distinct_from(database)))
    statement, type_id, _ = attach_source_fee_type(statement, fee, head)
    relation = source_allocation_relation(line, head)
    kind = case((relation, source_fee_kind(type_id, line, fee)))
    amount = cast(func.nullif(source_text(line.source_payload, "CashedAmount"), ""), Numeric(20, 2))
    columns = []
    for label, field in zip(("official", "agency", "other"), ASSIGNED_FIELDS):
        value = case((kind == label, amount), (kind.is_not(None), 0))
        complete = case(
            (and_(func.count(line.id) == 0,
                  cast(func.nullif(source_text(head.source_payload, "AppliedAmount"), ""), Numeric(20, 2)) == 0), 0),
            (func.count(line.id) == func.count(value), func.sum(value)),
        )
        columns.append(complete.label(field))
    baseline = func.coalesce(_AllocationBaseline(source_text(line.source_payload, "SeqId"), line.legacy_case_fee_id,
        source_text(line.source_payload, "CashedAmount"), source_text(line.source_payload, "PaymentId"),
        relation.is_(True), source_text(line.source_payload, "IsActived"),
        source_text(line.source_payload, "_source_database")).filter(
            line.id.is_not(None), line.is_active.is_(True)), literal([], type_=JSON)).label("baseline_allocations")
    return statement.add_columns(*columns, baseline,
        cast(func.nullif(source_text(head.source_payload, "AppliedAmount"), ""), Numeric(20, 2)).label("baseline_applied_amount"),
    ).where(head.source_table == "FAM_AR_Payment").group_by(
        head.id, source_text(head.source_payload, "AppliedAmount"),
    ).subquery("legacy_assigned_amounts")


LEGACY_ASSIGNED_AMOUNTS = legacy_assigned_amounts()

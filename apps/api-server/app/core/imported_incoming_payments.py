"""将指定源库的原始回款晋升为现行记录，事务由入口统一管理。"""

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import String, cast, or_, select, text

from app.models import BusinessRecord, IncomingPayment, LegacyFinanceAllocation, LegacyFinanceRecord
from app.core.incoming_allocation_projection import allocation_fee_id


SOURCE_KIND = "hz_crm_20260930"
PROMOTION_KEY = "_oa_incoming_promotion"
TARGET_FIELDS = (
    "legacy_finance_record_id", "source_kind", "receipt_no", "finance_scope", "payment_method",
    "received_date", "amount", "payer_name", "bank_reference", "status", "claimed_customer",
    "contract_record_id", "contract_no", "case_no", "bank_source", "claimant", "allocated_amount",
    "allocations", "operator", "remark", "local_allocation_summary",
)
SOURCE_UPDATE_FIELDS = frozenset({
    "finance_scope", "payment_method", "received_date", "amount", "payer_name", "status",
    "claimed_customer", "contract_record_id", "contract_no", "case_no", "claimant",
    "allocated_amount", "allocations", "remark",
})


def _json(value):
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, allow_nan=False))


def _digest(value):
    return hashlib.sha256(json.dumps(_json(value), ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _identifier(value, label, *, allow_negative=False):
    raw = str(value if value is not None else "").strip()
    digits = raw[1:] if allow_negative and raw.startswith("-") else raw
    if (isinstance(value, bool) or not digits.isascii() or not digits.isdecimal()
            or int(raw) == 0 or (not allow_negative and int(raw) < 0)):
        raise ValueError(f"{label}必须是明确的旧表非零整数标识")
    return str(int(raw))


def _money(value, label):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label}缺失或不是金额") from exc
    if not number.is_finite() or number != number.quantize(Decimal("0.01")):
        raise ValueError(f"{label}必须是有限的两位小数金额")
    return number


def _raw_optional_amount(value, normalized, label):
    # 原始归档器的可空金额投影为零，原字典中的空值仍原样保留。
    expected = Decimal(0) if value is None or value == "" else _money(value, label)
    if normalized != expected:
        raise ValueError(f"{label}与原始归档投影不一致")


def _float_amount(value):
    number = float(value)
    if Decimal(str(number)) != value:
        raise ValueError("源金额超出现行金额模型的无损范围，不能舍入后晋升")
    return number


def _source(row, database, key, column, *, allow_negative=False):
    payload = dict(row.source_payload or {})
    payload.pop(PROMOTION_KEY, None)
    identifier = _identifier(payload.get(column), column, allow_negative=allow_negative)
    if (payload.get("_source_database") != database or row.legacy_id != f"{database}:{identifier}"
            or payload.get("_legacy_id") != row.legacy_id):
        raise ValueError(f"{key}源库或原主键标记不一致")
    return payload, identifier


def _source_active(payload, normalized, label):
    # 业务晋升严格复现旧 SQL 的 T/F 条件，不改变原始账本的历史归档约定。
    value = payload.get("IsActived")
    if value not in ("T", "F") or normalized != (value == "T"):
        raise ValueError(f"{label}缺少明确且一致的原始 IsActived=T/F")
    return value == "T"


async def preserve_incoming_promotion_markers(db, records):
    """原始重导只保留本工具的基线，不把源文件当作基线权威。"""
    targets = [row for row in records if row["source_table"] == "FAM_AR_Payment"]
    for database in sorted({row["source_payload"]["_source_database"] for row in targets}):
        await lock_incoming_source(db, database)
    if any(PROMOTION_KEY in row["source_payload"] for row in targets):
        raise ValueError("导入文件包含保留的回款晋升元数据键")
    ids = [row["legacy_id"] for row in targets]
    previous = {}
    for offset in range(0, len(ids), 500):
        rows = (await db.scalars(select(LegacyFinanceRecord).where(
            LegacyFinanceRecord.source_table == "FAM_AR_Payment",
            LegacyFinanceRecord.legacy_id.in_(ids[offset:offset + 500]),
        ).with_for_update())).all()
        previous.update({row.legacy_id: (row.source_payload or {}).get(PROMOTION_KEY) for row in rows})
    for row in targets:
        marker = previous.get(row["legacy_id"])
        if marker is not None:
            row["source_payload"] = {**row["source_payload"], PROMOTION_KEY: marker}


async def lock_incoming_source(db, database):
    if db.get_bind().dialect.name == "postgresql":
        acquired = await db.scalar(text("SELECT pg_try_advisory_xact_lock(hashtext(:key))"),
                                   {"key": f"oa.hz-incoming:{database}"})
        if not acquired:
            raise ValueError("同源回款导入任务忙，整批退出；请待该任务结束后重新执行")


def _original(payload):
    return {key: value for key, value in payload.items()
            if key not in {"_source_database", "_legacy_id", PROMOTION_KEY}}


async def reconcile_unnamespaced_incoming(db, records, allocations, *, adopt_legacy_baseline=False):
    """仅按完整原头及明细快照认领旧导入身份，保留原头和分配行数据库主键。"""
    headers = [row for row in records if row["source_table"] == "FAM_AR_Payment"]
    keys = [_identifier(row["source_payload"].get("PaymentId"), "PaymentId") for row in headers]
    old_by_key = defaultdict(list)
    collisions = {}
    for offset in range(0, len(headers), 500):
        chunk = headers[offset:offset + 500]
        for row in (await db.scalars(select(LegacyFinanceRecord).where(
            LegacyFinanceRecord.source_table == "FAM_AR_Payment",
            LegacyFinanceRecord.legacy_id.in_(keys[offset:offset + 500]),
        ).with_for_update())).all():
            old_by_key[row.legacy_id].append(row)
        for row in (await db.scalars(select(LegacyFinanceRecord).where(
            LegacyFinanceRecord.source_table == "FAM_AR_Payment",
            LegacyFinanceRecord.legacy_id.in_([item["legacy_id"] for item in chunk]),
        ))).all():
            collisions[row.legacy_id] = row.id
    old_ids = [row.id for rows in old_by_key.values() for row in rows]
    receipts = {}
    lines_by_header = defaultdict(list)
    for offset in range(0, len(old_ids), 500):
        ids = old_ids[offset:offset + 500]
        numbers = [f"HZ-RCPT-{row.legacy_id}" for rows in old_by_key.values() for row in rows if row.id in ids]
        for row in (await db.scalars(select(IncomingPayment).where(
            IncomingPayment.receipt_no.in_(numbers),
        ).with_for_update())).all():
            receipts[row.receipt_no] = row
        for row in (await db.scalars(select(LegacyFinanceAllocation).where(
            LegacyFinanceAllocation.legacy_finance_record_id.in_(ids),
            LegacyFinanceAllocation.source_table == "FAM_AR_Payment_Object",
        ).with_for_update())).all():
            lines_by_header[row.legacy_finance_record_id].append(row)
    for incoming in headers:
        payload = incoming["source_payload"]
        database = payload["_source_database"]
        await lock_incoming_source(db, database)
        key = _identifier(payload.get("PaymentId"), "PaymentId")
        old_rows = old_by_key[key]
        if not old_rows:
            continue
        if len(old_rows) != 1:
            raise ValueError(f"旧回款 {key} 来源不唯一，不能恢复命名空间")
        old = old_rows[0]
        receipt = receipts.get(f"HZ-RCPT-{key}")
        if receipt and receipt.local_allocation_summary is not None:
            raise ValueError(f"旧回款 {key} 已有本地分配操作摘要，首次接管必须人工对账，禁止建立源更新基线")
        if (not receipt or receipt.source_kind != SOURCE_KIND
                or receipt.legacy_finance_record_id not in (None, old.id)
                or (not receipt.allocations and not adopt_legacy_baseline)
                or (old.source_payload or {}).get("_source_database")
                or _json(_original(old.source_payload or {})) != _json(_original(payload))):
            raise ValueError(f"旧回款 {key} 缺少同源基线；请先用原始快照bundle和"
                             " --adopt-legacy-baseline 完成接管，禁止用已更新源值覆盖旧基线")
        if (_money(receipt.amount, "现行回款金额") != _money(payload.get("CashedAmount"), "源回款金额")
                or _money(receipt.allocated_amount, "现行已分金额") != _money(payload.get("AppliedAmount"), "源已分金额")):
            raise ValueError(f"旧回款 {key} 现行金额已变化，禁止恢复来源覆盖本地流程")
        expected_lines = {str(row["source_payload"].get("SeqId")): row for row in allocations
                          if row["source_table"] == "FAM_AR_Payment_Object"
                          and row["_parent_key"] == ("FAM_AR_Payment", incoming["legacy_id"])}
        old_lines = lines_by_header[old.id]
        original_lines = {str((row.source_payload or {}).get("SeqId")): row for row in old_lines}
        if len(original_lines) != len(old_lines) or set(original_lines) != set(expected_lines):
            raise ValueError(f"旧回款 {key} 原始分配主键集合不一致")
        snapshots = {}
        for item in receipt.allocations:
            head = item.get("source_header")
            line = item.get("source_object")
            if (not isinstance(head, dict) or not isinstance(line, dict)
                    or _json(_original(head)) != _json(_original(payload))):
                raise ValueError(f"旧回款 {key} 现行分配原头快照不一致")
            seq = str(line.get("SeqId"))
            if seq in snapshots or seq not in expected_lines:
                raise ValueError(f"旧回款 {key} 现行分配原主键重复或缺失")
            if _json(_original(line)) != _json(_original(expected_lines[seq]["source_payload"])):
                raise ValueError(f"旧回款 {key} 现行分配原明细快照不一致")
            if _money(item.get("amount"), "现行分配金额") != _money(line.get("CashedAmount"), "源分配金额"):
                raise ValueError(f"旧回款 {key} 现行分配金额已变化")
            snapshots[seq] = item
        active_keys = {seq for seq, row in expected_lines.items() if row["is_active"]}
        if set(snapshots) != active_keys:
            raise ValueError(f"旧回款 {key} 现行分配与原有效明细不一致")
        for seq, row in original_lines.items():
            target = expected_lines[seq]
            if _json(_original(row.source_payload or {})) != _json(_original(target["source_payload"])):
                raise ValueError(f"旧回款 {key} 原归档明细与输入不一致")
        if collisions.get(incoming["legacy_id"]) not in (None, old.id):
            raise ValueError(f"旧回款 {key} 已有另一命名空间头，禁止合并")
        # 首次接管只改来源身份；目标财务字段和历史业务快照不改。
        fingerprint = _digest({"header": _original(payload),
                               "lines": [_original(row["source_payload"]) for row in expected_lines.values()]})
        old.legacy_id = incoming["legacy_id"]
        receipt.legacy_finance_record_id = old.id
        incoming["source_payload"] = {**payload, PROMOTION_KEY: {
            "version": 1, "target_id": receipt.id, "target": _snapshot(receipt),
            "source_digest": "", "adoption_digest": fingerprint,
        }}
        old.source_payload = incoming["source_payload"]
        for seq, row in original_lines.items():
            target = expected_lines[seq]
            row.legacy_key = target["legacy_key"]
            row.parent_legacy_id = incoming["legacy_id"]
            row.source_payload = target["source_payload"]
    await db.flush()


def _relation(rows, record_id, module, serial, label):
    record = rows.get(record_id)
    if not record or record.module != module or record.status == "已删除" or record.serial_no != serial:
        raise ValueError(f"{label}缺失或与旧业务编号不一致")
    return record


def _snapshot(payment):
    return _json({key: getattr(payment, key) for key in TARGET_FIELDS})


async def promote_imported_incoming_payments(db, *, source_database, write=True):
    """校验整批再晋升；不提交、不重放新系统审批，也不改费用已收金额。"""
    database = str(source_database).strip()
    if not database or len(database) > 64 or ":" in database:
        raise ValueError("必须明确指定合法源数据库名称")
    await lock_incoming_source(db, database)
    sources = list((await db.scalars(select(LegacyFinanceRecord).where(
        LegacyFinanceRecord.source_table.in_(["FAM_AR_Payment", "FAM_AR_CaseFee", "BAS_Case_FeeType"]),
        LegacyFinanceRecord.source_payload["_source_database"].as_string() == database,
    ).order_by(LegacyFinanceRecord.id).with_for_update())).all())
    headers = [row for row in sources if row.source_table == "FAM_AR_Payment"]
    if not headers:
        raise ValueError("指定源库没有可晋升的原始回款头")
    source_fees = {}
    fee_types = {}
    for row in sources:
        if row.source_table == "BAS_Case_FeeType":
            if row.record_kind != "case_fee_type":
                raise ValueError("原始费用分类字典类型不一致")
            payload, key = _source(row, database, row.legacy_id, "FeeTypeId", allow_negative=True)
            type_id = int(_identifier(payload.get("TypeId"), "费用字典TypeId"))
            # 旧分类查询不筛字典 IsActived；原值保留，不额外增加有效性门禁。
            if key in fee_types:
                raise ValueError("同源费用分类字典主键重复")
            fee_types[key] = (payload, type_id)
        if row.source_table == "FAM_AR_CaseFee":
            if row.record_kind != "case_fee" or row.mapping_status == "ambiguous":
                raise ValueError("原始费用类型或业务关联存在歧义")
            payload, key = _source(row, database, row.legacy_id, "CaseFeeId")
            _source_active(payload, row.is_active, "原始费用")
            if key in source_fees:
                raise ValueError("同源案件费用主键重复")
            source_fees[key] = row
    if not fee_types:
        raise ValueError("缺少同源 BAS_Case_FeeType 原始分类字典，不能按费用显示名称推断")
    header_ids = [row.id for row in headers]
    lines = list((await db.scalars(select(LegacyFinanceAllocation).where(
        LegacyFinanceAllocation.source_table == "FAM_AR_Payment_Object",
        LegacyFinanceAllocation.source_payload["_source_database"].as_string() == database,
    ).order_by(LegacyFinanceAllocation.id).with_for_update())).all())
    by_header = defaultdict(list)
    for line in lines:
        payload = line.source_payload or {}
        _source_active(payload, line.is_active, "原始分配明细")
        payment_id = _identifier(payload.get("PaymentId"), "分配PaymentId")
        seq_id = _identifier(payload.get("SeqId"), "分配SeqId")
        if (line.parent_source_table != "FAM_AR_Payment"
                or line.parent_legacy_id != f"{database}:{payment_id}"
                or line.legacy_key != f"{database}:{seq_id}"
                or payload.get("_legacy_id") != line.legacy_key
                or line.legacy_finance_record_id not in header_ids or line.orphan_reason):
            raise ValueError("分配行原主键或父回款关联缺失")
        by_header[line.legacy_finance_record_id].append(line)
    relation_ids = {identifier for row in sources for identifier in (
        row.case_record_id, row.contract_record_id, row.customer_record_id,
    ) if identifier}
    relations = {}
    for offset in range(0, len(relation_ids), 500):
        chunk = sorted(relation_ids)[offset:offset + 500]
        relations.update({row.id: row for row in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(chunk),
        ))).all()})
    fee_keys = set(source_fees) | {row.legacy_id for row in source_fees.values()}
    fees = []
    for offset in range(0, len(fee_keys), 500):
        fees.extend((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance",
            cast(BusinessRecord.data["legacy_case_fee_id"].as_string(), String).in_(sorted(fee_keys)[offset:offset + 500]),
        ))).all())
    fee_targets = defaultdict(list)
    for fee in fees:
        data = fee.data or {}
        legacy = data.get("legacy_record") or {}
        if not isinstance(legacy, dict):
            continue
        raw_key = str(data.get("legacy_case_fee_id") or "")
        key = raw_key.removeprefix(database + ":")
        if key not in source_fees:
            continue
        source = source_fees[key]
        namespaced = legacy.get("_source_database") == database
        # 旧费用的正式晋升器使用明确HZ标签和真实旧键，不能要求重晋升覆盖费用。
        legacy_hz = (not legacy.get("_source_database") and data.get("legacy_kind") == "ar_case_fee"
                     and data.get("source_table") == "FAM_AR_CaseFee"
                     and data.get("legacy_source") == SOURCE_KIND
                     and data.get("migration_source") in (None, "", SOURCE_KIND) and raw_key == key
                     and data.get("case_id", data.get("case_record_id")) == source.case_record_id
                     and data.get("contract_id", data.get("contract_record_id")) == source.contract_record_id)
        if not namespaced and not legacy_hz:
            continue
        if legacy.get("CaseFeeId") is not None and _identifier(legacy["CaseFeeId"], "现行费用旧主键") != key:
            raise ValueError("现行费用原始字典主键冲突")
        if str(data.get("legacy_case_fee_id")) not in {key, f"{database}:{key}"}:
            raise ValueError("现行费用旧主键与原始字典冲突")
        fee_targets[key].append(fee)
    receipts = []
    for offset in range(0, len(headers), 500):
        chunk = headers[offset:offset + 500]
        numbers = ["HZ-RCPT-" + _identifier(row.source_payload.get("PaymentId"), "PaymentId") for row in chunk]
        receipts.extend((await db.scalars(select(IncomingPayment).where(or_(
            IncomingPayment.receipt_no.in_(numbers),
            IncomingPayment.legacy_finance_record_id.in_([row.id for row in chunk]),
        )).with_for_update())).all())
    existing = {row.receipt_no: row for row in receipts}
    if len({row.id for row in receipts}) != len(existing):
        raise ValueError("目标回款来源或业务编号存在重复")
    source_targets = defaultdict(set)
    for row in receipts:
        source_targets[row.legacy_finance_record_id].add(row.receipt_no)
    if any(len(numbers) > 1 for key, numbers in source_targets.items() if key is not None):
        raise ValueError("同一原始回款头关联了多个现行回款")
    plans = []
    report = {"source_records": len(headers), "created": 0, "updated": 0, "unchanged": 0,
              "inactive": 0, "unclassified": 0}
    for header in headers:
        if header.record_kind != "ar_payment" or header.mapping_status == "ambiguous":
            raise ValueError("原始回款类型或业务关联存在歧义")
        source, payment_id = _source(header, database, header.legacy_id, "PaymentId")
        _source_active(source, header.is_active, "原始回款头")
        number = f"HZ-RCPT-{payment_id}"
        previous = existing.get(number)
        existing_marker = (header.source_payload or {}).get(PROMOTION_KEY)
        if previous is None and existing_marker is not None:
            raise ValueError(f"{number}已有晋升基线但现行回款已删除或缺失，必须人工恢复，禁止自动重建")
        if source_targets.get(header.id, set()) - {number}:
            raise ValueError(f"{number}原始头已关联其他业务编号")
        if previous and (previous.source_kind != SOURCE_KIND or previous.legacy_finance_record_id != header.id):
            raise ValueError(f"{number}已占用且没有相同原始头外键，禁止覆盖")
        if not header.is_active:
            if previous:
                raise ValueError(f"{number}源记录失效但已晋升，必须显式处理现行业务")
            report["inactive"] += 1
            continue
        amount = _money(source.get("CashedAmount"), "回款金额")
        applied = _money(source.get("AppliedAmount"), "已分金额")
        if amount < 0 or applied < 0 or applied > amount or amount != header.primary_amount:
            raise ValueError(f"{number}回款金额或已分金额不一致")
        raw_date = str(source.get("CashedDate") or "").strip()
        try:
            received_date = datetime.fromisoformat(raw_date).date()
        except ValueError as exc:
            raise ValueError(f"{number}回款日期缺失或格式无效") from exc
        group = str(source.get("GroupId") if source.get("GroupId") is not None else "").strip()
        scope = {"10": "firm", "20": "platform"}.get(group)
        customer = None
        contract = None
        if header.legacy_customer_no:
            customer = _relation(relations, header.customer_record_id, "customer", header.legacy_customer_no, number)
        if header.legacy_contract_no:
            contract = _relation(relations, header.contract_record_id, "contract", header.legacy_contract_no, number)
            if customer and contract.customer != customer.title:
                raise ValueError(f"{number}合同与客户关系冲突")
        allocations = []
        classification_sources = []
        seen = set()
        for line in by_header[header.id]:
            original = dict(line.source_payload or {})
            if _identifier(original.get("PaymentId"), "分配PaymentId") != payment_id:
                raise ValueError(f"{number}分配行指向其他回款")
            seq = _identifier(original.get("SeqId"), "SeqId")
            if seq in seen:
                raise ValueError(f"{number}分配行主键重复")
            seen.add(seq)
            if not line.is_active:
                continue
            fee_key = _identifier(original.get("CaseFeeId"), "CaseFeeId")
            raw_fee = source_fees.get(fee_key)
            matches = fee_targets[fee_key]
            if not raw_fee or len(matches) != 1:
                raise ValueError(f"{number}同源费用未唯一关联，必须先晋升费用")
            fee = matches[0]
            fee_payload = raw_fee.source_payload or {}
            fee_type_id = _identifier(fee_payload.get("CaseFeeTypeId"), "费用CaseFeeTypeId", allow_negative=True)
            if fee_type_id not in fee_types:
                raise ValueError(f"{number}费用分类没有同源原始字典关联")
            fee_type_payload, base_type_id = fee_types[fee_type_id]
            classification_sources.append({"fee": fee_payload, "fee_type": fee_type_payload})
            if str(line.legacy_case_fee_id) != fee_key:
                raise ValueError(f"{number}分配费用主键与源字典不一致")
            if fee_payload.get("GroupId") is not None and str(fee_payload["GroupId"]).strip() != group:
                raise ValueError(f"{number}回款与原费用财务主体冲突")
            case = _relation(relations, line.case_record_id, "case", line.legacy_case_no, number)
            fee_contract = _relation(relations, raw_fee.contract_record_id, "contract", raw_fee.legacy_contract_no, number)
            if raw_fee.case_record_id != case.id or (customer and fee_contract.customer != customer.title):
                raise ValueError(f"{number}费用案件或客户关联冲突")
            data = fee.data or {}
            if int(data.get("case_id") or data.get("case_record_id") or 0) != case.id:
                raise ValueError(f"{number}现行费用案件关联不一致")
            if int(data.get("contract_id") or data.get("contract_record_id") or 0) != fee_contract.id:
                raise ValueError(f"{number}现行费用合同关联不一致")
            line_amount = _money(original.get("CashedAmount"), "分配金额")
            if line_amount < 0 or line.amount != line_amount:
                raise ValueError(f"{number}分配金额与原始明细不一致")
            _raw_optional_amount(original.get("SettlementAmount"), line.settlement_amount, "结算金额")
            _raw_optional_amount(original.get("ArchiveAmount"), line.archive_amount, "归档金额")
            fee_type_name = {1: "官方费用", 2: "代理费", 3: "其他费用"}.get(base_type_id)
            if fee_type_name is None:
                fee_type_name = str(fee_type_payload.get("FeeTypeName") or "").strip()
                if not fee_type_name:
                    raise ValueError(f"{number}原始非三类费用名称缺失")
            allocations.append({"amount": _float_amount(line_amount), "fee_id": fee.id, "fee_record_id": fee.id,
                "case_id": case.id,
                "case_no": case.serial_no, "fee_type": fee_type_name, "is_refund": line.is_refund,
                "case_fee_type_id": int(fee_type_id), "base_fee_type_id": base_type_id,
                "legacy_fee_is_active": raw_fee.is_active,
                "case_fee_id": fee.id, "contract_no": fee_contract.serial_no, "finance_record_id": fee.id,
                "source_header": source, "source_object": original,
                "payment_method": str(source.get("PaymentModeName") or "")})
        if sum((_money(row["amount"], "分配金额") for row in allocations), Decimal(0)) != applied:
            raise ValueError(f"{number}分配明细合计不等于原已分金额")
        if applied and not customer:
            raise ValueError(f"{number}已分回款没有明确客户关联")
        values = {"legacy_finance_record_id": header.id, "source_kind": SOURCE_KIND,
            "receipt_no": number, "finance_scope": scope, "payment_method": str(source.get("PaymentModeName") or ""),
            "received_date": received_date, "amount": _float_amount(amount), "payer_name": str(source.get("PayerName") or ""),
            "bank_reference": None, "status": "已分配" if amount > 0 and applied == amount else
                "部分分配" if applied > 0 else "待分配" if customer else "待认领",
            "claimed_customer": customer.title if customer else "", "contract_record_id": contract.id if contract else None,
            "contract_no": header.legacy_contract_no, "case_no": header.legacy_case_no,
            "bank_source": "", "claimant": str(source.get("Receiver") or ""), "allocated_amount": _float_amount(applied),
            "allocations": allocations, "operator": str(source.get("Registrant") or ""),
            "remark": str(source.get("Remark") or "")}
        if not values["payer_name"]:
            raise ValueError(f"{number}回款单位缺失")
        for field, limit in (("receipt_no", 64), ("payment_method", 100), ("payer_name", 255),
                             ("claimed_customer", 255), ("contract_no", 64), ("case_no", 64),
                             ("claimant", 64), ("operator", 64)):
            if len(values[field]) > limit:
                raise ValueError(f"{number}源字段{field}超过现行长度，禁止截断后导入")
        fingerprint = _digest({"header": source, "active": header.is_active,
            "lines": [{"payload": row.source_payload, "active": row.is_active} for row in by_header[header.id]],
            "classification_sources": classification_sources,
            "target": _json(values)})
        marker = (header.source_payload or {}).get(PROMOTION_KEY)
        if previous:
            if not isinstance(marker, dict) or marker.get("version") != 1 or marker.get("target_id") != previous.id:
                raise ValueError(f"{number}缺少可信晋升基线，禁止重导覆盖")
            if marker.get("source_digest") == fingerprint:
                report["unchanged"] += 1
                continue
            if marker.get("target") != _snapshot(previous):
                raise ValueError(f"{number}源更新与本地业务操作冲突，整批停止")
            if (marker.get("target_updated_at") is not None
                    and marker["target_updated_at"] != str(previous.updated_at)):
                raise ValueError(f"{number}晋升后已发生本地更新，源更新需要人工对账")
            workflow = await db.scalar(select(BusinessRecord.id).where(
                BusinessRecord.module.in_(["finance_settlement", "finance_archive_settlement"]),
                BusinessRecord.data["receipt_id"].as_integer() == previous.id,
            ).limit(1))
            if workflow:
                raise ValueError(f"{number}已发生新系统结算，禁止重导更新")
            if marker.get("adoption_digest"):
                for field in ("receipt_no", "received_date", "amount", "payer_name", "allocated_amount",
                              "status", "claimed_customer", "contract_no"):
                    if _snapshot(previous)[field] != _json(values)[field]:
                        raise ValueError(f"{number}首次接管的{field}与源快照不一致")
                original_by_seq = {str(row["source_object"]["SeqId"]): row for row in previous.allocations}
                for row in allocations:
                    original = original_by_seq[str(row["source_object"]["SeqId"])]
                    if (allocation_fee_id(original) != row["fee_id"]
                            or original.get("case_id") != row["case_id"]
                            or original.get("case_no") != row["case_no"]
                            or original.get("contract_no") != row["contract_no"]):
                        raise ValueError(f"{number}首次接管的费用、案件或合同关联不一致")
                if write:
                    header.source_payload = {**header.source_payload, PROMOTION_KEY: {
                        "version": 1, "target_id": previous.id, "source_digest": fingerprint,
                        "target": _snapshot(previous), "target_updated_at": str(previous.updated_at),
                    }}
                report["unchanged"] += 1
                continue
            previous_lines = {str((row.get("source_object") or {}).get("SeqId")): row
                              for row in previous.allocations or []}
            for row in values["allocations"]:
                original = previous_lines.get(str(row["source_object"]["SeqId"]))
                if original:
                    row.update({key: value for key, value in original.items() if key not in row})
        plans.append((header, previous, values, fingerprint))
        report["updated" if previous else "created"] += 1
        if scope is None:
            report["unclassified"] += 1
    if not write:
        return report
    for header, previous, values, fingerprint in plans:
        payment = previous or IncomingPayment()
        for key, value in values.items():
            if previous is None or key in SOURCE_UPDATE_FIELDS:
                setattr(payment, key, value)
        if previous is None:
            db.add(payment)
        await db.flush()
        await db.refresh(payment, attribute_names=["updated_at"])
        header.source_payload = {**header.source_payload, PROMOTION_KEY: {
            "version": 1, "target_id": payment.id, "source_digest": fingerprint, "target": _snapshot(payment),
            "target_updated_at": str(payment.updated_at),
        }}
    await db.flush()
    return report

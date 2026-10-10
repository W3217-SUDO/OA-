"""幂等导入旧 FAM 财务账本到只读历史投影。

输入是导出机生成的目录：目录中必须有 ``manifest.json``，清单的每个
``tables`` 项包含 ``table``、``file``、``rows`` 和压缩文件 SHA-256。
压缩 XML 采用 DataTable.WriteXml 结构，行节点可以是 ``Row``，也可以是
表名节点，字段名保持旧表原列名。

脚本只写 ``LegacyFinanceRecord``、``LegacyFinanceAllocation``、
``LegacyFinanceFile`` 和 ``LegacyFinanceAudit``。历史行不会创建或更新
活动 ``BusinessRecord``。默认执行 dry-run；只有显式传入 ``--apply`` 才会
在一个事务中批量 upsert。任何清单、校验、映射或数据库错误都会回滚并返回
非零退出码，不会静默跳过坏行。

示例：

    python scripts/import_legacy_finance.py D:/exports/SH --dry-run
    python scripts/import_legacy_finance.py D:/exports/SH --apply --report SH.json

两个旧源库应分别执行一次，且 ``manifest.json`` 的 ``source_database`` 必须
不同。导入使用 Decimal 和 ISO datetime，金额超过两位小数或非 ISO 日期会被
拒绝。文件仅导入发票文件元数据，不伪造旧物理文件。
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import (
    BusinessRecord,
    LegacyFinanceAllocation,
    LegacyFinanceAudit,
    LegacyFinanceFile,
    LegacyFinanceRecord,
)


BATCH_SIZE = 1000
TRUE_VALUES = {"T", "Y", "1", "TRUE", "YES"}
FALSE_VALUES = {"F", "N", "0", "FALSE", "NO"}

# 清单只允许这些已审计的表。未知表直接报错，避免导入后用户误以为它已被保留。
SUPPORTED_TABLES = {
    "FAM_AP_Payment",
    "FAM_AP_Payment_Audit",
    "FAM_AP_Payment_Object",
    "FAM_AP_Payment_Packing",
    "FAM_AR_CaseFee",
    "FAM_AR_Payment",
    "FAM_AR_Payment_Object",
    "FAM_InternalFee",
    "FAM_InternalFee_Payment",
    "FAM_InternalFee_Payment_Audit",
    "FAM_InternalFee_Payment_Object",
    "FAM_InternalFee_Payment_Packing",
    "FAM_Invoice",
    "FAM_Invoice_Audit",
    "FAM_Invoice_File",
    "FAM_Invoice_Object",
}

HEADER_TABLES = {
    "FAM_AP_Payment": ("ap_payment", "PaymentId", "PaidAmount", "PaymentStatus"),
    "FAM_AR_Payment": ("ar_payment", "PaymentId", "CashedAmount", "PaymentStatus"),
    "FAM_Invoice": ("invoice", "InvoiceId", "InvoiceAmount", "InvoiceStatus"),
    "FAM_InternalFee": ("internal_fee", "InternalFeeId", "Amount", "InternalFeeStatus"),
    "FAM_InternalFee_Payment": ("internal_payment", "PaymentId", "PaidAmount", "PaymentStatus"),
    "FAM_AR_CaseFee": ("case_fee", "CaseFeeId", "Amount", "CaseFeeStatus"),
    "FAM_AP_Payment_Packing": ("ap_packing", "PackingId", None, "PackingStatus"),
    "FAM_InternalFee_Payment_Packing": ("internal_packing", "PackingId", None, "PackingStatus"),
}

CHILD_TABLES = {
    "FAM_AP_Payment_Object": ("FAM_AP_Payment", "ap_payment", "PaymentId", "SeqId"),
    "FAM_AR_Payment_Object": ("FAM_AR_Payment", "ar_payment", "PaymentId", "SeqId"),
    "FAM_Invoice_Object": ("FAM_Invoice", "invoice", "InvoiceId", "SeqId"),
    "FAM_InternalFee_Payment_Object": (
        "FAM_InternalFee_Payment",
        "internal_fee_payment",
        "PaymentId",
        "SeqId",
    ),
}

AUDIT_TABLES = {
    "FAM_AP_Payment_Audit": ("FAM_AP_Payment", "ap_payment", "PaymentId", "AuditId"),
    "FAM_InternalFee_Payment_Audit": (
        "FAM_InternalFee_Payment",
        "internal_fee_payment",
        "PaymentId",
        "AuditId",
    ),
    "FAM_Invoice_Audit": ("FAM_Invoice", "invoice", "InvoiceId", "AuditId"),
}


def clean(value: Any) -> str:
    """只清理关联键外围空白，原始值仍保存在 source_payload。"""

    if value is None:
        return ""
    return str(value).strip()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_decimal(value: Any, *, field: str, table: str, row_key: str) -> Decimal:
    text = clean(value).replace(",", "")
    if not text:
        return Decimal("0.00")
    try:
        result = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{table} {row_key} 的 {field} 不是有效金额: {text!r}") from exc
    if not result.is_finite() or result.as_tuple().exponent < -2:
        raise ValueError(f"{table} {row_key} 的 {field} 超出两位小数金额精度: {text!r}")
    return result.quantize(Decimal("0.01"))


def parse_integer(value: Any, *, field: str, table: str, row_key: str) -> int:
    text = clean(value).replace(",", "")
    if not text:
        return 0
    try:
        result = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{table} {row_key} 的 {field} 不是有效整数: {text!r}") from exc
    if not result.is_finite() or result != result.to_integral_value():
        raise ValueError(f"{table} {row_key} 的 {field} 不是有效整数: {text!r}")
    return int(result)


def parse_datetime(value: Any, *, field: str, table: str, row_key: str) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{table} {row_key} 的 {field} 不是 ISO datetime: {text!r}") from exc


def parse_active(value: Any, *, table: str, row_key: str) -> bool:
    text = clean(value).upper()
    # 既有旧导入约定空 IsActived 视为有效；非空必须是明确的旧枚举。
    if not text:
        return True
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ValueError(f"{table} {row_key} 的 IsActived 不是明确 T/F 枚举: {value!r}")


def qualified_id(source_database: str, value: Any) -> str:
    result = f"{source_database}:{clean(value)}"
    if len(result) > 128:
        raise ValueError(f"旧键超过 legacy_id 128 字符限制: {result[:80]!r}")
    return result


def qualified_key(source_database: str, values: Iterable[Any]) -> str:
    parts = [clean(value) for value in values]
    if not parts or any(not part for part in parts):
        raise ValueError("复合旧键存在空主键字段")
    result = f"{source_database}:{'|'.join(parts)}"
    if len(result) > 160:
        raise ValueError(f"旧键超过 legacy_key 160 字符限制: {result[:80]!r}")
    return result


def _load_schema_primary_keys(schema_path: Path) -> dict[str, tuple[str, ...]]:
    """从项目审计清单读取每张旧表的主键。"""

    result: dict[str, tuple[str, ...]] = {}
    if not schema_path.exists():
        raise RuntimeError(f"旧表 schema manifest 不存在: {schema_path}")
    try:
        document = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取旧表 schema manifest: {schema_path}") from exc

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            table = value.get("name")
            if table in SUPPORTED_TABLES:
                primary = [
                    str(column.get("name"))
                    for column in value.get("columns", [])
                    if isinstance(column, dict) and column.get("primary_key_ordinal")
                ]
                if primary:
                    result[table] = tuple(primary)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)
    missing = sorted(table for table in SUPPORTED_TABLES if table not in result)
    if missing:
        raise RuntimeError(f"旧表 schema manifest 缺少主键定义: {', '.join(missing)}")
    return result


def _row_key(row: dict[str, Any], table: str, primary_keys: dict[str, tuple[str, ...]]) -> str:
    keys = primary_keys.get(table)
    if not keys:
        raise ValueError(f"{table} 没有经过 schema manifest 校验的主键")
    values = [row.get(key) for key in keys]
    if any(not clean(value) for value in values):
        raise ValueError(f"{table} 的主键字段 {keys} 存在空值")
    return "|".join(clean(value) for value in values)


def _read_xml_rows(path: Path, table: str) -> Iterable[dict[str, str]]:
    try:
        stream = gzip.open(path, "rb")
    except OSError as exc:
        raise RuntimeError(f"无法打开 XML gzip 文件: {path}") from exc
    try:
        context = ET.iterparse(stream, events=("end",))
        for _, element in context:
            children = list(element)
            tag = local_name(element.tag)
            if not children or (tag.lower() != "row" and tag != table):
                continue
            if tag == table and any(local_name(child.tag).lower() == "row" for child in children):
                continue
            row: dict[str, str | None] = {}
            for child in children:
                field = local_name(child.tag)
                if field in row:
                    raise ValueError(f"{path} 的一行含重复字段: {field}")
                nil = next((value for name, value in child.attrib.items() if local_name(name) == "nil"), "")
                row[field] = None if clean(nil).lower() == "true" else (child.text or "")
            yield row
            element.clear()
    except ET.ParseError as exc:
        raise RuntimeError(f"XML 解析失败: {path}") from exc
    finally:
        stream.close()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_bundle(bundle_dir: Path, primary_keys: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    bundle_dir = bundle_dir.resolve()
    manifest_path = bundle_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取 bundle manifest: {manifest_path}") from exc
    source_database = clean(manifest.get("source_database"))
    if not source_database:
        raise ValueError("manifest.source_database 不能为空")
    if len(source_database) > 64:
        raise ValueError("manifest.source_database 超过 64 字符")
    table_specs = manifest.get("tables")
    if not isinstance(table_specs, list) or not table_specs:
        raise ValueError("manifest.tables 必须是非空数组")

    rows_by_table: dict[str, list[dict[str, str]]] = {}
    table_report: dict[str, dict[str, Any]] = {}
    seen_tables: set[str] = set()
    for item in table_specs:
        if not isinstance(item, dict):
            raise ValueError("manifest.tables 含非对象项")
        table = clean(item.get("table"))
        filename = clean(item.get("file"))
        if table not in SUPPORTED_TABLES:
            raise ValueError(f"manifest 含未支持的旧表: {table}")
        if table in seen_tables:
            raise ValueError(f"manifest 重复列出旧表: {table}")
        seen_tables.add(table)
        if not filename or not isinstance(item.get("rows"), int) or item["rows"] < 0:
            raise ValueError(f"manifest {table} 的 file/rows 不完整")
        expected_hash = clean(item.get("sha256")).lower()
        if len(expected_hash) != 64 or any(character not in "0123456789abcdef" for character in expected_hash):
            raise ValueError(f"manifest {table} 的 sha256 无效")
        file_path = (bundle_dir / filename).resolve()
        if bundle_dir not in file_path.parents or not file_path.is_file():
            raise ValueError(f"manifest {table} 的文件不在 bundle 目录或不存在: {filename}")
        actual_hash = _file_sha256(file_path)
        if actual_hash != expected_hash:
            raise ValueError(f"{table} SHA-256 不匹配: expected={expected_hash}, actual={actual_hash}")

        rows: list[dict[str, str]] = []
        keys: set[str] = set()
        for row in _read_xml_rows(file_path, table):
            key = _row_key(row, table, primary_keys)
            if key in keys:
                raise ValueError(f"{table} 存在重复主键: {key}")
            keys.add(key)
            rows.append(row)
        if len(rows) != item["rows"]:
            raise ValueError(f"{table} 行数不匹配: expected={item['rows']}, actual={len(rows)}")
        rows_by_table[table] = rows
        table_report[table] = {"file": filename, "expected_rows": item["rows"], "rows": len(rows), "sha256": actual_hash}

    missing_tables = sorted(SUPPORTED_TABLES - seen_tables)
    if missing_tables:
        raise ValueError(f"manifest 缺少已审计旧表，禁止不完整导入: {', '.join(missing_tables)}")
    return {"source_database": source_database, "rows": rows_by_table, "tables": table_report}


def _payload(source_database: str, legacy_id: str, row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "_source_database": source_database, "_legacy_id": legacy_id}


def _reference(row: dict[str, Any], field: str) -> str:
    return clean(row.get(field))


def _mapping_status(refs: dict[str, str], mapping: dict[tuple[str, str], BusinessRecord]) -> str:
    present = [(module, value) for module, value in refs.items() if value]
    if not present:
        return "unmapped"
    matched = sum((module, value) in mapping for module, value in present)
    if matched == len(present):
        return "mapped"
    if matched:
        return "partial"
    return "unmapped"


def _header_refs(table: str, row: dict[str, Any]) -> dict[str, str]:
    if table in {"FAM_AP_Payment", "FAM_AR_Payment"}:
        return {"contract": _reference(row, "ContractNo"), "customer": _reference(row, "CustomerNo")}
    if table == "FAM_Invoice":
        return {"customer": _reference(row, "CustomerNo")}
    if table in {"FAM_InternalFee", "FAM_InternalFee_Payment"}:
        return {"case": _reference(row, "CaseNo")}
    if table == "FAM_AR_CaseFee":
        return {
            "contract": _reference(row, "ContractNo"),
            "case": _reference(row, "CaseNo"),
            "customer": _reference(row, "CustomerNo"),
        }
    return {}


def _record_row(source_database: str, table: str, row: dict[str, str], primary_keys: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    kind, _, amount_field, status_field = HEADER_TABLES[table]
    key_text = _row_key(row, table, primary_keys)
    legacy_id = qualified_id(source_database, key_text)
    amount = Decimal("0.00")
    if amount_field:
        amount = parse_decimal(row.get(amount_field), field=amount_field, table=table, row_key=legacy_id)
    status_code = clean(row.get(status_field))
    return {
        "source_table": table,
        "legacy_id": legacy_id,
        "record_kind": kind,
        "status_code": status_code,
        "status_label": f"旧状态码 {status_code}" if status_code else "",
        "is_active": parse_active(row.get("IsActived"), table=table, row_key=legacy_id),
        "primary_amount": amount,
        "currency": "UNRECORDED_IN_LEGACY_SCHEMA",
        "legacy_contract_no": _reference(row, "ContractNo"),
        "legacy_case_no": _reference(row, "CaseNo"),
        "legacy_customer_no": _reference(row, "CustomerNo"),
        "contract_record_id": None,
        "case_record_id": None,
        "customer_record_id": None,
        "mapping_status": "unmapped",
        "source_payload": _payload(source_database, legacy_id, row),
        "_refs": _header_refs(table, row),
        "_source_key": key_text,
    }


def _packing_rows(
    source_database: str,
    table: str,
    rows: list[dict[str, str]],
    payment_rows: list[dict[str, str]],
    primary_keys: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    amount_field = "PaidAmount"
    grouped: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    refs: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for payment in payment_rows:
        package = _reference(payment, "PackageNo")
        if not package:
            continue
        grouped[package] += parse_decimal(payment.get(amount_field), field=amount_field, table=table, row_key=package)
        for module, field in (("contract", "ContractNo"), ("case", "CaseNo"), ("customer", "CustomerNo")):
            value = _reference(payment, field)
            if value:
                refs[package][module].add(value)
    result: list[dict[str, Any]] = []
    for row in rows:
        key_text = _row_key(row, table, primary_keys)
        legacy_id = qualified_id(source_database, key_text)
        package = _reference(row, "PackageNo")
        status_code = _reference(row, HEADER_TABLES[table][3])
        row_refs = refs.get(package, {})
        values = {module: next(iter(value_set)) if len(value_set) == 1 else "" for module, value_set in row_refs.items()}
        ambiguous_refs = {module for module, value_set in row_refs.items() if len(value_set) > 1}
        result.append(
            {
                "source_table": table,
                "legacy_id": legacy_id,
                "record_kind": HEADER_TABLES[table][0],
                "status_code": status_code,
                "status_label": f"旧状态码 {status_code}" if status_code else "",
                "is_active": parse_active(row.get("IsActived"), table=table, row_key=legacy_id),
                "primary_amount": grouped.get(package, Decimal("0.00")),
                "currency": "UNRECORDED_IN_LEGACY_SCHEMA",
                "legacy_contract_no": values.get("contract", ""),
                "legacy_case_no": values.get("case", ""),
                "legacy_customer_no": values.get("customer", ""),
                "contract_record_id": None,
                "case_record_id": None,
                "customer_record_id": None,
                "mapping_status": "unmapped",
                "source_payload": _payload(source_database, legacy_id, row),
                "_refs": values,
                "_ambiguous_refs": ambiguous_refs,
                "_source_key": key_text,
            }
        )
    return result


def _build_records(bundle: dict[str, Any], primary_keys: dict[str, tuple[str, ...]]) -> list[dict[str, Any]]:
    source_database = bundle["source_database"]
    rows = bundle["rows"]
    result: list[dict[str, Any]] = []
    for table in HEADER_TABLES:
        if table in {"FAM_AP_Payment_Packing", "FAM_InternalFee_Payment_Packing"}:
            continue
        for row in rows.get(table, []):
            result.append(_record_row(source_database, table, row, primary_keys))
    result.extend(
        _packing_rows(
            source_database,
            "FAM_AP_Payment_Packing",
            rows.get("FAM_AP_Payment_Packing", []),
            rows.get("FAM_AP_Payment", []),
            primary_keys,
        )
    )
    result.extend(
        _packing_rows(
            source_database,
            "FAM_InternalFee_Payment_Packing",
            rows.get("FAM_InternalFee_Payment_Packing", []),
            rows.get("FAM_InternalFee_Payment", []),
            primary_keys,
        )
    )
    return result


def _build_allocations(bundle: dict[str, Any], primary_keys: dict[str, tuple[str, ...]]) -> list[dict[str, Any]]:
    source_database = bundle["source_database"]
    rows = bundle["rows"]
    result: list[dict[str, Any]] = []
    for table, (parent_table, kind, parent_field, _) in CHILD_TABLES.items():
        for row in rows.get(table, []):
            key_text = _row_key(row, table, primary_keys)
            legacy_key = qualified_key(source_database, [key_text])
            parent_legacy_id = qualified_id(source_database, row.get(parent_field)) if _reference(row, parent_field) else ""
            if table == "FAM_AP_Payment_Object":
                amount_field, prepaid_field, settlement_field, archive_field = "PaidAmount", "PrePaidAmount", None, None
            elif table == "FAM_AR_Payment_Object":
                amount_field, prepaid_field, settlement_field, archive_field = "CashedAmount", None, "SettlementAmount", "ArchiveAmount"
            elif table == "FAM_Invoice_Object":
                amount_field, prepaid_field, settlement_field, archive_field = "InvoicedAmount", None, None, None
            else:
                amount_field, prepaid_field, settlement_field, archive_field = "PaidAmount", "PrePaidAmount", None, None
            refs = {"case": _reference(row, "CaseNo")}
            result.append(
                {
                    "legacy_finance_record_id": None,
                    "parent_source_table": parent_table,
                    "parent_legacy_id": parent_legacy_id,
                    "orphan_reason": "",
                    "source_table": table,
                    "legacy_key": legacy_key,
                    "allocation_kind": kind,
                    "legacy_case_id": _reference(row, "CaseId"),
                    "legacy_case_no": _reference(row, "CaseNo"),
                    "legacy_case_fee_id": _reference(row, "CaseFeeId") or _reference(row, "InternalFeeId"),
                    "amount": parse_decimal(row.get(amount_field), field=amount_field, table=table, row_key=legacy_key),
                    "prepaid_amount": parse_decimal(row.get(prepaid_field), field=prepaid_field, table=table, row_key=legacy_key) if prepaid_field else Decimal("0.00"),
                    "settlement_amount": parse_decimal(row.get(settlement_field), field=settlement_field, table=table, row_key=legacy_key) if settlement_field else Decimal("0.00"),
                    "archive_amount": parse_decimal(row.get(archive_field), field=archive_field, table=table, row_key=legacy_key) if archive_field else Decimal("0.00"),
                    "is_refund": parse_active(row.get("IsRefund"), table=table, row_key=legacy_key) if "IsRefund" in row else False,
                    "is_active": parse_active(row.get("IsActived"), table=table, row_key=legacy_key),
                    "case_record_id": None,
                    "mapping_status": "unmapped",
                    "source_payload": _payload(source_database, legacy_key, row),
                    "_parent_key": (parent_table, parent_legacy_id),
                    "_refs": refs,
                }
            )
    return result


def _build_files(bundle: dict[str, Any], primary_keys: dict[str, tuple[str, ...]]) -> list[dict[str, Any]]:
    source_database = bundle["source_database"]
    result: list[dict[str, Any]] = []
    for row in bundle["rows"].get("FAM_Invoice_File", []):
        key_text = _row_key(row, "FAM_Invoice_File", primary_keys)
        legacy_key = qualified_key(source_database, [key_text])
        parent_id = _reference(row, "InvoiceId")
        parent_legacy_id = qualified_id(source_database, parent_id) if parent_id else ""
        result.append(
            {
                "legacy_finance_record_id": None,
                "source_table": "FAM_Invoice_File",
                "parent_legacy_id": parent_legacy_id,
                "orphan_reason": "",
                "legacy_key": legacy_key,
                "legacy_case_fee_id": _reference(row, "CaseFeeId"),
                "filename": clean(row.get("InvoiceFileName"))[:255],
                "size_bytes": parse_integer(row.get("InvoiceFileSize"), field="InvoiceFileSize", table="FAM_Invoice_File", row_key=legacy_key),
                "file_amount": parse_decimal(row.get("InvoiceAmount"), field="InvoiceAmount", table="FAM_Invoice_File", row_key=legacy_key),
                "invoice_date": parse_datetime(row.get("InvoiceDate"), field="InvoiceDate", table="FAM_Invoice_File", row_key=legacy_key),
                "is_active": parse_active(row.get("IsActived"), table="FAM_Invoice_File", row_key=legacy_key),
                "physical_file_verified": False,
                "source_payload": _payload(source_database, legacy_key, row),
                "_parent_key": ("FAM_Invoice", parent_legacy_id),
            }
        )
    return result


def _build_audits(bundle: dict[str, Any], primary_keys: dict[str, tuple[str, ...]]) -> list[dict[str, Any]]:
    source_database = bundle["source_database"]
    result: list[dict[str, Any]] = []
    for table, (parent_table, kind, parent_field, _) in AUDIT_TABLES.items():
        for row in bundle["rows"].get(table, []):
            key_text = _row_key(row, table, primary_keys)
            legacy_id = qualified_id(source_database, key_text)
            parent_raw = _reference(row, parent_field)
            parent_legacy_id = qualified_id(source_database, parent_raw) if parent_raw else ""
            result.append(
                {
                    "legacy_finance_record_id": None,
                    "parent_source_table": parent_table,
                    "parent_legacy_id": parent_legacy_id,
                    "orphan_reason": "",
                    "source_table": table,
                    "legacy_id": legacy_id,
                    "audit_kind": kind,
                    "audit_status_code": _reference(row, "AuditStatus"),
                    "audit_flow_id": _reference(row, "AuditFlowId"),
                    "audit_flow_node_id": _reference(row, "AuditFlowNodeId"),
                    "audit_round_id": _reference(row, "AuditRoundId"),
                    "auditor": _reference(row, "Auditor"),
                    "audit_date": parse_datetime(row.get("AuditDate"), field="AuditDate", table=table, row_key=legacy_id),
                    "audit_content": clean(row.get("AuditContent")),
                    "source_payload": _payload(source_database, legacy_id, row),
                    "_parent_key": (parent_table, parent_legacy_id),
                }
            )
    return result


async def _load_business_mapping(db, references: set[tuple[str, str]]) -> dict[tuple[str, str], BusinessRecord]:
    result: dict[tuple[str, str], BusinessRecord] = {}
    pairs = sorted(references)
    for offset in range(0, len(pairs), BATCH_SIZE):
        chunk = pairs[offset : offset + BATCH_SIZE]
        if not chunk:
            continue
        modules = sorted({module for module, _ in chunk})
        serials = sorted({serial for _, serial in chunk})
        rows = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module.in_(modules), BusinessRecord.serial_no.in_(serials)))).all())
        for row in rows:
            key = (row.module, row.serial_no)
            if key in references:
                result[key] = row
    return result


def _collect_references(records: list[dict[str, Any]], allocations: list[dict[str, Any]]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for item in records:
        for module, value in item.get("_refs", {}).items():
            if value:
                result.add((module, value))
    for item in allocations:
        value = item.get("_refs", {}).get("case", "")
        if value:
            result.add(("case", value))
    return result


def _attach_mappings(records: list[dict[str, Any]], allocations: list[dict[str, Any]], mapping: dict[tuple[str, str], BusinessRecord]) -> None:
    for item in records:
        refs = item.pop("_refs", {})
        ambiguous_refs = item.pop("_ambiguous_refs", set())
        for module, column in (("contract", "contract_record_id"), ("case", "case_record_id"), ("customer", "customer_record_id")):
            target = mapping.get((module, refs.get(module, ""))) if refs.get(module) else None
            item[column] = target.id if target else None
        item["mapping_status"] = "ambiguous" if ambiguous_refs else _mapping_status(refs, mapping)
    for item in allocations:
        refs = item.pop("_refs", {})
        target = mapping.get(("case", refs.get("case", ""))) if refs.get("case") else None
        item["case_record_id"] = target.id if target else None
        item["mapping_status"] = _mapping_status({"case": refs.get("case", "")}, mapping)


def _strip_internal(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def _insert_for_dialect(dialect_name: str):
    if dialect_name == "sqlite":
        return sqlite_insert
    if dialect_name == "postgresql":
        return postgres_insert
    raise RuntimeError(f"仅支持 SQLite/PostgreSQL，当前数据库方言为 {dialect_name}")


async def _upsert(db, model: Any, rows: list[dict[str, Any]], unique_columns: list[str]) -> None:
    if not rows:
        return
    connection = await db.connection()
    insert_factory = _insert_for_dialect(connection.dialect.name)
    model_columns = {column.name for column in model.__table__.columns}
    for offset in range(0, len(rows), BATCH_SIZE):
        chunk = [{key: value for key, value in row.items() if key in model_columns} for row in rows[offset : offset + BATCH_SIZE]]
        statement = insert_factory(model).values(chunk)
        update_values = {
            column: getattr(statement.excluded, column)
            for column in model_columns
            if column not in set(unique_columns) and column not in {"id", "imported_at", "updated_at"}
        }
        await db.execute(statement.on_conflict_do_update(index_elements=unique_columns, set_=update_values))


async def _upsert_files(db, rows: list[dict[str, Any]]) -> None:
    """文件唯一约束含可空父键，先按源键预取以保证孤儿文件也幂等。"""

    if not rows:
        return
    pairs = [(row["source_table"], row["legacy_key"]) for row in rows]
    existing: dict[tuple[str, str], LegacyFinanceFile] = {}
    for offset in range(0, len(pairs), BATCH_SIZE):
        chunk = pairs[offset : offset + BATCH_SIZE]
        existing_rows = list((await db.scalars(select(LegacyFinanceFile).where(tuple_(LegacyFinanceFile.source_table, LegacyFinanceFile.legacy_key).in_(chunk)))).all())
        existing.update({(row.source_table, row.legacy_key): row for row in existing_rows})
    existing_rows: list[dict[str, Any]] = []
    new_rows: list[dict[str, Any]] = []
    for row in rows:
        previous = existing.get((row["source_table"], row["legacy_key"]))
        values = _strip_internal(row)
        if previous is None:
            new_rows.append(values)
        else:
            existing_rows.append({"id": previous.id, **values})
    await _upsert(db, LegacyFinanceFile, existing_rows, ["id"])
    await _upsert(db, LegacyFinanceFile, new_rows, ["legacy_finance_record_id", "legacy_key"])


async def _fetch_record_ids(db, rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    pairs = [(row["source_table"], row["legacy_id"]) for row in rows]
    result: dict[tuple[str, str], int] = {}
    for offset in range(0, len(pairs), BATCH_SIZE):
        chunk = pairs[offset : offset + BATCH_SIZE]
        existing = list((await db.execute(select(LegacyFinanceRecord.source_table, LegacyFinanceRecord.legacy_id, LegacyFinanceRecord.id).where(tuple_(LegacyFinanceRecord.source_table, LegacyFinanceRecord.legacy_id).in_(chunk)))).all())
        result.update({(source_table, legacy_id): record_id for source_table, legacy_id, record_id in existing})
    return result


def _report_counts(records: list[dict[str, Any]], allocations: list[dict[str, Any]], files: list[dict[str, Any]], audits: list[dict[str, Any]]) -> dict[str, Any]:
    def grouped(items: list[dict[str, Any]], key: str) -> dict[str, int]:
        result: dict[str, int] = defaultdict(int)
        for item in items:
            result[str(item.get(key) or "") or "<empty>"] += 1
        return dict(sorted(result.items()))

    return {
        "records": len(records),
        "allocations": len(allocations),
        "files": len(files),
        "audits": len(audits),
        "record_kinds": grouped(records, "record_kind"),
        "allocation_kinds": grouped(allocations, "allocation_kind"),
        "mapping_status": {
            "records": grouped(records, "mapping_status"),
            "allocations": grouped(allocations, "mapping_status"),
        },
    }


async def run(bundle_dir: Path, *, apply: bool, report_path: Path | None = None, schema_manifest: Path | None = None) -> dict[str, Any]:
    schema_path = schema_manifest or Path(__file__).resolve().parents[1] / "app" / "legacy_schema_manifest.json"
    primary_keys = _load_schema_primary_keys(schema_path)
    bundle = load_bundle(bundle_dir, primary_keys)
    records = _build_records(bundle, primary_keys)
    allocations = _build_allocations(bundle, primary_keys)
    files = _build_files(bundle, primary_keys)
    audits = _build_audits(bundle, primary_keys)

    references = _collect_references(records, allocations)
    report: dict[str, Any] = {
        "mode": "apply" if apply else "dry-run",
        "source_database": bundle["source_database"],
        "tables": bundle["tables"],
        "source_counts": _report_counts(records, allocations, files, audits),
        "target": {"created_or_updated": {"records": 0, "allocations": 0, "files": 0, "audits": 0}},
        "mapping_reference_count": len(references),
    }
    header_keys = {(row["source_table"], row["legacy_id"]) for row in records}
    report["orphan_counts"] = {
        "allocations": sum(1 for row in allocations if row["_parent_key"] not in header_keys),
        "files": sum(1 for row in files if row["_parent_key"] not in header_keys),
        "audits": sum(1 for row in audits if row["_parent_key"] not in header_keys),
    }
    async with SessionLocal() as db:
        try:
            mapping = await _load_business_mapping(db, references)
            _attach_mappings(records, allocations, mapping)

            if apply:
                await _upsert(db, LegacyFinanceRecord, [_strip_internal(row) for row in records], ["source_table", "legacy_id"])
                header_ids = await _fetch_record_ids(db, records)
                for item in allocations:
                    item["legacy_finance_record_id"] = header_ids.get(item["_parent_key"])
                    if item["legacy_finance_record_id"] is None:
                        item["orphan_reason"] = "missing_parent_record"
                for item in files:
                    item["legacy_finance_record_id"] = header_ids.get(item["_parent_key"])
                    if item["legacy_finance_record_id"] is None:
                        item["orphan_reason"] = "missing_parent_record"
                for item in audits:
                    item["legacy_finance_record_id"] = header_ids.get(item["_parent_key"])
                    if item["legacy_finance_record_id"] is None:
                        item["orphan_reason"] = "missing_parent_record"
                for item in allocations + files + audits:
                    item.pop("_parent_key", None)
                await _upsert(db, LegacyFinanceAllocation, [_strip_internal(row) for row in allocations], ["source_table", "legacy_key"])
                await _upsert_files(db, files)
                await _upsert(db, LegacyFinanceAudit, [_strip_internal(row) for row in audits], ["source_table", "legacy_id"])
                await db.commit()
                report["target"]["created_or_updated"] = {
                    "records": len(records),
                    "allocations": len(allocations),
                    "files": len(files),
                    "audits": len(audits),
                }
            else:
                await db.rollback()
            report["mapping"] = {
                "references": len(references),
                "matched": len(mapping),
                "unmatched": len(references) - len(mapping),
            }
            report["source_counts"] = _report_counts(records, allocations, files, audits)
        except Exception:
            await db.rollback()
            raise
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入旧 FAM 财务账本到只读历史投影")
    parser.add_argument("bundle", type=Path, help="包含 manifest.json 与 XML.gz 的 bundle 目录")
    parser.add_argument("--apply", action="store_true", help="显式开启事务写入；缺省为 dry-run")
    parser.add_argument("--dry-run", action="store_true", help="只解析、校验并检查映射")
    parser.add_argument("--report", type=Path, help="将 JSON 报告写入此路径")
    parser.add_argument("--schema-manifest", type=Path, help="旧表 schema manifest，缺省使用 app/legacy_schema_manifest.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.apply and args.dry_run:
        raise SystemExit("--apply 与 --dry-run 不能同时使用")
    try:
        report = asyncio.run(run(args.bundle, apply=args.apply, report_path=args.report, schema_manifest=args.schema_manifest))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps({"ok": True, **report}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()

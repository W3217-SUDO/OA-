"""将本地 SQL Server 沪知快照迁入隔离的新版 OA PostgreSQL 库。"""

from __future__ import annotations

import argparse
import base64
import json
import os
from collections import Counter
from datetime import date, datetime
from decimal import Decimal

import pyodbc
import psycopg
from psycopg.types.json import Jsonb
from hz_field_maps import mapped_data


SOURCE = "hz_crm_20260930"
TABLES = (
    "CRM_Customer",
    "CRM_Customer_Contacts",
    "FCM_Contract",
    "Legal_Case",
    "Legal_Investigation",
    "Legal_Investigation_Task",
    "Legal_Investigation_Clue",
    "Legal_Investigation_Clue_Evidence",
    "IPR_Case",
    "IPR_CaseType",
)

SOURCE_COLUMNS = {
    "CRM_Customer": {"CustomerId", "CustomerNo", "CustomerName", "CustomerType", "IsActived"},
    "CRM_Customer_Contacts": {
        "ContactsId", "CustomerNo", "Contacts", "ContactsTitle", "ProjectRole", "Email", "OfficePhone",
        "Mobilephone", "IM", "IsContacted", "IsPeopleBASE", "IsReceivedEmail", "IsDefault", "IsActived",
    },
    "FCM_Contract": {"ContractId", "ContractNo", "ContractName", "CustomerNo"},
    "Legal_Case": {"CaseId", "CaseNo", "CaseName", "CustomerNo", "ContractNo"},
    "Legal_Investigation": {"InvestigationId", "InvestigationNo", "ContractNo"},
    "Legal_Investigation_Task": {"TaskId", "TaskNo", "InvestigationNo"},
    "Legal_Investigation_Clue": {"ClueId", "ClueNo", "ClueGuid", "InvestigationTaskNo", "InvestigationNo"},
    "Legal_Investigation_Clue_Evidence": {"EvidenceId", "ClueGuid"},
    "IPR_Case": {"CaseId", "CaseNo", "CustomerId", "ContractId", "CaseTypeId"},
    "IPR_CaseType": {"CaseTypeId", "CaseTypeName"},
}

TARGET_COLUMNS = {
    "business_records": {"id", "module", "serial_no", "title", "customer", "status", "owner", "department", "description", "data", "created_at", "updated_at"},
    "contract_objects": {"contract_record_id", "case_record_id", "fee_type", "amount", "remark", "created_by", "updated_by"},
    "investigation_historical_references": {"id", "entity_type", "legacy_key", "source_table", "reason", "source_snapshot"},
    "investigation_task_links": {"task_record_id", "investigation_record_id", "missing_investigation_reference_id", "legacy_task_id", "legacy_task_no", "legacy_task_guid"},
    "investigation_clue_links": {"clue_record_id", "task_record_id", "investigation_record_id", "legacy_clue_id", "legacy_clue_no", "legacy_clue_guid"},
    "investigation_evidences": {"record_id", "clue_record_id", "missing_clue_reference_id", "legacy_evidence_id", "legacy_evidence_no", "legacy_evidence_guid", "evidence_type", "evidence_date", "status", "source_snapshot"},
    "ipr_case_customers": {"case_record_id", "customer_record_id", "is_primary", "created_by"},
}


def check_source_schema(dsn: str) -> None:
    with pyodbc.connect(dsn, timeout=10) as source:
        for name, required in SOURCE_COLUMNS.items():
            cursor = source.execute(f"SELECT TOP (0) * FROM [{name}]")
            actual = {column[0] for column in cursor.description}
            missing = required - actual
            if missing:
                raise ValueError(f"SQL Server 源表 {name} 缺少字段: {', '.join(sorted(missing))}")


def check_target_schema(pg) -> None:
    for name, required in TARGET_COLUMNS.items():
        actual = {
            row[0] for row in pg.execute(
                "SELECT attname FROM pg_attribute "
                "WHERE attrelid = to_regclass(%s) AND attnum > 0 AND NOT attisdropped",
                (name,),
            )
        }
        missing = required - actual
        if missing:
            raise ValueError(f"PostgreSQL 目标表 {name} 缺少字段: {', '.join(sorted(missing))}")


def json_value(value):
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, str) and "\x00" in value:
        raise ValueError("源数据包含 PostgreSQL 不支持的 NUL 字符")
    return value


def read_tables(dsn: str) -> dict[str, list[dict]]:
    result = {}
    with pyodbc.connect(dsn, timeout=10) as source:
        for name in TABLES:
            cursor = source.execute(f"SELECT * FROM [{name}]")
            fields = [column[0] for column in cursor.description]
            missing = SOURCE_COLUMNS[name] - set(fields)
            if missing:
                raise ValueError(f"SQL Server 源表 {name} 缺少字段: {', '.join(sorted(missing))}")
            result[name] = [dict(zip(fields, row)) for row in cursor]
    return result


def token(value) -> str:
    return str(value or "").strip()


def index_by(rows: list[dict], key: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        identifier = token(row.get(key))
        if not identifier or identifier in result:
            raise ValueError(f"{key} 为空或重复: {identifier!r}")
        result[identifier] = row
    return result


def flag(value, default=True) -> bool:
    text_value = token(value).upper()
    return default if not text_value else text_value in {"Y", "T", "1", "TRUE"}


def customer_contacts(rows: list[dict]) -> list[dict]:
    """旧联系人表转为客户记录 data.contacts，字段与 legacy_sync 的反向投影一致。"""
    return [
        {
            "id": f"legacy-{row['ContactsId']}", "name": token(row.get("Contacts")),
            "position": token(row.get("ContactsTitle")), "project_role": token(row.get("ProjectRole")),
            "email": token(row.get("Email")), "office_phone": token(row.get("OfficePhone")),
            "phone": token(row.get("Mobilephone")), "im_account": token(row.get("IM")),
            "is_contacted": flag(row.get("IsContacted")), "is_people_base": flag(row.get("IsPeopleBASE")),
            "is_received_email": flag(row.get("IsReceivedEmail")), "is_primary": flag(row.get("IsDefault"), False),
            "is_valid": flag(row.get("IsActived")),
        }
        for row in sorted(rows, key=lambda item: item["ContactsId"])
    ]


CUSTOMER_TYPES = ("客户", "当事人")


def refresh_customer(pg, record_id: int, row: dict, contacts: list[dict], status: str, report: Counter) -> None:
    """补齐早先导入的客户：旧数字类型、缺失联系人、应回收状态；已被页面改过的值不覆盖。"""
    current_status, data = pg.execute("SELECT status, data FROM business_records WHERE id = %s", (record_id,)).fetchone()
    data = dict(data or {})
    wanted = mapped_data("customer", row)
    changed = False
    if data.get("customer_type") not in CUSTOMER_TYPES:
        data["customer_type"] = wanted["customer_type"]
        data["legacy_customer_type"] = wanted["legacy_customer_type"]
        changed = True
    if not data.get("contacts") and contacts:
        data["contacts"] = contacts
        changed = True
    new_status = status if current_status == "历史数据" and status == "已回收" else current_status
    if changed or new_status != current_status:
        pg.execute("UPDATE business_records SET data = %s, status = %s WHERE id = %s", (Jsonb(data), new_status, record_id))
        report["customer_backfilled"] += 1


def record_data(module: str, row: dict, **relations) -> dict:
    return {
        "migration_source": SOURCE,
        "legacy_record": json_value(row),
        **mapped_data(module, row),
        **relations,
    }


def upsert_record(pg, module: str, serial: str, title: str, customer: str, row: dict, relations: dict, report: Counter, status: str = "历史数据") -> int:
    if not serial or len(serial) > 64:
        raise ValueError(f"{module} 编号无效: {serial!r}")
    existing = pg.execute(
        "SELECT id, module, data FROM business_records WHERE serial_no = %s", (serial,)
    ).fetchone()
    source_id = token(row.get("CustomerId") or row.get("ContractId") or row.get("CaseId") or row.get("InvestigationId") or row.get("TaskId") or row.get("ClueId") or row.get("EvidenceId"))
    if existing:
        previous = existing[2] or {}
        previous_row = previous.get("legacy_record") or {}
        previous_id = token(previous_row.get("CustomerId") or previous_row.get("ContractId") or previous_row.get("CaseId") or previous_row.get("InvestigationId") or previous_row.get("TaskId") or previous_row.get("ClueId") or previous_row.get("EvidenceId"))
        if existing[1] != module or previous.get("migration_source") != SOURCE or previous_id != source_id:
            raise ValueError(f"目标编号已被其他数据占用: {serial}")
        report[f"{module}_existing"] += 1
        return existing[0]
    payload = record_data(module, row, **relations)
    created_at = row.get("CreateTime") or datetime.now()
    updated_at = row.get("ChangeTime") or created_at
    record_id = pg.execute(
        """INSERT INTO business_records
           (module, serial_no, title, customer, status, owner, department,
            description, data, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, 'admin', '沪知', '', %s, %s, %s)
           RETURNING id""",
        (module, serial, (title or serial)[:255], customer[:255], status, Jsonb(payload), created_at, updated_at),
    ).fetchone()[0]
    report[f"{module}_created"] += 1
    return record_id


def historical_reference(pg, entity_type: str, key: str, row: dict) -> int:
    return pg.execute(
        """INSERT INTO investigation_historical_references
           (entity_type, legacy_key, source_table, reason, source_snapshot)
           VALUES (%s, %s, %s, '源快照中找不到父记录', %s)
           ON CONFLICT (entity_type, legacy_key) DO UPDATE
           SET source_snapshot = EXCLUDED.source_snapshot
           RETURNING id""",
        (entity_type, key[:128], SOURCE, Jsonb(json_value(row))),
    ).fetchone()[0]


def import_data(pg, tables: dict[str, list[dict]]) -> Counter:
    report = Counter()
    customers = index_by(tables["CRM_Customer"], "CustomerNo")
    contacts_by_customer: dict[str, list[dict]] = {}
    for contact in tables["CRM_Customer_Contacts"]:
        contacts_by_customer.setdefault(token(contact.get("CustomerNo")), []).append(contact)
    report["customer_contact_unresolved"] = sum(len(rows) for no, rows in contacts_by_customer.items() if no not in customers)
    contracts = index_by(tables["FCM_Contract"], "ContractNo")
    investigations = index_by(tables["Legal_Investigation"], "InvestigationNo")
    tasks = index_by(tables["Legal_Investigation_Task"], "TaskNo")
    clues = index_by(tables["Legal_Investigation_Clue"], "ClueNo")
    types = {row["CaseTypeId"]: token(row["CaseTypeName"]) for row in tables["IPR_CaseType"]}
    customers_by_id = {token(row["CustomerId"]): row for row in customers.values()}
    contracts_by_id = {token(row["ContractId"]): row for row in contracts.values()}
    clue_by_guid = {token(row["ClueGuid"]): row for row in clues.values()}
    ids: dict[str, dict[str, int]] = {name: {} for name in ("customer", "contract", "case", "investigation", "task", "clue", "ipr_case")}

    for no, row in customers.items():
        contacts = customer_contacts(contacts_by_customer.get(no, []))
        status = "历史数据" if flag(row.get("IsActived")) else "已回收"
        existing_before = report["customer_existing"]
        ids["customer"][no] = upsert_record(pg, "customer", no, token(row.get("CustomerName")), "", row, {"customer_no": no, "legacy_customer_id": row["CustomerId"], "contacts": contacts}, report, status)
        if report["customer_existing"] > existing_before:
            refresh_customer(pg, ids["customer"][no], row, contacts, status, report)

    for no, row in contracts.items():
        customer_no = token(row.get("CustomerNo"))
        parent = customers.get(customer_no)
        if not parent:
            raise ValueError(f"合同缺少客户: {no} -> {customer_no}")
        customer_id = ids["customer"][customer_no]
        ids["contract"][no] = upsert_record(pg, "contract", no, token(row.get("ContractName")), token(parent.get("CustomerName")), row, {"customer_id": customer_id, "customer_record_id": customer_id, "customer_no": customer_no, "contract_no": no, "legacy_contract_id": row["ContractId"]}, report)

    for row in tables["Legal_Case"]:
        no = token(row.get("CaseNo"))
        customer_no = token(row.get("CustomerNo"))
        contract_no = token(row.get("ContractNo"))
        if customer_no not in customers or contract_no not in contracts:
            report["case_unresolved"] += 1
            continue
        if token(contracts[contract_no].get("CustomerNo")) != customer_no:
            raise ValueError(f"案件客户与合同不一致: {no}")
        customer_id = ids["customer"][customer_no]
        contract_id = ids["contract"][contract_no]
        case_id = upsert_record(pg, "case", no, token(row.get("CaseName")), token(customers[customer_no].get("CustomerName")), row, {"customer_id": customer_id, "customer_record_id": customer_id, "customer_no": customer_no, "contract_id": contract_id, "contract_record_id": contract_id, "contract_no": contract_no, "case_type_id": row.get("CaseTypeId"), "case_phase_id": row.get("CasePhaseId"), "legacy_case_id": row["CaseId"]}, report)
        ids["case"][no] = case_id
        pg.execute(
            """INSERT INTO contract_objects
               (contract_record_id, case_record_id, fee_type, amount, remark, created_by, updated_by)
               SELECT %s, %s, '', 0, '沪知历史案件关联', 'legacy-import', 'legacy-import'
               WHERE NOT EXISTS (SELECT 1 FROM contract_objects WHERE contract_record_id = %s AND case_record_id = %s)""",
            (contract_id, case_id, contract_id, case_id),
        )

    for no, row in investigations.items():
        contract_no = token(row.get("ContractNo"))
        if contract_no not in ids["contract"]:
            raise ValueError(f"调查缺少合同: {no} -> {contract_no}")
        contract = contracts[contract_no]
        customer_no = token(contract.get("CustomerNo"))
        customer_id = ids["customer"][customer_no]
        ids["investigation"][no] = upsert_record(pg, "investigation", no, token(row.get("InvestigationTitle") or row.get("IndicterName")), token(customers[customer_no].get("CustomerName")), row, {"contract_id": ids["contract"][contract_no], "contract_record_id": ids["contract"][contract_no], "contract_no": contract_no, "customer_id": customer_id, "customer_record_id": customer_id, "customer_no": customer_no, "legacy_investigation_id": row["InvestigationId"]}, report)

    for no, row in tasks.items():
        investigation_no = token(row.get("InvestigationNo"))
        parent = investigations.get(investigation_no)
        investigation_id = ids["investigation"].get(investigation_no)
        customer_no = token(contracts[token(parent["ContractNo"])]["CustomerNo"]) if parent else ""
        relations = {"investigation_no": investigation_no, "legacy_task_id": row["TaskId"]}
        if investigation_id:
            relations.update({"investigation_id": investigation_id, "investigation_record_id": investigation_id, "customer_no": customer_no})
        else:
            report["task_historical_parent"] += 1
        task_id = upsert_record(pg, "task", no, token(row.get("TaskName")), token(customers[customer_no].get("CustomerName")) if customer_no else "", row, relations, report)
        ids["task"][no] = task_id
        missing_id = None if investigation_id else historical_reference(pg, "investigation", investigation_no, row)
        pg.execute(
            """INSERT INTO investigation_task_links
               (task_record_id, investigation_record_id, missing_investigation_reference_id,
                legacy_task_id, legacy_task_no, legacy_task_guid)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (task_record_id) DO NOTHING""",
            (task_id, investigation_id, missing_id, row["TaskId"], no, token(row.get("TaskGuid"))),
        )

    for no, row in clues.items():
        task_no = token(row.get("InvestigationTaskNo"))
        investigation_no = token(row.get("InvestigationNo"))
        task_id = ids["task"].get(task_no)
        investigation_id = ids["investigation"].get(investigation_no)
        if not task_id or not investigation_id:
            raise ValueError(f"线索缺少真实任务/调查: {no}")
        investigation = investigations[investigation_no]
        contract = contracts[token(investigation["ContractNo"])]
        customer_no = token(contract["CustomerNo"])
        clue_id = upsert_record(pg, "clue", no, token(row.get("StoreName") or row.get("Indictee")), token(customers[customer_no].get("CustomerName")), row, {"source_task_id": task_id, "source_task_record_id": task_id, "source_task_no": task_no, "investigation_id": investigation_id, "investigation_record_id": investigation_id, "investigation_no": investigation_no, "customer_no": customer_no, "contract_no": token(investigation["ContractNo"]), "legacy_clue_id": row["ClueId"]}, report)
        ids["clue"][no] = clue_id
        pg.execute(
            """INSERT INTO investigation_clue_links
               (clue_record_id, task_record_id, investigation_record_id, legacy_clue_id,
                legacy_clue_no, legacy_clue_guid)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (clue_record_id) DO NOTHING""",
            (clue_id, task_id, investigation_id, row["ClueId"], no, token(row.get("ClueGuid"))),
        )

    for row in tables["Legal_Investigation_Clue_Evidence"]:
        legacy_id = row["EvidenceId"]
        no = f"HZ-EV-{legacy_id}"
        clue_guid = token(row.get("ClueGuid"))
        parent = clue_by_guid.get(clue_guid)
        clue_id = ids["clue"].get(token(parent.get("ClueNo"))) if parent else None
        relations = {"legacy_evidence_id": legacy_id, "legacy_evidence_no": token(row.get("EvidenceNo")), "clue_guid": clue_guid}
        if clue_id:
            relations.update({"clue_id": clue_id, "clue_record_id": clue_id, "clue_no": token(parent["ClueNo"])})
        else:
            report["evidence_historical_parent"] += 1
        evidence_record_id = upsert_record(pg, "evidence", no, token(row.get("EvidenceNo")) or no, "", row, relations, report)
        missing_id = None if clue_id else historical_reference(pg, "clue", clue_guid, row)
        pg.execute(
            """INSERT INTO investigation_evidences
               (record_id, clue_record_id, missing_clue_reference_id, legacy_evidence_id,
                legacy_evidence_no, legacy_evidence_guid, evidence_type, evidence_date,
                status, source_snapshot)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '历史数据', %s)
               ON CONFLICT (record_id) DO NOTHING""",
            (evidence_record_id, clue_id, missing_id, legacy_id, token(row.get("EvidenceNo")), token(row.get("EvidenceGuid")), token(row.get("EvidenceType"))[:32], row.get("EvidenceDate"), Jsonb(json_value(row))),
        )

    for row in tables["IPR_Case"]:
        no = token(row.get("CaseNo"))
        customer_row = customers_by_id.get(token(row.get("CustomerId")))
        customer_no = token(customer_row.get("CustomerNo")) if customer_row else ""
        contract_row = contracts_by_id.get(token(row.get("ContractId")))
        contract_no = token(contract_row.get("ContractNo")) if contract_row else ""
        type_name = types.get(row.get("CaseTypeId"), "")
        kind = "商标" if "商标" in type_name else "专利" if any(word in type_name for word in ("专利", "PCT", "实用新型", "外观设计")) else type_name
        if not customer_row:
            report["ipr_case_unresolved_customer"] += 1
        customer_name = token(customer_row.get("CustomerName")) if customer_row else token(row.get("ApplicantName"))
        relations = {"legacy_ipr_case_id": row["CaseId"], "customer_no": customer_no, "contract_no": contract_no, "case_kind": kind, "case_type_id": row.get("CaseTypeId"), "case_type_name": type_name, "application_no": token(row.get("CaseRequestNo")), "applicant": token(row.get("ApplicantName")), "case_phase_id": row.get("CasePhaseId"), "deadline": json_value(row.get("Deadline")), "case_inventor": token(row.get("CaseInventor"))}
        if customer_row:
            relations.update({"customer_id": ids["customer"][customer_no], "customer_record_id": ids["customer"][customer_no]})
        if contract_row:
            relations.update({"contract_id": ids["contract"][contract_no], "contract_record_id": ids["contract"][contract_no]})
        case_id = upsert_record(pg, "ipr_case", no, token(row.get("CaseName")), customer_name, row, relations, report)
        ids["ipr_case"][no] = case_id
        if customer_row:
            pg.execute(
                """INSERT INTO ipr_case_customers
                   (case_record_id, customer_record_id, is_primary, created_by)
                   VALUES (%s, %s, true, 'legacy-import')
                   ON CONFLICT (case_record_id, customer_record_id) DO NOTHING""",
                (case_id, ids["customer"][customer_no]),
            )
        if contract_row:
            pg.execute(
                """INSERT INTO contract_objects
                   (contract_record_id, case_record_id, fee_type, amount, remark, created_by, updated_by)
                   SELECT %s, %s, '', 0, '沪知历史知识产权案件关联', 'legacy-import', 'legacy-import'
                   WHERE NOT EXISTS (SELECT 1 FROM contract_objects WHERE contract_record_id = %s AND case_record_id = %s)""",
                (ids["contract"][contract_no], case_id, ids["contract"][contract_no], case_id),
            )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check-schema", action="store_true")
    args = parser.parse_args()
    sql_dsn = os.environ["HZ_SQLSERVER_DSN"]
    pg_dsn = os.environ["HZ_POSTGRES_DSN"]
    with psycopg.connect(pg_dsn, autocommit=False) as pg:
        check_target_schema(pg)
        check_source_schema(sql_dsn)
        if args.check_schema:
            print(json.dumps({"schema": "ok", "applied": False}, ensure_ascii=False))
            return
        tables = read_tables(sql_dsn)
        report = import_data(pg, tables)
        if args.apply:
            pg.commit()
        else:
            pg.rollback()
        print(json.dumps({"applied": args.apply, "source_counts": {name: len(rows) for name, rows in tables.items()}, "result": dict(report)}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

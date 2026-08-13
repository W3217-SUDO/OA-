"""Import the 8091 local legacy sample bundle into the local FastAPI database.

The legacy SQL Server is never opened or changed by this tool.  It reads the
three exported DataSet packages and writes an idempotent projection into the
current local SQLite database used by the 5173 application.
"""

import argparse
import asyncio
import base64
import gzip
import json
import secrets
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

# Support direct execution from the API project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.models import (
    BusinessRecord,
    FileAttachment,
    LegacyCase,
    LegacyCaseFile,
    LegacyCaseLog,
    LegacyCaseParticipant,
    LegacyContract,
    LegacyCustomer,
    LegacyCustomerContact,
    LegacyInvestigation,
    LegacyInvestigationClue,
    LegacyInvestigationTask,
    User,
)
from app.security import hash_password


SOURCE = "8091-local-PRD_CRM_GD_20200211"
DEFAULT_OWNER = "admin"
CASE_TYPES = {110: "民事案件", 120: "刑事案件", 130: "行政案件", 140: "法律顾问案件", 150: "仲裁案件"}


def clean(value, limit=None):
    text = " ".join(str(value or "").split()).strip()
    return text[:limit] if limit else text


def parse_datetime(value):
    text = clean(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def decode_dataset(path):
    payload = Path(path).read_bytes()
    encoding = "utf-16" if payload.startswith((b"\xff\xfe", b"\xfe\xff")) else "ascii"
    raw = base64.b64decode(payload.decode(encoding).strip())
    root = ET.fromstring(gzip.decompress(raw))
    rows = {}
    for child in root:
        # The DataSet schema has a namespace; data rows do not.
        if child.tag.startswith("{"):
            continue
        row = {field.tag.rsplit("}", 1)[-1]: field.text or "" for field in child}
        rows.setdefault(child.tag, []).append(row)
    return rows


def legacy_values(model, row):
    values = {}
    date_columns = {column.name for column in model.__table__.columns if "DATETIME" in str(column.type).upper()}
    integer_columns = {column.name for column in model.__table__.columns if "INT" in str(column.type).upper()}
    numeric_columns = {column.name for column in model.__table__.columns if any(word in str(column.type).upper() for word in ("NUMERIC", "FLOAT", "REAL"))}
    for column in model.__table__.columns:
        if column.name not in row or row[column.name] == "":
            continue
        value = row[column.name]
        if column.name in date_columns:
            value = parse_datetime(value)
        elif column.name in integer_columns:
            try:
                value = int(float(value))
            except ValueError:
                continue
        elif column.name in numeric_columns:
            try:
                value = float(value)
            except ValueError:
                continue
        values[column.name] = value
    return values


async def upsert_legacy(db, model, key, rows):
    created = updated = 0
    for row in rows:
        marker = clean(row.get(key))
        if not marker:
            continue
        item = await db.scalar(select(model).where(getattr(model, key) == marker))
        values = legacy_values(model, row)
        if item is None:
            item = model(**values)
            db.add(item)
            created += 1
        else:
            for name, value in values.items():
                setattr(item, name, value)
            updated += 1
    await db.flush()
    return {"created": created, "updated": updated}


async def upsert_legacy_case_participants(db, rows):
    """The legacy participant table uses CaseNo + StaffName as its key."""
    created = updated = 0
    for row in rows:
        case_no = clean(row.get("CaseNo"), 20)
        staff_name = clean(row.get("StaffName"), 20)
        if not case_no or not staff_name:
            continue
        item = await db.get(LegacyCaseParticipant, {"CaseNo": case_no, "StaffName": staff_name})
        values = legacy_values(LegacyCaseParticipant, row)
        if item is None:
            db.add(LegacyCaseParticipant(**values))
            created += 1
        else:
            for name, value in values.items():
                setattr(item, name, value)
            updated += 1
    await db.flush()
    return {"created": created, "updated": updated}


def owner_for(users, token):
    wanted = clean(token).casefold()
    for user in users:
        if user.username.casefold() == wanted or clean(user.display_name).casefold() == wanted:
            return user.username
    return next((user.username for user in users if user.username == DEFAULT_OWNER), users[0].username)


async def upsert_sample_staff(db, rows):
    """Make legacy account references resolvable without importing old passwords."""
    created = updated = 0
    for row in rows:
        username = clean(row.get("StaffName")).lower()
        display_name = clean(row.get("StaffChName"), 64)
        if not username or not display_name:
            continue
        user = await db.scalar(select(User).where(User.username == username))
        if user is None:
            # A random one-time hash prevents accidental reuse of legacy
            # credentials. An administrator sets each real login password.
            user = User(
                username=username,
                display_name=display_name,
                department=clean(row.get("DepartmentName"), 64) or "上海分所",
                role="user",
                role_ids=["user"],
                profile={
                    "migration_source": SOURCE,
                    "legacy_staff_no": clean(row.get("StaffNo")),
                    "legacy_department_id": clean(row.get("DepartmentId")),
                },
                password_hash=hash_password(secrets.token_urlsafe(32)),
                is_active=clean(row.get("IsActived")) in {"", "Y", "1", "T"},
                must_change_password=True,
            )
            db.add(user)
            created += 1
            continue
        profile = dict(user.profile or {})
        if profile.get("migration_source") == SOURCE:
            profile.update({
                "legacy_staff_no": clean(row.get("StaffNo")),
                "legacy_department_id": clean(row.get("DepartmentId")),
            })
            user.profile = profile
            user.display_name = display_name
            if not clean(user.department):
                user.department = clean(row.get("DepartmentName"), 64) or "上海分所"
            updated += 1
    await db.flush()
    return {"created": created, "updated": updated}


async def upsert_record(db, index, *, module, serial_no, title, customer="", owner=DEFAULT_OWNER, department="", status="历史数据", description="", data=None, created_at=None, updated_at=None):
    item = index.get(serial_no)
    if item:
        # Imported records are projections of a fixed 8091 sample bundle.  A
        # rerun must refresh missing projection keys from an earlier importer.
        item_data = dict(item.data or {})
        item_data.update(data or {})
        item.title = title or item.title
        item.customer = customer or item.customer
        item.owner = owner or item.owner
        item.department = department or item.department
        item.status = status or item.status
        item.description = description or item.description
        item.data = item_data
        item.updated_at = updated_at or item.updated_at
        return item, False
    item = BusinessRecord(
        module=module, serial_no=serial_no, title=title or serial_no, customer=customer,
        owner=owner, department=department, status=status, description=description,
        data=data or {}, created_at=created_at, updated_at=updated_at or created_at,
    )
    db.add(item)
    await db.flush()
    index[serial_no] = item
    return item, True


async def run(bundle_dir, dry_run):
    bundle_dir = Path(bundle_dir)
    main = decode_dataset(bundle_dir / "SH_latest50_dataset.xml.gz.b64")
    deps = decode_dataset(bundle_dir / "SH_latest50_dependencies.xml.gz.b64")
    inv = decode_dataset(bundle_dir / "SH_latest50_investigation_dependencies.xml.gz.b64")
    expected = {"cases": len(main.get("Legal_Case", [])), "customers": len(deps.get("CRM_Customer", [])), "contracts": len(deps.get("FCM_Contract", [])), "investigations": len(inv.get("Legal_Investigation", [])), "tasks": len(inv.get("Legal_Investigation_Task", [])), "clues": len(main.get("Legal_Investigation_Clue", []))}
    if expected["cases"] != 50:
        raise RuntimeError(f"Expected 50 legacy cases, found {expected['cases']}")
    # Importers may run against a database created before new compatibility
    # projections were added. Register all current models before opening a
    # session so the historical relation tables are available.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        result = {"source": SOURCE, "expected": expected, "legacy": {}, "records": {}}
        if dry_run:
            records = list((await db.scalars(select(BusinessRecord))).all())
            index = {record.serial_no: record for record in records}
            result["existing_records"] = {name: sum(1 for key in index if key in {clean(row.get(field)) for row in rows}) for name, field, rows in (("cases", "CaseNo", main.get("Legal_Case", [])), ("customers", "CustomerNo", deps.get("CRM_Customer", [])), ("contracts", "ContractNo", deps.get("FCM_Contract", [])), ("investigations", "InvestigationNo", inv.get("Legal_Investigation", [])), ("tasks", "TaskNo", inv.get("Legal_Investigation_Task", [])), ("clues", "ClueNo", main.get("Legal_Investigation_Clue", [])))}
            print(json.dumps(result, ensure_ascii=False))
            return
        result["staff"] = await upsert_sample_staff(db, inv.get("HR_Staff", []))
        users = list((await db.scalars(select(User).where(User.is_active.is_(True)))).all())
        if not users:
            raise RuntimeError("No active target users exist")
        records = list((await db.scalars(select(BusinessRecord))).all())
        index = {record.serial_no: record for record in records}
        result["legacy"]["customers"] = await upsert_legacy(db, LegacyCustomer, "CustomerNo", deps.get("CRM_Customer", []))
        result["legacy"]["contacts"] = await upsert_legacy(db, LegacyCustomerContact, "ContactsId", deps.get("CRM_Customer_Contacts", []))
        result["legacy"]["contracts"] = await upsert_legacy(db, LegacyContract, "ContractNo", deps.get("FCM_Contract", []))
        result["legacy"]["cases"] = await upsert_legacy(db, LegacyCase, "CaseNo", main.get("Legal_Case", []))
        result["legacy"]["case_files"] = await upsert_legacy(db, LegacyCaseFile, "FileId", main.get("Legal_Case_File", []))
        result["legacy"]["case_participants"] = await upsert_legacy_case_participants(db, main.get("Legal_Case_Participant", []))
        result["legacy"]["case_logs"] = await upsert_legacy(db, LegacyCaseLog, "LogId", main.get("Legal_Case_Log", []))
        result["legacy"]["investigations"] = await upsert_legacy(db, LegacyInvestigation, "InvestigationNo", inv.get("Legal_Investigation", []))
        result["legacy"]["tasks"] = await upsert_legacy(db, LegacyInvestigationTask, "TaskNo", inv.get("Legal_Investigation_Task", []))
        result["legacy"]["clues"] = await upsert_legacy(db, LegacyInvestigationClue, "ClueNo", main.get("Legal_Investigation_Clue", []))
        customers = {}
        for row in deps.get("CRM_Customer", []):
            serial = clean(row.get("CustomerNo"))
            if not serial:
                continue
            item, made = await upsert_record(db, index, module="customer", serial_no=serial, title=clean(row.get("CustomerName"), 255), owner=owner_for(users, row.get("BusinessOwner")), status="正常", description="8091旧系统样本客户", data={"migration_source": SOURCE, "legacy_customer_id": row.get("CustomerId"), "legacy_record": row, "customer_no": serial}, created_at=parse_datetime(row.get("CreateTime")), updated_at=parse_datetime(row.get("ChangeTime")))
            customers[serial] = item
            result["records"].setdefault("customers", 0); result["records"]["customers"] += int(made)
        contracts = {}
        for row in deps.get("FCM_Contract", []):
            serial = clean(row.get("ContractNo"))
            if not serial:
                continue
            customer_no = clean(row.get("CustomerNo")); customer = customers.get(customer_no)
            item, made = await upsert_record(db, index, module="contract", serial_no=serial, title=clean(row.get("ContractName"), 255), customer=customer.title if customer else customer_no, owner=owner_for(users, row.get("BusinessOwner") or row.get("CreateUser")), status="历史数据", description="8091旧系统样本合同", data={"migration_source": SOURCE, "legacy_contract_id": row.get("ContractId"), "legacy_record": row, "customer_id": customer.id if customer else None, "customer_no": customer_no, "contract_no": serial}, created_at=parse_datetime(row.get("CreateTime")), updated_at=parse_datetime(row.get("ChangeTime")))
            contracts[serial] = item
            result["records"].setdefault("contracts", 0); result["records"]["contracts"] += int(made)
        investigations = {}
        for row in inv.get("Legal_Investigation", []):
            serial = clean(row.get("InvestigationNo"))
            if not serial:
                continue
            contract_no = clean(row.get("ContractNo")); contract = contracts.get(contract_no)
            scope = clean(row.get("InvestigationScope"))
            item, made = await upsert_record(db, index, module="investigation", serial_no=serial, title=clean(row.get("InvestigationTitle") or row.get("IndicterName"), 255), customer=contract.customer if contract else clean(row.get("IndicterName"), 255), owner=owner_for(users, row.get("BusinessOwner")), status="历史数据", description=clean(row.get("Remark")), data={"migration_source": SOURCE, "legacy_investigation_id": row.get("InvestigationId"), "legacy_record": row, "contract_id": contract.id if contract else None, "contract_no": contract_no, "case_type_id": row.get("CaseTypeId"), "case_type": "商标" if str(row.get("CaseTypeId") or "").startswith("110") else "", "authorization_scope": "全国" if scope in {"Y", "1", "T"} else "区域", "province": clean(row.get("Province")), "city": clean(row.get("City")), "authorized_from": row.get("AuthorizationBeginTime"), "authorized_to": row.get("AuthorizationEndTime"), "customer_review": scope in {"Y", "1", "T"} and clean(row.get("NeedToAuditOnCustomer")) in {"Y", "1", "T"}, "source_owner": clean(row.get("BusinessOwner") or row.get("CreateUser")), "publisher": clean(row.get("CreateUser")), "auditor": clean(row.get("Auditor"))}, created_at=parse_datetime(row.get("CreateTime")), updated_at=parse_datetime(row.get("ChangeTime")))
            investigations[serial] = item
            result["records"].setdefault("investigations", 0); result["records"]["investigations"] += int(made)
        tasks = {}
        for row in inv.get("Legal_Investigation_Task", []):
            serial = clean(row.get("TaskNo"))
            if not serial:
                continue
            parent_no = clean(row.get("InvestigationNo")); parent = investigations.get(parent_no)
            item, made = await upsert_record(db, index, module="task", serial_no=serial, title=clean(row.get("TaskName"), 255), customer=parent.customer if parent else "", owner=owner_for(users, row.get("Investigator") or row.get("CreateUser")), status="历史数据", description=clean(row.get("Remark")), data={"migration_source": SOURCE, "legacy_task_id": row.get("TaskId"), "legacy_record": row, "investigation_record_id": parent.id if parent else None, "investigation_no": parent_no, "authorization_scope": "全国" if clean(row.get("InvestigationScope")) in {"Y", "1", "T"} else "区域", "province": clean(row.get("Province")), "city": clean(row.get("City")), "district": clean(row.get("District")), "authorized_from": row.get("BeginTime"), "authorized_to": row.get("EndTime"), "start_date": row.get("BeginTime"), "deadline": row.get("EndTime"), "source_owner": clean(row.get("CreateUser")), "publisher": clean(row.get("CreateUser"))}, created_at=parse_datetime(row.get("CreateTime")), updated_at=parse_datetime(row.get("ChangeTime")))
            tasks[serial] = item
            result["records"].setdefault("tasks", 0); result["records"]["tasks"] += int(made)
        for row in main.get("Legal_Case", []):
            serial = clean(row.get("CaseNo"))
            if not serial:
                continue
            customer_no = clean(row.get("CustomerNo")); contract_no = clean(row.get("ContractNo")); customer = customers.get(customer_no); contract = contracts.get(contract_no)
            item, made = await upsert_record(db, index, module="case", serial_no=serial, title=clean(row.get("CaseName"), 255), customer=customer.title if customer else customer_no, owner=owner_for(users, row.get("BusinessOwner") or row.get("CreateUser")), department="历史案件", status="历史数据", description="8091旧系统样本案件", data={"migration_source": SOURCE, "legacy_case_id": row.get("CaseId"), "legacy_record": row, "customer_id": customer.id if customer else None, "customer_no": customer_no, "contract_id": contract.id if contract else None, "contract_no": contract_no, "case_type_id": row.get("CaseTypeId"), "case_type": CASE_TYPES.get(int(row.get("CaseTypeId") or 0), "案件"), "cause_or_charge": clean(row.get("CauseName")), "business_owner": clean(row.get("BusinessOwner")), "plaintiff": clean(row.get("AppellantNames")), "defendant": clean(row.get("AppelleeNames")), "court": clean(row.get("FirstIntanceCourt")), "court_case_no": clean(row.get("FirstIntanceCaseNo")), "investigation_clue_nos": clean(row.get("InvestigationClueNos")), "settlement_amount": row.get("SettlementAmount"), "litigation_amount": row.get("LitigationAmount"), "original_case_no": clean(row.get("OriginalCaseNo"))}, created_at=parse_datetime(row.get("CreateTime")), updated_at=parse_datetime(row.get("ChangeTime")))
            result["records"].setdefault("cases", 0); result["records"]["cases"] += int(made)
        for row in main.get("Legal_Investigation_Clue", []):
            serial = clean(row.get("ClueNo"))
            if not serial:
                continue
            task_no = clean(row.get("InvestigationTaskNo")); investigation_no = clean(row.get("InvestigationNo")); source = tasks.get(task_no) or investigations.get(investigation_no)
            item, made = await upsert_record(db, index, module="clue", serial_no=serial, title=clean(row.get("StoreName") or row.get("Indictee"), 255), customer=source.customer if source else "", owner=owner_for(users, row.get("CreateUser")), status="历史数据", description=clean(row.get("Remark")), data={"migration_source": SOURCE, "legacy_clue_id": row.get("ClueId"), "legacy_record": row, "source_task_id": source.id if source else None, "source_task_no": task_no, "investigation_record_id": investigations.get(investigation_no).id if investigations.get(investigation_no) else None, "investigation_no": investigation_no, "case_no": clean(row.get("CaseNo")), "platform": clean(row.get("PlatformName")), "store_name": clean(row.get("StoreName")), "store_url": clean(row.get("StoreUrl")), "province": clean(row.get("ProvinceZh") or row.get("Province")), "city": clean(row.get("CityZh") or row.get("City")), "district": clean(row.get("DistrictZh") or row.get("District")), "address": clean(row.get("Address") or row.get("LocationAddress")), "investigation_date": row.get("InvestigationDate")}, created_at=parse_datetime(row.get("CreateTime")), updated_at=parse_datetime(row.get("ChangeTime")))
            result["records"].setdefault("clues", 0); result["records"]["clues"] += int(made)
        cases = {clean(row.get("CaseNo")): index.get(clean(row.get("CaseNo"))) for row in main.get("Legal_Case", [])}
        for row in main.get("Legal_Case_File", []):
            case = cases.get(clean(row.get("CaseNo")))
            if not case:
                continue
            name = clean(row.get("FileName"), 255) or f"legacy-file-{row.get('FileId')}"
            stored = f"legacy-{row.get('FileId')}-{name}"[:255]
            exists = await db.scalar(select(FileAttachment).where(FileAttachment.stored_name == stored))
            if not exists:
                db.add(FileAttachment(record_id=case.id, category="旧系统案件文件", file_type_code=clean(row.get("CaseFileTypeId")), original_name=name, stored_name=stored, content_type="application/octet-stream", size=int(float(row.get("FileSize") or 0)), path=clean(row.get("FullPath") or row.get("FilePath"), 512), uploader=owner_for(users, row.get("CreateUser") or row.get("UploadUser")), remark="8091旧系统样本文件元数据", created_at=parse_datetime(row.get("CreateTime"))))
                result["records"].setdefault("files", 0); result["records"]["files"] += 1
        await db.commit()
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle_dir")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.bundle_dir, args.dry_run))

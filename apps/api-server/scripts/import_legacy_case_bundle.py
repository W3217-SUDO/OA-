"""Import one read-only legacy case bundle and restore its parent relations."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import (
    BusinessRecord,
    ContractObject,
    ContractObjectLog,
    LegacyCase,
    LegacyCaseFile,
    LegacyCaseLog,
    LegacyContract,
    LegacyCustomer,
    User,
    WorkflowEvent,
)
from scripts.import_sh_latest50_samples import (
    clean,
    owner_for,
    parse_datetime,
    upsert_legacy,
    upsert_legacy_case_participants,
)


CASE_TYPES = {110: "民事案件", 120: "刑事案件", 130: "行政案件", 140: "法律顾问案件", 150: "仲裁案件"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def run(bundle_path: Path, apply: bool) -> dict:
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    case_row = dict(bundle.get("case") or {})
    contract_rows = list(bundle.get("contract") or [])
    customer_rows = list(bundle.get("customer") or [])
    if not case_row.get("CaseNo") or len(contract_rows) != 1 or len(customer_rows) != 1:
        raise RuntimeError("bundle must contain one case, one contract, and one customer")

    async with SessionLocal() as db:
        users = list((await db.scalars(select(User).where(User.is_active.is_(True)))).all())
        if not users:
            raise RuntimeError("target database has no active users")

        case_no = clean(case_row.get("CaseNo"))
        customer_row = customer_rows[0]
        contract_row = contract_rows[0]
        customer_no = clean(customer_row.get("CustomerNo"))
        contract_no = clean(contract_row.get("ContractNo"))
        customer = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == customer_no))
        contract = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == contract_no))
        case = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == case_no))
        contract_object = None
        if contract and case:
            contract_object = await db.scalar(
                select(ContractObject).where(
                    ContractObject.contract_record_id == contract.id,
                    ContractObject.case_record_id == case.id,
                )
            )
        report = {
            "mode": "apply" if apply else "dry-run",
            "case_no": case_no,
            "customer_exists": bool(customer),
            "contract_created": not bool(contract),
            "case_created": not bool(case),
            "contract_object_created": not bool(contract_object),
            "legacy_files": len(bundle.get("files") or []),
            "legacy_participants": len(bundle.get("participants") or []),
            "legacy_logs": len(bundle.get("logs") or []),
        }
        if not customer:
            raise RuntimeError(f"customer parent is missing: {customer_no}")

        if not apply:
            await db.rollback()
            return report

        await upsert_legacy(db, LegacyCustomer, "CustomerNo", customer_rows)
        await upsert_legacy(db, LegacyContract, "ContractNo", contract_rows)
        await upsert_legacy(db, LegacyCase, "CaseNo", [case_row])
        await upsert_legacy(db, LegacyCaseFile, "FileId", bundle.get("files") or [])
        await upsert_legacy_case_participants(db, bundle.get("participants") or [])
        await upsert_legacy(db, LegacyCaseLog, "LogId", bundle.get("logs") or [])

        contract_owner = owner_for(users, contract_row.get("BusinessOwner") or contract_row.get("CreateUser"))
        contract_owner_user = next(user for user in users if user.username == contract_owner)
        if not contract:
            contract = BusinessRecord(
                module="contract",
                serial_no=contract_no,
                title=clean(contract_row.get("ContractName"), 255) or contract_no,
                customer=customer.title,
                status="历史数据",
                owner=contract_owner,
                department=contract_owner_user.department,
                description="从旧系统只读同步的历史合同",
                data={
                    "migration_source": "legacy_prd_crm",
                    "legacy_contract_id": contract_row.get("ContractId"),
                    "legacy_record": contract_row,
                    "customer_id": customer.id,
                    "customer_no": customer_no,
                    "contract_no": contract_no,
                    "contract_type_id": contract_row.get("ContractType"),
                    "charging_type_id": contract_row.get("ChargingType"),
                    "contract_status_id": contract_row.get("ContractStatus"),
                    "contract_start": contract_row.get("ContractBeginDate"),
                    "contract_end": contract_row.get("ContractEndDate"),
                    "reference_contract_no": clean(contract_row.get("RefContractNo")),
                },
                created_at=parse_datetime(contract_row.get("CreateTime")),
                updated_at=parse_datetime(contract_row.get("ChangeTime") or contract_row.get("CreateTime")),
            )
            db.add(contract)
            await db.flush()
            db.add(WorkflowEvent(record_id=contract.id, action="旧系统合同迁移", from_status="", to_status=contract.status, operator="legacy-migration", comment=f"恢复案件 {case_no} 的合同父记录"))

        case_owner = owner_for(users, case_row.get("BusinessOwner") or case_row.get("CreateUser"))
        case_owner_user = next(user for user in users if user.username == case_owner)
        lawyer_names = [name for name in str(case_row.get("CaseLawyerName") or "").split(",") if name]
        lawyer_usernames = [name for name in str(case_row.get("CaseLawyer") or "").split(",") if name]
        if not case:
            case = BusinessRecord(
                module="case",
                serial_no=case_no,
                title=clean(case_row.get("CaseName"), 255) or case_no,
                customer=customer.title,
                status="待分配",
                owner=case_owner,
                department=case_owner_user.department,
                description="从旧系统只读同步的历史案件",
                data={
                    "migration_source": "legacy_prd_crm",
                    "legacy_case_id": case_row.get("CaseId"),
                    "legacy_record": case_row,
                    "customer_id": customer.id,
                    "customer_no": customer_no,
                    "contract_id": contract.id,
                    "contract_no": contract_no,
                    "contract_title": contract.title,
                    "case_type_id": case_row.get("CaseTypeId"),
                    "case_type": CASE_TYPES.get(int(case_row.get("CaseTypeId") or 0), "案件"),
                    "cause_or_charge": clean(case_row.get("CauseName")),
                    "source_person": clean(case_row.get("CaseOriginPeople")),
                    "source_owner": case_owner,
                    "handling_lawyers": lawyer_names,
                    "handling_lawyer_usernames": lawyer_usernames,
                    "assistant": clean(case_row.get("CaseAssistantName")),
                    "assistant_username": clean(case_row.get("CaseAssistant")),
                    "case_team_usernames": [value for value in dict.fromkeys([*lawyer_usernames, clean(case_row.get("CaseAssistant"))]) if value],
                    "plaintiff": clean(case_row.get("AppellantNames")),
                    "appellant_nos": clean(case_row.get("AppellantNos")),
                    "opponent": clean(case_row.get("AppelleeNames")),
                    "defendant": clean(case_row.get("AppelleeNames")),
                    "appellee_nos": clean(case_row.get("AppelleeNos")),
                    "third_party": clean(case_row.get("TheThirdNames")),
                    "third_party_nos": clean(case_row.get("TheThirdNos")),
                    "third_party_agent": clean(case_row.get("TheThirdAgent")),
                    "court": clean(case_row.get("FirstIntanceCourt")),
                    "court_code": clean(case_row.get("FirstIntanceCourt")),
                    "court_case_no": clean(case_row.get("FirstIntanceCaseNo")),
                    "filing_date": case_row.get("FirstIntanceRegisterDate"),
                    "case_register_date": case_row.get("CaseRegisterDate"),
                    "deadline": case_row.get("Deadline"),
                },
                created_at=parse_datetime(case_row.get("CreateTime")),
                updated_at=parse_datetime(case_row.get("ChangeTime") or case_row.get("CreateTime")),
            )
            db.add(case)
            await db.flush()
            db.add(WorkflowEvent(record_id=case.id, action="旧系统案件迁移", from_status="", to_status=case.status, operator="legacy-migration", comment=f"恢复旧系统案件 {case_no} 及其合同、附件关联"))

        if not contract_object:
            contract_object = ContractObject(
                contract_record_id=contract.id,
                case_record_id=case.id,
                fee_type="历史案件",
                amount=0,
                remark=f"旧系统同步案件 {case_no}",
                created_by="legacy-migration",
                updated_by="legacy-migration",
            )
            db.add(contract_object)
            await db.flush()
            db.add(
                ContractObjectLog(
                    contract_object_id=contract_object.id,
                    action="旧系统合同标的迁移",
                    before={},
                    after={"case_no": case_no, "fee_type": "历史案件", "amount": 0},
                    operator="legacy-migration",
                )
            )

        report["contract_id"] = contract.id
        report["case_id"] = case.id
        report["contract_object_id"] = contract_object.id
        await db.commit()
        return report


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(asyncio.run(run(args.bundle, args.apply)), ensure_ascii=False, indent=2))

"""Recover missing customer and contract parents from retained legacy snapshots.

Dry-run is the default. ``--apply`` commits one atomic transaction. A parent is
created only when its legacy number and name are both present in a child record;
unrecoverable references remain visible in the report instead of being forged.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.main import _sync_legacy_projection
from app.models import (
    BusinessRecord,
    LegacyContract,
    LegacyCustomer,
    LegacyInvestigation,
    LegacyInvestigationTask,
)
from scripts.backfill_legacy_projections import record_identity


RECOVERY_SOURCE = "legacy_relation_recovery"


def text(value: object) -> str:
    return str(value or "").strip()


def snapshot(record: BusinessRecord) -> dict:
    value = (record.data or {}).get("legacy_record")
    return value if isinstance(value, dict) else {}


def first(*values: object) -> str:
    return next((text(value) for value in values if text(value)), "")


def add_spec(specs: dict[str, list[dict]], number: str, name: str, source: BusinessRecord, **extra) -> None:
    if number and name:
        specs[number].append({"name": name, "source": source, **extra})


def one_value(number: str, rows: list[dict], key: str) -> str:
    values = {text(row.get(key)) for row in rows if text(row.get(key))}
    if len(values) > 1:
        raise RuntimeError(f"Conflicting {key} values for {number}: {sorted(values)}")
    return next(iter(values), "")


async def run(apply: bool) -> dict:
    async with SessionLocal() as db:
        records = list((await db.scalars(select(BusinessRecord).order_by(BusinessRecord.id))).all())
        by_no = {record.serial_no: record for record in records}
        by_module = defaultdict(list)
        for record in records:
            by_module[record.module].append(record)
        projection_parent_nos = {
            "customer": set((await db.scalars(select(LegacyCustomer.CustomerNo))).all()),
            "contract": set((await db.scalars(select(LegacyContract.ContractNo))).all()),
            "investigation": set((await db.scalars(select(LegacyInvestigation.InvestigationNo))).all()),
            "task": set((await db.scalars(select(LegacyInvestigationTask.TaskNo))).all()),
        }

        customer_specs: dict[str, list[dict]] = defaultdict(list)
        contract_specs: dict[str, list[dict]] = defaultdict(list)
        for contract in by_module["contract"]:
            data = contract.data or {}
            old = snapshot(contract)
            customer_no = first(data.get("customer_no"), old.get("CustomerNo"), old.get("customer_no"))
            add_spec(
                customer_specs,
                customer_no,
                first(old.get("CustomerName"), old.get("customer_name"), contract.customer),
                contract,
                legacy_id=first(data.get("legacy_customer_id"), old.get("CustomerId"), old.get("legacy_customer_id")),
            )
        for child in [*by_module["case"], *by_module["investigation"]]:
            data = child.data or {}
            old = snapshot(child)
            customer_no = first(data.get("customer_no"), old.get("CustomerNo"), old.get("customer_no"))
            customer_name = first(old.get("CustomerName"), old.get("customer_name"), child.customer)
            add_spec(customer_specs, customer_no, customer_name, child)
            contract_no = first(data.get("contract_no"), old.get("ContractNo"), old.get("contract_no"))
            add_spec(
                contract_specs,
                contract_no,
                first(old.get("ContractName"), old.get("contract_name")),
                child,
                customer_no=customer_no,
                customer_name=customer_name,
            )

        changed: list[BusinessRecord] = []
        created_customers = 0
        for customer_no, rows in sorted(customer_specs.items()):
            customer = by_no.get(customer_no)
            if customer:
                if customer.module != "customer":
                    raise RuntimeError(f"Serial {customer_no} belongs to {customer.module}, not customer")
            else:
                source = rows[0]["source"]
                customer = BusinessRecord(
                    module="customer",
                    serial_no=customer_no,
                    title=one_value(customer_no, rows, "name"),
                    customer=one_value(customer_no, rows, "name"),
                    status="历史数据",
                    owner=source.owner,
                    department=source.department,
                    description="由旧系统子记录快照恢复的关联客户",
                    data={
                        "migration_source": RECOVERY_SOURCE,
                        "customer_no": customer_no,
                        "legacy_customer_id": one_value(customer_no, rows, "legacy_id"),
                        "recovered_from": sorted({row["source"].serial_no for row in rows}),
                    },
                )
                db.add(customer)
                await db.flush()
                by_no[customer_no] = customer
                changed.append(customer)
                created_customers += 1
            for row in rows:
                source = row["source"]
                data = dict(source.data or {})
                if data.get("customer_id") != customer.id or data.get("customer_no") != customer_no:
                    data.update({"customer_id": customer.id, "customer_record_id": customer.id, "customer_no": customer_no})
                    source.data = data
                    changed.append(source)

        created_contracts = 0
        for contract_no, rows in sorted(contract_specs.items()):
            contract = by_no.get(contract_no)
            if contract:
                if contract.module != "contract":
                    raise RuntimeError(f"Serial {contract_no} belongs to {contract.module}, not contract")
            else:
                source = rows[0]["source"]
                customer_no = one_value(contract_no, rows, "customer_no")
                customer = by_no.get(customer_no)
                contract = BusinessRecord(
                    module="contract",
                    serial_no=contract_no,
                    title=one_value(contract_no, rows, "name"),
                    customer=customer.title if customer else one_value(contract_no, rows, "customer_name"),
                    status="历史数据",
                    owner=source.owner,
                    department=source.department,
                    description="由旧系统子记录快照恢复的关联合同",
                    data={
                        "migration_source": RECOVERY_SOURCE,
                        "contract_no": contract_no,
                        "customer_id": customer.id if customer else None,
                        "customer_no": customer_no,
                        "recovered_from": sorted({row["source"].serial_no for row in rows}),
                    },
                )
                db.add(contract)
                await db.flush()
                by_no[contract_no] = contract
                changed.append(contract)
                created_contracts += 1
            for row in rows:
                source = row["source"]
                data = dict(source.data or {})
                if data.get("contract_id") != contract.id or data.get("contract_no") != contract_no:
                    data.update({"contract_id": contract.id, "contract_record_id": contract.id, "contract_no": contract_no})
                    source.data = data
                    changed.append(source)

        unique_changed = {record.id: record for record in changed if record.id}.values()
        for record in unique_changed:
            await _sync_legacy_projection(record, record_identity(record), db)
        await db.flush()

        unresolved = {}
        for module, parent_module, key in (
            ("contract", "customer", "customer_no"),
            ("case", "contract", "contract_no"),
            ("investigation", "contract", "contract_no"),
            ("task", "investigation", "investigation_no"),
            ("clue", "investigation", "investigation_no"),
            ("clue", "task", "investigation_task_no"),
        ):
            parent_nos = {record.serial_no for record in by_module[parent_module]} | {
                record.serial_no for record in changed if record.module == parent_module
            }
            missing = []
            for record in by_module[module]:
                data = record.data or {}
                old = snapshot(record)
                value = first(
                    data.get(key),
                    old.get({"customer_no": "CustomerNo", "contract_no": "ContractNo", "investigation_no": "InvestigationNo", "investigation_task_no": "InvestigationTaskNo"}[key]),
                )
                if value and value not in parent_nos:
                    existing = by_no.get(value)
                    missing.append({
                        "record": record.serial_no,
                        "parent": value,
                        "source": text(data.get("migration_source")) or "current",
                        "existing_module": existing.module if existing else "",
                        "legacy_projection_exists": value in projection_parent_nos[parent_module],
                    })
            unresolved[f"{module}->{parent_module}"] = missing

        result = {
            "mode": "apply" if apply else "dry-run",
            "created_customers": created_customers,
            "created_contracts": created_contracts,
            "changed_records": len(list(unique_changed)),
            "unresolved_counts": {key: len(value) for key, value in unresolved.items()},
            "unresolved_by_source": {
                key: dict(sorted(Counter(row["source"] for row in value).items()))
                for key, value in unresolved.items()
            },
            "wrong_module_counts": {
                key: dict(sorted(Counter(row["existing_module"] for row in value if row["existing_module"]).items()))
                for key, value in unresolved.items()
            },
            "recoverable_projection_counts": {
                key: sum(1 for row in value if row["legacy_projection_exists"])
                for key, value in unresolved.items()
            },
            "unresolved_samples": {key: value[:10] for key, value in unresolved.items() if value},
        }
        if apply:
            await db.commit()
        else:
            await db.rollback()
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit the atomic recovery")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.apply)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

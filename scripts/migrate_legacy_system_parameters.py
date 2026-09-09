#!/usr/bin/env python3
"""Migrate legacy fee types, causes and payment units into system_parameters."""
from __future__ import annotations
import argparse
import asyncio
import json
from pathlib import Path
from typing import Any
from sqlalchemy import select
from app.database import SessionLocal
from app.models import SystemParameter

ACTOR = "legacy_system_parameter_migration"

def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()

def enabled(value: Any) -> bool:
    return clean(value).casefold() not in {"0", "f", "false", "n", "no", "停用"}

def read_source(server: str, database: str, driver: str) -> dict[str, list[dict[str, Any]]]:
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError("pyodbc is required to read the legacy SQL Server") from exc
    connection_string = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;ApplicationIntent=ReadOnly;TrustServerCertificate=yes;"
    queries = {
        "fee_type": "SELECT FeeTypeId,FeeTypeName,TypeId,CaseTypeId,OfficeName,CPCOfficeName,FeeTypeCode,IsActived FROM dbo.BAS_Case_FeeType ORDER BY FeeTypeId",
        "cause": "SELECT CauseId,CauseName,ParentCauseId FROM dbo.BAS_Causes ORDER BY CauseId",
        "payment_type": "SELECT PaymentTypeId,CaseFeeTypeId,PaymentTypeName,OrganizationName,Account,AccountBank,Remark,IsActived FROM dbo.FAM_AP_PaymentType ORDER BY PaymentTypeId",
    }
    result: dict[str, list[dict[str, Any]]] = {}
    with pyodbc.connect(connection_string, autocommit=True) as connection:
        for category, query in queries.items():
            cursor = connection.cursor()
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            result[category] = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return result

def normalize(source: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    fee_group_names = {1: "官方费用", 2: "律师费用", 3: "提成费用", 4: "第三方费用", 5: "内部费用"}
    fee_group_bases = {1: "官方费用", 2: "代理费", 3: "其他费用", 4: "其他费用", 5: "内部费用"}
    used_fee_groups = sorted({int(row["TypeId"]) for row in source["fee_type"] if row.get("TypeId")})
    for type_id in used_fee_groups:
        result.append({
            "category": "fee_type", "code": f"LEGACY-FEE-GROUP-{type_id}",
            "name": fee_group_names.get(type_id, f"费用大类{type_id}"), "is_active": True,
            "sort_order": type_id * 100000000,
            "extra": {"legacy_group_id": type_id, "parent_code": "", "base_fee_type": fee_group_bases.get(type_id, "其他费用"), "expense_scopes": ["law_firm", "platform", "internal"]},
        })
    for row in source["fee_type"]:
        legacy_id = int(row["FeeTypeId"])
        # Negative rows are the old selector's "请选择..." placeholders, not
        # payable leaf values. The real hierarchy is TypeId -> FeeTypeId.
        if legacy_id < 0:
            continue
        type_id = int(row["TypeId"])
        result.append({"category": "fee_type", "code": f"LEGACY-FEE-{legacy_id}", "name": clean(row["FeeTypeName"]), "is_active": enabled(row["IsActived"]), "sort_order": type_id * 100000000 + legacy_id, "extra": {"legacy_id": legacy_id, "legacy_code": clean(row.get("FeeTypeCode")), "legacy_group_id": type_id, "parent_code": f"LEGACY-FEE-GROUP-{type_id}", "base_fee_type": fee_group_bases.get(type_id, "其他费用"), "expense_scopes": ["law_firm", "platform", "internal"], "case_type_id": row.get("CaseTypeId"), "office_name": clean(row.get("OfficeName")), "cpc_office_name": clean(row.get("CPCOfficeName"))}})
    for row in source["cause"]:
        legacy_id = int(row["CauseId"])
        parent_id = int(row.get("ParentCauseId") or 0)
        result.append({"category": "cause", "code": f"LEGACY-CAUSE-{legacy_id}", "name": clean(row["CauseName"]), "is_active": True, "sort_order": legacy_id, "extra": {"legacy_id": legacy_id, "parent_code": f"LEGACY-CAUSE-{parent_id}" if parent_id > 0 else ""}})
    for row in source["payment_type"]:
        legacy_id = int(row["PaymentTypeId"])
        result.append({"category": "payment_type", "code": f"LEGACY-PAYMENT-{legacy_id}", "name": clean(row["OrganizationName"]) or clean(row["PaymentTypeName"]), "is_active": enabled(row["IsActived"]), "sort_order": legacy_id, "extra": {"legacy_id": legacy_id, "fee_type_legacy_id": row.get("CaseFeeTypeId"), "nature": clean(row.get("PaymentTypeName")), "payee": clean(row.get("OrganizationName")), "account": clean(row.get("Account")), "account_bank": clean(row.get("AccountBank")), "remark": clean(row.get("Remark"))}})
    rows = [row for row in result if row["name"]]
    audit(rows)
    return rows


def audit(rows: list[dict[str, Any]]) -> None:
    keys = [(row["category"], row["code"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise RuntimeError("迁移源存在重复的系统参数编码")
    for category in ("fee_type", "cause"):
        codes = {row["code"] for row in rows if row["category"] == category}
        orphaned = [row["code"] for row in rows if row["category"] == category and (row["extra"].get("parent_code") or "") not in codes | {""}]
        if orphaned:
            raise RuntimeError(f"{category} 存在孤立父节点：{orphaned[:10]}")

async def migrate(rows: list[dict[str, Any]], apply: bool) -> dict[str, dict[str, int]]:
    stats = {category: {"source": 0, "created": 0, "updated": 0} for category in ("fee_type", "cause", "payment_type")}
    async with SessionLocal() as db:
        existing = list((await db.scalars(select(SystemParameter).where(SystemParameter.category.in_(stats)))).all())
        by_key = {(item.category, item.code): item for item in existing}
        by_legacy = {(item.category, str((item.extra or {}).get("legacy_id"))): item for item in existing if (item.extra or {}).get("legacy_id") is not None}
        for row in rows:
            category = row["category"]
            stats[category]["source"] += 1
            legacy_id = row["extra"].get("legacy_id")
            item = by_key.get((category, row["code"])) or (by_legacy.get((category, str(legacy_id))) if legacy_id is not None else None)
            if item is None:
                db.add(SystemParameter(created_by=ACTOR, updated_by=ACTOR, **row))
                stats[category]["created"] += 1
            else:
                item.code = row["code"]
                item.name = row["name"]
                item.extra = row["extra"]
                item.sort_order = row["sort_order"]
                item.is_active = row["is_active"]
                item.updated_by = ACTOR
                stats[category]["updated"] += 1
        if apply:
            await db.commit()
        else:
            await db.rollback()
    return stats

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default=".")
    parser.add_argument("--database", default="PRD_CRM_GD_20200211")
    parser.add_argument("--driver", default="SQL Server")
    parser.add_argument("--source-json", type=Path)
    parser.add_argument("--export-json", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.source_json:
        rows = json.loads(args.source_json.read_text(encoding="utf-8"))
    else:
        rows = normalize(read_source(args.server, args.database, args.driver))
    if args.export_json:
        args.export_json.parent.mkdir(parents=True, exist_ok=True)
        args.export_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"exported": len(rows), "path": str(args.export_json)}, ensure_ascii=False))
        return 0
    print(json.dumps(asyncio.run(migrate(rows, args.apply)), ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

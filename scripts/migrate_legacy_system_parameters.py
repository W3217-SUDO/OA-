#!/usr/bin/env python3
"""Migrate legacy fee types, causes and payment units into system_parameters."""
from __future__ import annotations
import argparse
import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from sqlalchemy import select
from app.database import SessionLocal
from app.models import SystemParameter

ACTOR = "legacy_system_parameter_migration"
FEE_GROUP_NAMES = {1: "官费", 2: "代理费", 3: "其他费用", 4: "内部提成", 5: "第三方费用", 6: "平台费用"}
FEE_GROUP_BASES = {1: "官方费用", 2: "代理费", 3: "其他费用", 4: "内部费用", 5: "其他费用", 6: "其他费用"}

def source_audit(row: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for source, target in (("CreateUser", "created_by"), ("ChangeUser", "updated_by")):
        if clean(row.get(source)):
            result[target] = clean(row[source])
    for source, target in (("CreateTime", "created_at"), ("ChangeTime", "updated_at")):
        if row.get(source):
            value = row[source] if isinstance(row[source], datetime) else datetime.fromisoformat(str(row[source]))
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone(timedelta(hours=8)))
            result[target] = value.astimezone(timezone.utc)
    return result

def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()

def enabled(value: Any) -> bool:
    return clean(value).casefold() not in {"0", "f", "false", "n", "no", "停用"}

def field(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    """Read legacy exports that use SQL column names or xlsx/JSON aliases."""
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default
def read_source(server: str, database: str, driver: str) -> dict[str, list[dict[str, Any]]]:
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError("pyodbc is required to read the legacy SQL Server") from exc
    connection_string = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;ApplicationIntent=ReadOnly;TrustServerCertificate=yes;"
    queries = {
        "fee_type": "SELECT * FROM dbo.BAS_Case_FeeType WHERE CaseTypeId > 0 ORDER BY FeeTypeId",
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
    fee_group_names = FEE_GROUP_NAMES
    fee_group_bases = FEE_GROUP_BASES
    used_fee_groups = sorted({int(field(row, "TypeId", "type_id", "费用类型大类ID", default=0)) for row in source["fee_type"] if field(row, "TypeId", "type_id", "费用类型大类ID", default=0) not in (None, "")})
    for type_id in used_fee_groups:
        result.append({
            "category": "fee_type", "code": f"LEGACY-FEE-GROUP-{type_id}",
            "name": fee_group_names.get(type_id, f"费用大类{type_id}"), "is_active": True,
            "sort_order": type_id * 100000000,
            "extra": {"legacy_group_id": type_id, "parent_code": "", "base_fee_type": fee_group_bases.get(type_id, "其他费用"), "expense_scopes": ["law_firm", "platform", "internal"]},
        })
    for row in source["fee_type"]:
        legacy_id = int(field(row, "FeeTypeId", "CaseFeeTypeId", "fee_type_id", "费用类型ID"))
        # Keep legacy placeholders visible in maintenance, always inactive.
        type_id = int(field(row, "TypeId", "type_id", "费用类型大类ID", default=0))
        result.append({"category": "fee_type", "code": f"LEGACY-FEE-{legacy_id}", "name": clean(field(row, "FeeTypeName", "CaseFeeTypeName", "name", "费用类型名称")), "is_active": enabled(field(row, "IsActived", "is_active", "启用", default=True)), "sort_order": type_id * 100000000 + legacy_id, "extra": {"legacy_id": legacy_id, "legacy_code": clean(field(row, "FeeTypeCode", "code", "费用类型编码", default=legacy_id)), "legacy_group_id": type_id, "parent_code": f"LEGACY-FEE-GROUP-{type_id}", "base_fee_type": fee_group_bases.get(type_id, "其他费用"), "expense_scopes": ["law_firm", "platform", "internal"], "case_type_id": field(row, "CaseTypeId", "case_type_id", "案件类型ID"), "office_name": clean(field(row, "OfficeName", "office_name")), "cpc_office_name": clean(field(row, "CPCOfficeName", "cpc_office_name"))}})
        result[-1].update(source_audit(row))
        result[-1]["is_active"] = legacy_id > 0 and result[-1]["is_active"]
        result[-1]["extra"]["is_invoiced"] = enabled(row.get("IsInvoiced", True))
        if row.get("CreateTime") or row.get("ChangeTime"):
            result[-1]["extra"]["legacy_audit_utc"] = True
    for row in result:
        row["extra"]["expense_scopes"] = ["internal"] if row["extra"]["legacy_group_id"] == 4 else ["law_firm", "platform"]
    for row in source["cause"]:
        legacy_id = int(field(row, "CauseId", "cause_id", "案由ID"))
        parent_id = int(field(row, "ParentCauseId", "parent_cause_id", "父案由ID", default=0) or 0)
        result.append({"category": "cause", "code": f"LEGACY-CAUSE-{legacy_id}", "name": clean(field(row, "CauseName", "name", "案由名称")), "is_active": True, "sort_order": legacy_id, "extra": {"legacy_id": legacy_id, "parent_code": f"LEGACY-CAUSE-{parent_id}" if parent_id > 0 else ""}})
    for row in source["payment_type"]:
        legacy_id = int(field(row, "PaymentTypeId", "payment_type_id", "付款类型ID"))
        result.append({"category": "payment_type", "code": f"LEGACY-PAYMENT-{legacy_id}", "name": clean(field(row, "OrganizationName", "organization_name", "收款单位")) or clean(field(row, "PaymentTypeName", "payment_type_name", "付款类型")), "is_active": enabled(field(row, "IsActived", "is_active", "启用", default=True)), "sort_order": legacy_id, "extra": {"legacy_id": legacy_id, "fee_type_legacy_id": field(row, "CaseFeeTypeId", "fee_type_id"), "nature": clean(field(row, "PaymentTypeName", "payment_type_name", "付款类型")), "payee": clean(field(row, "OrganizationName", "organization_name", "收款单位")), "account": clean(field(row, "Account", "account", "账号")), "account_bank": clean(field(row, "AccountBank", "account_bank", "开户行")), "remark": clean(field(row, "Remark", "remark", "备注"))}})
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
    stats = {category: {"source": 0, "created": 0, "updated": 0, "deleted": 0} for category in ("fee_type", "cause", "payment_type")}
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
                values = {"created_by": ACTOR, "updated_by": ACTOR, **row}
                for key in ("created_at", "updated_at"):
                    if isinstance(values.get(key), str):
                        values[key] = datetime.fromisoformat(values[key])
                db.add(SystemParameter(**values))
                stats[category]["created"] += 1
            else:
                if category != "fee_type":
                    item.code = row["code"]
                item.name = row["name"]
                item.extra = {**(item.extra or {}), **row["extra"]}
                item.sort_order = row["sort_order"]
                item.is_active = row["is_active"]
                item.updated_by = ACTOR
                for key in ("created_by", "updated_by", "created_at", "updated_at"):
                    if key in row:
                        value = row[key]
                        if key.endswith("_at") and isinstance(value, str):
                            value = datetime.fromisoformat(value)
                        setattr(item, key, value)
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
        args.export_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"exported": len(rows), "path": str(args.export_json)}, ensure_ascii=False))
        return 0
    print(json.dumps(asyncio.run(migrate(rows, args.apply)), ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

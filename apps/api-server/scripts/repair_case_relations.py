"""限定范围的案件关系修复：计划导出、校验后应用、按原值恢复。"""
import argparse
import asyncio
from datetime import date, datetime
import hashlib
import json
from pathlib import Path

from sqlalchemy import Date, DateTime, delete, inspect, select, update
from app.database import Base, SessionLocal
from app.models import BusinessRecord
from app.core.case_relation_repair import repair_case_relations


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))


async def plan(spec, db):
    with db.no_autoflush:
        await repair_case_relations(spec, db)
        tables = {}
        related_ids = set()
        for item in db.dirty:
            table = inspect(item).mapper.local_table
            pk = list(table.primary_key.columns)
            condition = [column == getattr(item, column.key) for column in pk]
            row = (await db.execute(select(table).where(*condition))).mappings().one()
            tables.setdefault(table.name, []).append(dict(row))
            for key in ("record_id", "case_record_id"):
                if key in row:
                    related_ids.update(value for value in (row[key], getattr(item, key)) if value is not None)
            if table.name == "business_records":
                related_ids.add(item.id)
                for data in (row["data"] or {}, item.data or {}):
                    for key, value in data.items():
                        if key.endswith("_id") and str(value or "").isdigit():
                            related_ids.add(int(value))
                        if key.endswith("_ids") and isinstance(value, list):
                            related_ids.update(int(v) for v in value if str(v or "").isdigit())
        for item in db.new:
            tables.setdefault(inspect(item).mapper.local_table.name, [])
        for rows in tables.values():
            rows.sort(key=lambda row: encoded(row))
        relations = [dict(row) for row in (await db.execute(select(BusinessRecord.__table__).where(BusinessRecord.id.in_(related_ids)).order_by(BusinessRecord.id))).mappings()]
        snapshot = {"tables": tables, "relations": relations}
        return {"spec": spec, **snapshot, "sha256": hashlib.sha256(encoded(snapshot).encode()).hexdigest()}


async def run(args):
    async with SessionLocal() as db:
        if args.mode == "plan":
            spec = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
            result = await plan(spec, db)
            print(encoded(result))
            await db.rollback()
        elif args.mode == "apply":
            saved = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
            result = await plan(saved["spec"], db)
            if result["sha256"] != saved["sha256"]:
                raise ValueError("备份与当前待修改记录不一致，停止应用")
            new = list(db.new)
            await db.flush()
            inserted = [{"table": inspect(item).mapper.local_table.name,
                         "keys": {column.key: getattr(item, column.key) for column in inspect(item).mapper.local_table.primary_key.columns}}
                        for item in new]
            await db.commit()
            print(encoded({"sha256": saved["sha256"], "inserted": inserted, "applied": True}))
        else:
            saved = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
            receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8-sig"))
            if saved["sha256"] != receipt["sha256"]:
                raise ValueError("恢复回执与备份不匹配")
            for row in reversed(receipt["inserted"]):
                table = Base.metadata.tables[row["table"]]
                await db.execute(delete(table).where(*(table.c[key] == value for key, value in row["keys"].items())))
            for name, rows in saved["tables"].items():
                table = Base.metadata.tables[name]
                for raw in rows:
                    row = dict(raw)
                    for column in table.columns:
                        if row.get(column.name) and isinstance(column.type, DateTime):
                            row[column.name] = datetime.fromisoformat(row[column.name])
                        elif row.get(column.name) and isinstance(column.type, Date):
                            row[column.name] = date.fromisoformat(row[column.name])
                    await db.execute(update(table).where(*(column == row[column.name] for column in table.primary_key.columns)).values(**row))
            await db.commit()
            print(encoded({"restored": True, "sha256": saved["sha256"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "apply", "restore"))
    parser.add_argument("input")
    parser.add_argument("--receipt")
    asyncio.run(run(parser.parse_args()))

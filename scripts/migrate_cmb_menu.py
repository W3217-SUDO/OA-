"""One-time CMB menu grant migration. Export scoped tables before apply."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=["backup", "apply", "rollback"])
parser.add_argument("--service-pid", type=int)
parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
if args.service_pid:
    for part in Path(f"/proc/{args.service_pid}/environ").read_bytes().split(b"\0"):
        if b"=" in part:
            key, value = part.split(b"=", 1)
            os.environ[key.decode()] = value.decode()
sys.path.insert(0, str(args.repo / "apps" / "api-server"))
from app.database import engine
from sqlalchemy import text

KEY = "finance-receipts-cmb"
OLD = {"finance-receipts-icbc", "finance-receipts-citic", "finance-receipts-boc"}
TABLES = ("system_menus", "role_permissions", "job_roles", "users")

def decode(value, fallback):
    return json.loads(value) if isinstance(value, str) else (value or fallback)

async def main():
    async with engine.begin() as conn:
        if args.mode == "backup":
            data = {name: [dict(row) for row in (await conn.execute(text(f"SELECT * FROM {name}"))).mappings()] for name in TABLES}
            payload = json.dumps(data, ensure_ascii=False, default=str, sort_keys=True, separators=(",", ":"))
            print(json.dumps({"payload": payload, "sha256": hashlib.sha256(payload.encode()).hexdigest()}, ensure_ascii=False))
        else:
            counts = {}
            for table, column in (("role_permissions", "menu_keys"), ("job_roles", "permissions"), ("users", "profile")):
                changed = 0
                for row in (await conn.execute(text(f"SELECT id, {column} FROM {table}"))).mappings():
                    value = decode(row[column], {} if table == "users" else [])
                    if table == "users":
                        overrides = value.get("permission_overrides") or {}
                        keys = overrides.get("menu_keys")
                        if not isinstance(keys, list):
                            continue
                    else:
                        keys = value
                    if args.mode == "apply":
                        if KEY in keys or not OLD.issubset(set(keys)):
                            continue
                        updated = [*keys, KEY]
                    else:
                        if KEY not in keys:
                            continue
                        updated = [key for key in keys if key != KEY]
                    if table == "users":
                        value = {**value, "permission_overrides": {**overrides, "menu_keys": updated}}
                    else:
                        value = updated
                    await conn.execute(text(f"UPDATE {table} SET {column}=:value WHERE id=:id"), {"value": json.dumps(value, ensure_ascii=False), "id": row["id"]})
                    changed += 1
                counts[table] = changed
            if args.mode == "rollback":
                await conn.execute(text("DELETE FROM system_menus WHERE key=:key"), {"key": KEY})
            print(json.dumps({"mode": args.mode, "updated": counts}))
    await engine.dispose()

asyncio.run(main())

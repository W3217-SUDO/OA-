"""复用现有人事导入器，保留管理员凭据并补全员工原字段。"""

import asyncio
import importlib.util
import sys
from pathlib import Path
from psycopg.types.json import Jsonb
from .common import SOURCE, connect, rows, save_report
from ..hz_field_maps import json_value, mapped_data, text


async def main():
    api = Path(__file__).resolve().parents[2] / "apps" / "api-server"
    sys.path.insert(0, str(api))
    spec = importlib.util.spec_from_file_location("existing_hr_migration", api / "scripts" / "migrate_legacy_hr.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SOURCE = SOURCE
    with connect() as pg:
        payload = {
            "source": SOURCE,
            "departments": json_value(rows(pg, "HR_Department")),
            "staff": json_value(rows(pg, "HR_Staff")),
            "performances": json_value(rows(pg, "HR_Staff_Performance")),
        }
        admin_before = pg.execute("SELECT password_hash,role,is_active FROM users WHERE username='admin'").fetchone()
    async with module.SessionLocal() as session:
        report = await module.migrate_payload(session, payload)
        await session.commit()
    await module.engine.dispose()
    with connect() as pg:
        for row in payload["staff"]:
            username = text(row["StaffName"]).lower()
            # 密码及摘要仅用于认证表，不放入面向页面的员工资料。
            sanitized = {k: v for k, v in row.items() if "password" not in k.lower()}
            data = mapped_data("hr", sanitized)
            data["legacy_record"] = sanitized
            pg.execute(
                "UPDATE business_records SET data=(data::jsonb || %s)::json, description='沪知旧系统员工资料迁移', customer=%s WHERE module='hr' AND data->>'username'=%s",
                (Jsonb(data), text(row.get("Company")), username),
            )
            pg.execute(
                "UPDATE users SET profile=(profile::jsonb || %s)::json WHERE username=%s",
                (Jsonb({"company": text(row.get("Company"))}), username),
            )
        admin_after = pg.execute("SELECT password_hash,role,is_active FROM users WHERE username='admin'").fetchone()
        if admin_after != admin_before:
            raise RuntimeError("Administrator authentication was unexpectedly changed")
        report["admin_credentials_preserved"] = True
        report["sensitive_fields_excluded"] = True
    save_report("people-report.json", report)


if __name__ == "__main__":
    asyncio.run(main())

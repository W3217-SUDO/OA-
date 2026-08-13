"""Print bounded non-secret relation evidence for selected business records."""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import BusinessRecord


EVIDENCE_KEYS = (
    "investigation_no",
    "investigation_record_id",
    "investigation_title",
    "investigation_task_no",
    "source_task_id",
    "source_task_no",
    "source_task_title",
    "contract_id",
    "contract_no",
    "customer_id",
    "customer_no",
    "publisher",
    "initiator",
    "assignee",
    "investigator",
    "start_date",
    "deadline",
)


async def run(serial_nos: list[str]) -> None:
    async with SessionLocal() as db:
        records = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.serial_no.in_(serial_nos)
        ))).all())
        output = []
        for record in records:
            data = record.data or {}
            linked = {}
            for key in ("investigation_record_id", "source_task_id", "contract_id", "customer_id"):
                value = data.get(key)
                if not isinstance(value, int):
                    continue
                candidate = await db.get(BusinessRecord, value)
                linked[key] = {
                    "exists": candidate is not None,
                    "module": candidate.module if candidate else "",
                    "serial_no": candidate.serial_no if candidate else "",
                    "title": candidate.title if candidate else "",
                }
            output.append({
                "serial_no": record.serial_no,
                "module": record.module,
                "title": record.title,
                "customer": record.customer,
                "owner": record.owner,
                "department": record.department,
                "evidence": {key: data.get(key) for key in EVIDENCE_KEYS if data.get(key) not in (None, "", [])},
                "linked_records": linked,
            })
        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:]))

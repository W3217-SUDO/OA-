"""Audit ordinary case-search filtering without changing data."""

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.main import CounselCaseSearchInput, _query_counsel_cases, _record_scope_conditions
from app.models import BusinessRecord, User


async def run(username: str) -> None:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if user is None:
            raise RuntimeError(f"User does not exist: {username}")
        identity = {
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "department": user.department,
        }
        all_cases = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "case"
        ))).all())
        scope_conditions = await _record_scope_conditions(identity, db)
        visible_cases = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "case", *scope_conditions
        ))).all())
        searched = await _query_counsel_cases(
            CounselCaseSearchInput(scope="company", page=1, page_size=15),
            identity,
            db,
            counsel_only=False,
        )
        print(json.dumps({
            "identity": identity,
            "all_cases": len(all_cases),
            "visible_cases": len(visible_cases),
            "search_results": len(searched),
            "case_types": Counter(str((record.data or {}).get("case_type") or "") for record in visible_cases),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "admin"))

"""普通案件检索快速路径：类型/阶段筛选、阶段计数、排序和分页在数据库内完成，结果必须与完整筛选路径逐条一致。"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api_schemas.cases import CounselCaseSearchInput
from app.areas.legal.router import search_ordinary_cases
from app.core import case_search_projection as projection
from app.core.cases import _case_search_scope_conditions, _query_counsel_cases
from app.database import Base
from app.models import BusinessRecord, User


IDENTITY = {"username": "fast-admin", "role": "admin", "role_ids": ["admin"], "display_name": "快速检索管理员", "department": "诉讼部"}
TYPES = ("民事争议", "民事案件", "刑事案件", "法律顾问", "仲裁", None)
PHASES = ("文书准备", "等待立案", "一审阶段", "归档审核", None, " 等待立案 ")


async def full_path(body, db):
    records = await _query_counsel_cases(body, IDENTITY, db, counsel_only=False, include_status_filter=False, search_projection=True)
    counts: dict[str, int] = {}
    for record in records:
        counts[str(record.status or "")] = counts.get(str(record.status or ""), 0) + 1
    matched = [record for record in records if projection.matches_case_search_status(record, body)]
    page = await projection.read_case_search_page(matched, body.page, body.page_size, db)
    return counts, len(matched), [record.id for record in page]


async def fast_path(body, db):
    counts, total, page = await projection.fast_case_search_page(body, await _case_search_scope_conditions(body, IDENTITY, db), db)
    return counts, total, [record.id for record in page]


class CaseSearchFastPathTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        base = datetime(2026, 1, 1, 8, 0, 0)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"],
                        role="admin", role_ids=["admin"], password_hash="x", profile={}, is_active=True))
            for index in range(60):
                case_type = TYPES[index % len(TYPES)]
                created = base + timedelta(hours=index % 7)  # 刻意制造相同时间，检验按 id 的次序
                db.add(BusinessRecord(
                    module="case",
                    serial_no=f"CODEX-FAST-{(index * 37) % 60:03d}{'a' if index % 5 == 0 else 'B'}",
                    title=f"快速检索{index}",
                    customer=f"客户{index % 4}",
                    status=PHASES[index % len(PHASES)] if index != 59 else "已合并",
                    owner=IDENTITY["username"],
                    department=IDENTITY["department"],
                    data={"case_type": case_type} if case_type is not None else {},
                    created_at=created,
                    updated_at=None if index % 4 == 0 else created + timedelta(minutes=index % 3),
                ))
            await db.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_fast_path_matches_full_filter(self):
        scenarios = []
        for scope in ("company", "department", "mine", "global"):
            for types in (["民事争议", "民事案件"], ["刑事案件"], ["法律顾问"], []):
                scenarios += [
                    dict(scope=scope, case_types=types),
                    dict(scope=scope, case_types=types, case_status="等待"),
                    dict(scope=scope, case_types=types, case_statuses=["等待立案", "归档审核"]),
                    dict(scope=scope, case_types=types, page=2, page_size=4),
                ]
        for sort in sorted(projection.SORT_ORDERS):
            for page in (1, 2, 3):
                scenarios.append(dict(scope="company", sort_order=sort, page=page, page_size=7))
        scenarios.append(dict(scope="company", case_type="仲裁", case_types=["刑事案件"]))
        scenarios.append(dict(scope="company", page=50))
        async with self.sessions() as db:
            for scenario in scenarios:
                with self.subTest(**scenario):
                    body = CounselCaseSearchInput(**scenario)
                    self.assertTrue(projection.fast_case_search_eligible(body))
                    self.assertEqual(await fast_path(body, db), await full_path(body, db))

    async def test_endpoint_response_is_unchanged(self):
        body = CounselCaseSearchInput(scope="company", case_types=["民事争议", "民事案件"], page_size=5)
        async with self.sessions() as db:
            fast = await search_ordinary_cases(body, IDENTITY, db)
            with patch.object(projection, "fast_case_search_eligible", lambda _body: False):
                full = await search_ordinary_cases(body, IDENTITY, db)
        self.assertEqual(fast, full)
        self.assertGreater(fast["total"], 0)

    def test_other_conditions_keep_the_full_filter(self):
        for extra in ({"keyword": "客户"}, {"plaintiff": "甲"}, {"customer_id": 1}, {"case_queue": "urgent"},
                      {"dashboard_queue": "x"}, {"selected_only": True}, {"advanced_logic": "or"}, {"sort_order": "bogus"}):
            with self.subTest(**extra):
                self.assertFalse(projection.fast_case_search_eligible(CounselCaseSearchInput(scope="company", **extra)))
        self.assertTrue(projection.fast_case_search_eligible(CounselCaseSearchInput(
            scope="department", case_types=["民事争议"], case_status="", customer_id=None, advanced_logic="and")))


if __name__ == "__main__":
    unittest.main()

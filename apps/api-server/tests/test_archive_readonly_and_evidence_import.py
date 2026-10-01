"""验证归档查询只读与证据 CSV 逐行保存点。"""

import io
import os
import re
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.legal.router import archive_readiness
from app.areas.wms.router import import_evidence_records
from app.core.cases import _case_archive_checks
from app.database import Base
from app.models import BusinessRecord, User, WorkflowEvent


POSTGRES_URL = os.environ.get("ARCHIVE_EVIDENCE_TEST_POSTGRES_URL", "")


class ArchiveAndEvidenceAssertions:
    async def asyncSetUp(self):
        if self.database_url:
            if make_url(self.database_url).database != "oa_test_enterprise_commands":
                raise RuntimeError("归档和证据测试只能使用专用 PostgreSQL 测试库")
            self.schema = f"oa_test_enterprise_checks_{uuid4().hex[:12]}"
            self.admin_engine = create_async_engine(self.database_url)
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
            self.engine = create_async_engine(
                self.database_url,
                connect_args={"server_settings": {"search_path": self.schema}},
            )
        else:
            self.engine = create_async_engine(
                "sqlite+aiosqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.database_url:
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin_engine.dispose()

    async def _seed_case(self, db):
        db.add(User(
            username="archive-lawyer", display_name="归档律师", department="上海",
            password_hash="x", role="admin",
        ))
        case = BusinessRecord(
            module="case", serial_no="ENTERPRISE-CHECKS-CASE", title="归档检查案件",
            customer="测试客户", status="办理中", owner="archive-lawyer", department="上海",
            data={"case_type": "民事案件", "case_closed_at": "2026-09-01T00:00:00",
                  "case_closed_by": "archive-lawyer", "archive_no": "DA-01"},
        )
        db.add(case)
        await db.flush()
        db.add(BusinessRecord(
            module="finance", serial_no="ENTERPRISE-CHECKS-FEE", title="诉讼费用",
            customer="测试客户", status="待收款", owner="archive-lawyer", department="上海",
            data={"case_id": case.id, "case_no": case.serial_no, "amount": 100,
                  "fee_type": "诉讼费用", "expense_scope": "律所"},
        ))
        await db.commit()
        return case.id

    async def test_archive_get_is_readonly_and_action_preserves_projection(self):
        async with self.sessions() as db:
            case_id = await self._seed_case(db)

        writes = []

        def count_writes(_connection, _cursor, statement, _parameters, _context, _executemany):
            if re.match(r"^\s*(INSERT|UPDATE|DELETE)\b", statement, re.IGNORECASE):
                writes.append(statement)

        event.listen(self.engine.sync_engine, "before_cursor_execute", count_writes)
        try:
            async with self.sessions() as db:
                response = await archive_readiness(
                    case_id, {"username": "archive-lawyer", "role": "admin"}, db,
                )
                self.assertFalse(db.dirty)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", count_writes)
        self.assertEqual(writes, [])
        self.assertEqual(response["checks"], {
            "case_closed": True, "fees_settled": False,
            "documents_complete": False, "finance_complete": False,
        })
        self.assertEqual(response["check_details"]["unsettled_fees"][0]["outstanding"], 100)
        self.assertEqual(response["archive_no"], "DA-01")

        async with self.sessions() as db:
            case = await db.get(BusinessRecord, case_id)
            self.assertNotIn("archive_check_details", case.data)
            action_checks = await _case_archive_checks(case, db)
            action_details = case.data["archive_check_details"]
            await db.commit()
        self.assertEqual(action_checks, response["checks"])
        self.assertEqual(action_details, response["check_details"])
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, case_id)
            self.assertEqual(case.data["archive_check_details"], response["check_details"])
            self.assertEqual(case.data["archive_material_categories"], [])

    async def test_csv_row_failure_preserves_other_rows_and_links(self):
        async with self.sessions() as db:
            db.add(User(
                username="evidence-lawyer", display_name="证据律师", department="上海",
                password_hash="x", role="admin",
            ))
            clue = BusinessRecord(
                module="clue", serial_no="ENTERPRISE-CHECKS-CLUE", title="关联线索",
                customer="测试客户", status="有效", owner="evidence-lawyer", department="上海",
                data={},
            )
            db.add(clue)
            await db.commit()
            clue_id = clue.id

        from app.core.investigation import _build_evidence_record

        async def fail_after_build(entry, identity, db):
            record = await _build_evidence_record(entry, identity, db)
            if entry.title == "中间行失败":
                raise ValueError("模拟后续校验失败")
            return record

        csv_content = (
            "title,clue_no\n"
            "首行成功,ENTERPRISE-CHECKS-CLUE\n"
            "中间行失败,ENTERPRISE-CHECKS-CLUE\n"
            "末行成功,ENTERPRISE-CHECKS-CLUE\n"
        ).encode("utf-8")
        async with self.sessions() as db:
            with patch("app.core.investigation._build_evidence_record", fail_after_build):
                result = await import_evidence_records(
                    UploadFile(file=io.BytesIO(csv_content), filename="evidence.csv"),
                    {"username": "evidence-lawyer", "role": "admin"}, db,
                )
        self.assertEqual(result["created"], 2)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"][0]["row"], 3)

        async with self.sessions() as db:
            titles = (await db.scalars(select(BusinessRecord.title).where(
                BusinessRecord.module == "evidence",
            ).order_by(BusinessRecord.id))).all()
            self.assertEqual(titles, ["首行成功", "末行成功"])
            clue = await db.get(BusinessRecord, clue_id)
            self.assertEqual(len(clue.data["evidence_ids"]), 2)
            self.assertEqual(clue.data["evidence_count"], 2)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(
                WorkflowEvent.action == "登记证据",
            )), 2)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(
                WorkflowEvent.action == "建立证据目录",
            )), 2)


class ArchiveAndEvidenceSQLiteTests(ArchiveAndEvidenceAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = ""


@unittest.skipUnless(POSTGRES_URL, "需要显式设置 ARCHIVE_EVIDENCE_TEST_POSTGRES_URL")
class ArchiveAndEvidencePostgresTests(ArchiveAndEvidenceAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = POSTGRES_URL

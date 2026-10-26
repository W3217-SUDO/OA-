"""问题处理中心：编号按提交日期加当天流水；管理员可以删除问题（逻辑删除，删除后编号不重用）。"""
import re
import unittest
from datetime import datetime

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.system import feedback
from app.core import soft_delete
from app.core.feedback_serial_migration import upgrade_feedback_date_serial
from app.core.dependencies import current_identity, get_db
from app.database import Base
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent

ADMIN = {"username": "CODEXFBADMIN", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
         "display_name": "反馈管理员", "department": "CODEXFB"}
STAFF = {"username": "CODEXFBSTAFF", "role": "staff", "role_ids": ["staff"], "_actual_role_ids": ["staff"],
         "display_name": "反馈提交人", "department": "CODEXFB"}


class FeedbackSerialAndDeleteTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name="反馈管理员", password_hash="isolated-only",
                     department="CODEXFB", role="admin"),
                User(username=STAFF["username"], display_name="反馈提交人", password_hash="isolated-only",
                     department="CODEXFB", role="staff"),
            ])
            await db.commit()
        self.identity = dict(ADMIN)
        app = FastAPI()
        app.include_router(feedback.router)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _record(self, db, serial_no, *, deleted=False):
        record = BusinessRecord(module="bug_feedback", serial_no=serial_no, title="CODEXFB", customer="",
                                status="待处理", owner=STAFF["username"], description="CODEXFB", data={})
        db.add(record)
        await db.commit()
        if deleted:
            await db.delete(record)
            await db.commit()
        return record

    async def test_serial_is_date_plus_daily_sequence_and_skips_deleted_numbers(self):
        day = datetime(2026, 10, 26, 9, 30, tzinfo=feedback.FEEDBACK_TZ)
        async with self.sessions() as db:
            self.assertEqual(await feedback._next_feedback_serial(db, now=day), "BUG20261026001")
            await self._record(db, "BUG20261026001")
            await self._record(db, "BUG20261026002", deleted=True)
            await self._record(db, "BUG20261025007")
            await self._record(db, "BUG3F2A9C0D1E2B3A4C5D6E")
            # 删除的问题仍占号；前一天和旧格式编号不影响当天流水。
            self.assertEqual(await feedback._next_feedback_serial(db, now=day), "BUG20261026003")
            next_day = datetime(2026, 10, 27, 0, 5, tzinfo=feedback.FEEDBACK_TZ)
            self.assertEqual(await feedback._next_feedback_serial(db, now=next_day), "BUG20261027001")
            # 日期按北京时间：UTC 10 月 26 日 16:30 已是北京时间 27 日。
            utc_evening = datetime.fromisoformat("2026-10-26T16:30:00+00:00")
            self.assertEqual(await feedback._next_feedback_serial(db, now=utc_evening), "BUG20261027001")

    async def test_submitted_feedback_gets_sequential_serials(self):
        self.identity = dict(STAFF)
        serials = []
        for text in ("CODEXFB 第一个问题", "CODEXFB 第二个问题"):
            response = await self.client.post("/api/v1/feedback/submit", json={"description": text, "page": "工作台"})
            self.assertEqual(response.status_code, 200, response.text)
            serials.append(response.json()["serial_no"])
        self.assertRegex(serials[0], r"^BUG\d{8}001$")
        self.assertEqual(serials[1], f"{serials[0][:-3]}002")

    async def test_only_admin_can_delete_and_delete_is_logical(self):
        self.identity = dict(STAFF)
        created = await self.client.post("/api/v1/feedback/submit", json={"description": "CODEXFB 待删除", "page": "工作台"})
        self.assertEqual(created.status_code, 200, created.text)
        feedback_id, serial_no = created.json()["id"], created.json()["serial_no"]
        async with self.sessions() as db:
            db.add(FileAttachment(record_id=feedback_id, category="问题反馈截图", original_name="a.png",
                                  stored_name="codexfb-a.png", content_type="image/png", size=1,
                                  path="/nonexistent/codexfb-a.png", uploader=STAFF["username"], remark=""))
            await db.commit()

        listing = await self.client.get("/api/v1/feedback", params={"mine": True})
        self.assertFalse(listing.json()["can_delete"])
        self.assertFalse((await self.client.get(f"/api/v1/feedback/{feedback_id}")).json()["can_delete"])
        denied = await self.client.delete(f"/api/v1/feedback/{feedback_id}")
        self.assertEqual(denied.status_code, 403, denied.text)

        self.identity = dict(ADMIN)
        listing = await self.client.get("/api/v1/feedback")
        self.assertTrue(listing.json()["can_delete"])
        self.assertTrue((await self.client.get(f"/api/v1/feedback/{feedback_id}")).json()["can_delete"])
        deleted = await self.client.delete(f"/api/v1/feedback/{feedback_id}")
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json(), {"id": feedback_id, "serial_no": serial_no})

        listing = await self.client.get("/api/v1/feedback")
        self.assertEqual(listing.json()["total"], 0)
        self.assertEqual((await self.client.get("/api/v1/feedback/status-counts")).json()["total"], 0)
        self.assertEqual((await self.client.get(f"/api/v1/feedback/{feedback_id}")).status_code, 404)
        self.assertEqual((await self.client.delete(f"/api/v1/feedback/{feedback_id}")).status_code, 404)

        async with self.sessions() as db:
            raw = select(BusinessRecord).where(BusinessRecord.id == feedback_id).execution_options(include_deleted=True)
            record = await db.scalar(raw)
            self.assertIsNotNone(record.deleted_at)
            self.assertEqual(record.deleted_by, ADMIN["username"])
            for model in (WorkflowEvent, FileAttachment):
                rows = (await db.scalars(select(model).where(model.record_id == feedback_id)
                                         .execution_options(include_deleted=True))).all()
                self.assertTrue(rows)
                self.assertTrue(all(row.deleted_at is not None for row in rows), model.__name__)

        # 删除后新提交的问题不重用被删的编号。
        self.identity = dict(STAFF)
        again = await self.client.post("/api/v1/feedback/submit", json={"description": "CODEXFB 删除后再提", "page": "工作台"})
        self.assertEqual(again.status_code, 200, again.text)
        self.assertNotEqual(again.json()["serial_no"], serial_no)
        self.assertEqual(int(re.search(r"(\d{3})$", again.json()["serial_no"]).group(1)),
                         int(serial_no[-3:]) + 1)

    async def test_migration_renumbers_old_serials_by_beijing_date(self):
        def utc(text):
            return datetime.fromisoformat(f"{text}+00:00")
        # 与生产上的旧问题同样的编号格式；时间是 UTC，北京时间 +8。
        rows = [
            ("BUG855D1A2F448043179850", "2026-10-26T09:02:00", None, {"page": "案件详情"}),
            ("BUG26B4DC9A60A54720BA1E", "2026-10-26T09:00:00", None, {}),
            ("BUG1B85B2CB8B204546AA57", "2026-10-26T03:23:00", None, {}),
            ("BUG76197D1B1E7247D9B7EC", "2026-10-25T04:06:00", None, {}),
            ("BUG8D8B25AD93FA4F5F9694", "2026-10-24T14:35:00", None, {}),
            ("BUG00000000000000000A0B", "2026-10-24T16:30:00", "2026-10-25T01:00:00", {}),  # 已删除，北京时间 25 日
            ("BUG20261026001", "2026-10-26T10:00:00", None, {}),  # 当天已有新编号，旧问题接在后面
        ]
        table = BusinessRecord.__table__
        async with self.engine.begin() as connection:
            await connection.execute(table.insert(), [{
                "module": "bug_feedback", "serial_no": serial, "title": "CODEXFB", "customer": "", "status": "待处理",
                "owner": STAFF["username"], "department": "CODEXFB", "description": "CODEXFB", "data": data,
                "created_at": utc(created), "updated_at": utc(created), "deleted_at": utc(deleted) if deleted else None,
            } for serial, created, deleted, data in rows])
            await connection.execute(table.insert(), [{
                "module": "case", "serial_no": "BUGAAAAAAAAAAAAAAAAAAAA", "title": "CODEXFB 其他模块", "customer": "",
                "status": "草稿", "owner": STAFF["username"], "department": "CODEXFB", "description": "", "data": {},
            }])
            self.assertEqual(await connection.run_sync(upgrade_feedback_date_serial), 6)
            self.assertEqual(await connection.run_sync(upgrade_feedback_date_serial), 0)
            result = {row.data.get("legacy_serial_no", row.serial_no): (row.serial_no, row.updated_at) for row in (
                await connection.execute(select(table.c.serial_no, table.c.data, table.c.updated_at)))}
        self.assertEqual({legacy: serial for legacy, (serial, _) in result.items()}, {
            "BUG8D8B25AD93FA4F5F9694": "BUG20261024001",
            "BUG00000000000000000A0B": "BUG20261025001",
            "BUG76197D1B1E7247D9B7EC": "BUG20261025002",
            "BUG1B85B2CB8B204546AA57": "BUG20261026002",
            "BUG26B4DC9A60A54720BA1E": "BUG20261026003",
            "BUG855D1A2F448043179850": "BUG20261026004",
            "BUG20261026001": "BUG20261026001",
            "BUGAAAAAAAAAAAAAAAAAAAA": "BUGAAAAAAAAAAAAAAAAAAAA",
        })
        # “最近更新”不因改号变化；页面信息等原有字段保留。
        self.assertEqual(result["BUG855D1A2F448043179850"][1].replace(tzinfo=None), datetime(2026, 10, 26, 9, 2))

        listing = await self.client.get("/api/v1/feedback", params={"keyword": "BUG855D1A2F"})
        self.assertEqual(listing.status_code, 200, listing.text)
        [found] = listing.json()["items"]
        self.assertEqual((found["serial_no"], found["legacy_serial_no"], found["page"]),
                         ("BUG20261026004", "BUG855D1A2F448043179850", "案件详情"))
        # 改号后当天新提交的问题接着往下编。
        async with self.sessions() as db:
            day = datetime(2026, 10, 26, 20, 0, tzinfo=feedback.FEEDBACK_TZ)
            self.assertEqual(await feedback._next_feedback_serial(db, now=day), "BUG20261026005")


if __name__ == "__main__":
    unittest.main()

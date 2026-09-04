"""9.2 row 4: dashboard refund count, case-participant scope, and mutations."""

import unittest
from xml.etree import ElementTree

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app, dashboard
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "codex-92-r4-admin", "role": "admin", "display_name": "管理者", "department": "测试部"}
MEMBER = {"username": "codex-92-r4-member", "role": "user", "display_name": "案件成员", "department": "测试部"}
OUTSIDER = {"username": "codex-92-r4-outsider", "role": "user", "display_name": "同部门非成员", "department": "测试部"}
EXCEL_NS = "{urn:schemas-microsoft-com:office:spreadsheet}"


class DashboardRefundWorkbench92Row4Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name=ADMIN["display_name"], department="测试部", role="admin", password_hash="test", is_active=True),
                User(username=MEMBER["username"], display_name=MEMBER["display_name"], department="测试部", role="user", password_hash="test", is_active=True),
                User(username=OUTSIDER["username"], display_name=OUTSIDER["display_name"], department="测试部", role="user", password_hash="test", is_active=True),
            ])
            related_case = BusinessRecord(
                module="case", serial_no="CODEX-92-R4-CASE-RELATED", title="相关案件",
                customer="相关客户", status="一审准备材料", owner="other", department="测试部",
                data={
                    "case_team_usernames": [MEMBER["username"]], "plaintiff": "相关原告",
                    "opponent": "相关被告", "court_case_no": "沪测01", "court_name": "测试法院",
                    "assistant": MEMBER["username"], "hearing_lawyer": "开庭律师", "case_stage": "一审准备材料",
                },
            )
            unrelated_case = BusinessRecord(
                module="case", serial_no="CODEX-92-R4-CASE-UNRELATED", title="同部门无关案件",
                customer="无关客户", status="一审准备材料", owner="other", department="测试部",
                data={"case_team_usernames": ["someone-else"], "court_name": "其他法院"},
            )
            db.add_all([related_case, unrelated_case])
            await db.flush()
            related_fee = BusinessRecord(
                module="finance", serial_no="CODEX-92-R4-FEE-RELATED", title="相关案件诉讼费",
                customer="相关客户", status="已付款", owner="finance", department="测试部",
                data={
                    "case_id": related_case.id, "case_no": related_case.serial_no,
                    "fee_type": "官方费用", "amount": 4300, "paid_date": "2026-08-01",
                    "legacy_case_fee_id": 920401,
                    "legacy_record": {
                        "RefundAmount": 2800, "RefundedAmount": 0, "RefundStatus": 10,
                        "RefundStatus10StartTime": "2026-08-02", "CreateTime": "2026-08-01",
                    },
                },
            )
            unrelated_fee = BusinessRecord(
                module="finance", serial_no="CODEX-92-R4-FEE-UNRELATED", title="无关案件诉讼费",
                customer="无关客户", status="已付款", owner="finance", department="测试部",
                data={
                    "case_id": unrelated_case.id, "case_no": unrelated_case.serial_no,
                    "fee_type": "官方费用", "amount": 5800, "paid_date": "2026-08-03",
                    "refund_requested_amount": 2900, "refunded_amount": 0,
                    "refund_status": "R20", "refund_status_started_at": "2026-08-04",
                },
            )
            settled_fee = BusinessRecord(
                module="finance", serial_no="CODEX-92-R4-FEE-SETTLED", title="已退完费用",
                customer="相关客户", status="已付款", owner="finance", department="测试部",
                data={
                    "case_id": related_case.id, "case_no": related_case.serial_no,
                    "fee_type": "官方费用", "amount": 100,
                    "refund_requested_amount": 100, "refunded_amount": 100,
                },
            )
            db.add_all([related_fee, unrelated_fee, settled_fee])
            await db.flush()
            self.related_case_id = related_case.id
            self.related_fee_id = related_fee.id
            self.unrelated_fee_id = unrelated_fee.id
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row4.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_admin_count_list_filters_and_export_share_one_case_fee_set(self):
        response = await self.client.get(f"{API}/finance/case-fees/refunds", params={"court_name": "测试", "refund_status": "准备材料"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total"], 1)
        row = response.json()["items"][0]
        self.assertEqual(row["serial_no"], "CODEX-92-R4-FEE-RELATED")
        self.assertEqual(row["data"]["refund_requested_amount"], 2800)
        self.assertEqual(row["data"]["plaintiff"], "相关原告")
        self.assertEqual(row["data"]["refund_status"], "R10")
        async with self.sessions() as db:
            metrics = {item["key"]: item for item in (await dashboard(ADMIN, db))["metrics"]}
        self.assertEqual(metrics["refund-pending"]["value"], "2件")
        self.assertEqual(metrics["refund-pending"]["route"], "finance-refund")

        exported = await self.client.get(f"{API}/finance/case-fees/refunds/export", params={"ids": str(self.related_fee_id)})
        self.assertEqual(exported.status_code, status.HTTP_200_OK)
        root = ElementTree.fromstring(exported.content)
        rows = [[cell.text or "" for cell in row.findall(f"{EXCEL_NS}Cell/{EXCEL_NS}Data")] for row in root.findall(f".//{EXCEL_NS}Row")]
        self.assertEqual(rows[0][:4], ["案号", "原告", "被告", "案件阶段"])
        self.assertIn("CODEX-92-R4-CASE-RELATED", rows[1])

    async def test_department_user_sees_only_cases_where_they_are_related(self):
        app.dependency_overrides[current_identity] = lambda: MEMBER
        response = await self.client.get(f"{API}/finance/case-fees/refunds")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({row["id"] for row in response.json()["items"]}, {self.related_fee_id})
        async with self.sessions() as db:
            metrics = {item["key"]: item for item in (await dashboard(MEMBER, db))["metrics"]}
        self.assertEqual(metrics["refund-pending"]["value"], "1件")

        app.dependency_overrides[current_identity] = lambda: OUTSIDER
        outsider = await self.client.get(f"{API}/finance/case-fees/refunds")
        self.assertEqual(outsider.status_code, status.HTTP_200_OK)
        self.assertEqual(outsider.json()["total"], 0)

    async def test_batch_preflight_is_atomic_and_status_logs_persist(self):
        app.dependency_overrides[current_identity] = lambda: MEMBER
        denied_batch = await self.client.post(
            f"{API}/finance/case-fees/refunds/status",
            json={"ids": [self.related_fee_id, self.unrelated_fee_id], "status": "R20", "comment": "批量跟进"},
        )
        self.assertEqual(denied_batch.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        async with self.sessions() as db:
            related = await db.get(BusinessRecord, self.related_fee_id)
            self.assertNotEqual((related.data or {}).get("refund_status"), "R20")

        changed = await self.client.post(
            f"{API}/finance/case-fees/refunds/status",
            json={"ids": [self.related_fee_id], "status": "R20", "comment": "已提交法院"},
        )
        self.assertEqual(changed.status_code, status.HTTP_200_OK)
        log = await self.client.post(
            f"{API}/finance/case-fees/refunds/logs",
            json={"ids": [self.related_fee_id], "kind": "court", "content": "法院已收材料"},
        )
        self.assertEqual(log.status_code, status.HTTP_200_OK)
        forbidden = await self.client.post(
            f"{API}/finance/case-fees/refunds/status",
            json={"ids": [self.related_fee_id], "status": "R100"},
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        async with self.sessions() as db:
            related = await db.get(BusinessRecord, self.related_fee_id)
            self.assertEqual((related.data or {})["refund_status"], "R20")
            actions = set((await db.scalars(select(WorkflowEvent.action).where(
                WorkflowEvent.record_id.in_((self.related_fee_id, self.related_case_id))
            ))).all())
        self.assertTrue({"修改退费进度", "添加法院退费日志", "新增案件日志"}.issubset(actions))

        app.dependency_overrides[current_identity] = lambda: ADMIN
        marked = await self.client.post(
            f"{API}/finance/case-fees/refunds/status",
            json={"ids": [self.related_fee_id], "status": "R100", "comment": "不再办理"},
        )
        self.assertEqual(marked.status_code, status.HTTP_200_OK)
        listed = await self.client.get(f"{API}/finance/case-fees/refunds")
        self.assertNotIn(self.related_fee_id, {row["id"] for row in listed.json()["items"]})

    async def test_case_fee_endpoint_marks_refund_not_required_with_audit_fields(self):
        app.dependency_overrides[current_identity] = lambda: MEMBER
        forbidden = await self.client.post(
            f"{API}/finance/fees/{self.related_fee_id}/mark-refund-not-required",
            json={"comment": "无权限尝试"},
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        app.dependency_overrides[current_identity] = lambda: ADMIN
        marked = await self.client.post(
            f"{API}/finance/fees/{self.related_fee_id}/mark-refund-not-required",
            json={"comment": "法院确认不再办理"},
        )
        self.assertEqual(marked.status_code, status.HTTP_200_OK)
        result = marked.json()
        self.assertEqual(result["status"], "已付款")
        self.assertEqual(result["data"]["refund_status"], "R100")
        self.assertEqual(result["data"]["refund_status_label"], "不再办理退费")
        self.assertEqual(result["data"]["refund_not_required_by"], ADMIN["username"])
        self.assertEqual(result["data"]["refund_not_required_comment"], "法院确认不再办理")
        self.assertTrue(result["data"]["refund_not_required_at"])

        async with self.sessions() as db:
            event = await db.scalar(select(WorkflowEvent).where(
                WorkflowEvent.record_id == self.related_fee_id,
                WorkflowEvent.action == "标记不再办理退费",
            ))
        self.assertIsNotNone(event)
        self.assertEqual(event.from_status, "准备材料")
        self.assertEqual(event.to_status, "不再办理退费")
        self.assertEqual(event.operator, ADMIN["username"])
        self.assertEqual(event.comment, "法院确认不再办理")

    async def test_case_fee_endpoint_rejects_fee_without_refund_context_without_writing(self):
        async with self.sessions() as db:
            plain_fee = BusinessRecord(
                module="finance", serial_no="CODEX-92-R4-FEE-NO-REFUND", title="无退费流程费用",
                customer="相关客户", status="已付款", owner=ADMIN["username"], department="测试部",
                data={
                    "case_id": self.related_case_id, "case_no": "CODEX-92-R4-CASE-RELATED",
                    "fee_type": "官方费用", "amount": 300,
                },
            )
            db.add(plain_fee)
            await db.commit()
            plain_fee_id = plain_fee.id

        rejected = await self.client.post(
            f"{API}/finance/fees/{plain_fee_id}/mark-refund-not-required",
            json={"comment": "不应写入"},
        )
        self.assertEqual(rejected.status_code, status.HTTP_409_CONFLICT)

        async with self.sessions() as db:
            unchanged = await db.get(BusinessRecord, plain_fee_id)
            self.assertNotIn("refund_status", unchanged.data or {})
            events = list((await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == plain_fee_id,
            ))).all())
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()

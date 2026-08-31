"""Backend contract tests for the concrete IPR case-center gap batch.

Covers: legacy IPR list projection fields, multi-condition search, Excel and
Word exports, the case fee tab plus fee operations, locked application-file
packages, and in-progress case updates with cross-module links.
"""

import io
import shutil
import tempfile
import unittest
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from docx import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, IncomingPayment, IprCaseReminder, SystemParameter, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "ipr-c-admin",
    "role": "admin",
    "display_name": "IPR C Admin",
    "department": "上海分所",
}
BASE_TIME = datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc)


class IprConcreteCBackendContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.upload_root = Path(tempfile.mkdtemp(prefix="codex-ipr-c-"))
        from app import main as main_module
        self.main_module = main_module
        self.original_upload_root = main_module.UPLOAD_ROOT
        main_module.UPLOAD_ROOT = self.upload_root

        async with self.sessions() as db:
            db.add(User(
                username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                department=IDENTITY["department"], role="admin", password_hash="test", is_active=True,
            ))
            payment_type = SystemParameter(
                category="payment_type", code="CODEX-IPR-C-PAYEE", name="官费",
                extra={"nature": "官费", "payee": "专利局", "account_bank": "知识产权银行", "account": "IPR-C-ACCOUNT"},
                sort_order=1, is_active=True, created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
            )
            db.add(payment_type)
            await db.flush()
            self.payment_type_id = payment_type.id
            customer = BusinessRecord(
                module="customer", serial_no="CODEX-IPR-C-CUSTOMER-001", title="IPR C 客户",
                customer="", status="合作中", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={},
            )
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-IPR-C-CONTRACT-001", title="IPR C 合同",
                customer="IPR C 客户", status="审批通过", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={},
            )
            db.add_all([customer, contract])
            await db.flush()
            self.customer_id = customer.id
            self.contract_id = contract.id

            cases = []
            case_a_data = {
                "case_kind": "专利", "case_type": "专利申请", "application_no": "APP-C-001",
                "application_type": "发明", "applicant": "权利人A", "case_manager": "负责人A",
                "application_date": "2026-01-15", "deadline": "2026-01-20",
                "case_phase": "申请阶段", "acceptance_date": "2026-01-16",
                "case_source": "客户转介", "source_date": "2026-01-10",
                "agent": "代理人A", "writer": "撰稿人A", "submitter": "提交人A",
                "submit_date": "2026-01-12", "inventor": "发明人A",
                "annual_fee_year": 1, "annual_fee_monitoring": True, "rate": 0.5,
            }
            case_a = BusinessRecord(
                module="ipr_case", serial_no="IPR-C-001", title="IPR C 专利案件",
                customer="IPR C 客户", status="在办", owner=IDENTITY["username"],
                department=IDENTITY["department"], data=case_a_data,
                created_at=BASE_TIME, updated_at=BASE_TIME,
            )
            case_b = BusinessRecord(
                module="ipr_case", serial_no="IPR-C-002", title="IPR C 商标案件",
                customer="IPR C 客户", status="在办", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={
                    "case_kind": "商标", "case_type": "商标注册", "application_no": "APP-C-002",
                    "application_date": "2026-06-30", "deadline": "2026-06-12",
                    "case_manager": "负责人B", "annual_fee_year": 2,
                    "annual_fee_monitoring": False, "rate": 0.3,
                },
                created_at=BASE_TIME - timedelta(days=1), updated_at=BASE_TIME - timedelta(days=1),
            )
            case_c = BusinessRecord(
                module="ipr_case", serial_no="IPR-C-003", title="IPR C 草稿案件",
                customer="IPR C 客户", status="草稿", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={
                    "case_kind": "专利", "application_no": "APP-C-003",
                    "application_date": "2025-01-15", "deadline": "2025-12-31",
                    "case_manager": "负责人C",
                },
                created_at=BASE_TIME - timedelta(days=2), updated_at=BASE_TIME - timedelta(days=2),
            )
            db.add_all([case_a, case_b, case_c])
            await db.flush()
            self.case_a_id = case_a.id
            self.case_b_id = case_b.id
            self.case_c_id = case_c.id
            cases = [case_a, case_b, case_c]

            db.add_all([
                IprCaseReminder(
                    case_record_id=case_a.id, event_type_id=4, event_type="缴纳年费",
                    reminder_date=date(2026, 1, 19), deadline=date(2026, 1, 20),
                    content="年费提醒", creator=IDENTITY["username"],
                ),
                IprCaseReminder(
                    case_record_id=case_b.id, event_type_id=15, event_type="商标续展",
                    reminder_date=date(2026, 6, 10), deadline=date(2026, 6, 12),
                    content="续展提醒", creator=IDENTITY["username"],
                ),
            ])

            fee_data_base = {
                "case_id": case_a.id, "case_no": case_a.serial_no, "case_kind": "专利",
                "payment_status": "创建待提交", "contract_id": None, "contract_no": "",
                "locked": False, "is_locked": False,
            }
            fee1 = BusinessRecord(
                module="finance", serial_no="CODEX-IPR-C-FEE-001", title="IPR C 官方费用",
                customer="IPR C 客户", status="草稿", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={**fee_data_base, "amount": 1000.0, "fee_type": "官方费用"},
            )
            fee2 = BusinessRecord(
                module="finance", serial_no="CODEX-IPR-C-FEE-002", title="IPR C 代理费",
                customer="IPR C 客户", status="草稿", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={**fee_data_base, "amount": 2000.0, "fee_type": "代理费", "locked": True, "is_locked": True},
            )
            fee3 = BusinessRecord(
                module="finance", serial_no="CODEX-IPR-C-FEE-003", title="IPR C 已审批费用",
                customer="IPR C 客户", status="已审批", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={**fee_data_base, "amount": 500.0, "fee_type": "其他费用"},
            )
            db.add_all([fee1, fee2, fee3])
            await db.flush()
            self.fee1_id = fee1.id
            self.fee2_id = fee2.id
            self.fee3_id = fee3.id

            payment = BusinessRecord(
                module="contract_payment", serial_no="CODEX-IPR-C-PAY-001", title="IPR C 付款记录",
                customer="IPR C 客户", status="待审批", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"case_id": case_a.id, "case_no": case_a.serial_no},
            )
            db.add(payment)
            await db.flush()
            self.payment_id = payment.id

            source_path = self.upload_root / "ipr-c-source.pdf"
            source_path.write_bytes(b"ipr-c-source-content")
            source_attachment = FileAttachment(
                record_id=case_a.id, category="IPR C 源文档", file_type_code="",
                original_name="ipr-c-source.pdf", stored_name="ipr-c-source.pdf",
                content_type="application/pdf", size=len(b"ipr-c-source-content"),
                path=str(source_path), uploader=IDENTITY["username"], document_date=date(2026, 8, 5),
            )
            db.add(source_attachment)
            await db.flush()
            self.source_attachment_id = source_attachment.id
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://ipr-c.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.main_module.UPLOAD_ROOT = self.original_upload_root
        shutil.rmtree(self.upload_root, ignore_errors=True)
        await self.engine.dispose()

    async def test_list_projects_legacy_fields_and_multi_condition_search(self):
        response = await self.client.get(f"{API}/ipr/cases", params={"keyword": "APP-C-001"})
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        item = payload["items"][0]
        self.assertEqual(item["case_phase"], "申请阶段")
        self.assertEqual(item["acceptance_date"], "2026-01-16")
        self.assertEqual(item["case_source"], "客户转介")
        self.assertEqual(item["source_date"], "2026-01-10")
        self.assertEqual(item["agent"], "代理人A")
        self.assertEqual(item["writer"], "撰稿人A")
        self.assertEqual(item["handler"], "负责人A")
        self.assertEqual(item["submitter"], "提交人A")
        self.assertEqual(item["submit_date"], "2026-01-12")
        self.assertEqual(item["inventor"], "发明人A")
        self.assertEqual(item["deadline"], "2026-01-20")

        by_type = await self.client.get(f"{API}/ipr/cases", params={"case_type": "专利申请"})
        self.assertEqual(by_type.json()["total"], 1)
        self.assertEqual(by_type.json()["items"][0]["id"], self.case_a_id)

        by_phase = await self.client.get(f"{API}/ipr/cases", params={"case_phase": "申请阶段"})
        self.assertEqual(by_phase.json()["total"], 1)
        self.assertEqual(by_phase.json()["items"][0]["id"], self.case_a_id)

        by_reminder = await self.client.get(f"{API}/ipr/cases", params={"reminder_type": "缴纳年费"})
        self.assertEqual(by_reminder.json()["total"], 1)
        self.assertEqual(by_reminder.json()["items"][0]["id"], self.case_a_id)

        by_date = await self.client.get(
            f"{API}/ipr/cases", params={"date_from": "2026-01-01", "date_to": "2026-01-31"}
        )
        self.assertEqual(by_date.json()["total"], 1)
        self.assertEqual(by_date.json()["items"][0]["id"], self.case_a_id)

        by_month_day = await self.client.get(
            f"{API}/ipr/cases", params={"search_by_month_day": "true", "month_day": "01-15"}
        )
        self.assertEqual(by_month_day.status_code, 200, by_month_day.text)
        serials = {item["serial_no"] for item in by_month_day.json()["items"]}
        self.assertEqual(serials, {"IPR-C-001", "IPR-C-003"})

        invalid_month = await self.client.get(
            f"{API}/ipr/cases", params={"search_by_month_day": "true", "month_day": "2026-01-15"}
        )
        self.assertEqual(invalid_month.status_code, 422)
        missing_month = await self.client.get(f"{API}/ipr/cases", params={"search_by_month_day": "true"})
        self.assertEqual(missing_month.status_code, 422)
        bad_range = await self.client.get(
            f"{API}/ipr/cases", params={"date_from": "2026-02-01", "date_to": "2026-01-01"}
        )
        self.assertEqual(bad_range.status_code, 422)

    async def test_excel_and_word_exports_are_real_files_with_legacy_columns(self):
        excel = await self.client.get(f"{API}/ipr/cases/export/excel", params={"case_kind": "专利"})
        self.assertEqual(excel.status_code, 200, excel.text)
        self.assertIn("vnd.ms-excel", excel.headers["content-type"])
        excel_text = excel.content.decode("utf-8")
        self.assertIn("案件编号", excel_text)
        self.assertIn("申请人/权利人", excel_text)
        self.assertIn("IPR-C-001", excel_text)

        word = await self.client.get(f"{API}/ipr/cases/export/word", params={"case_kind": "专利"})
        self.assertEqual(word.status_code, 200, word.text)
        self.assertIn("wordprocessingml.document", word.headers["content-type"])
        self.assertTrue(word.content.startswith(b"PK"))
        document = Document(io.BytesIO(word.content))
        cells = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
        self.assertIn("案件编号", cells)
        self.assertIn("IPR-C-001", cells)

    async def test_fee_tab_lists_paginates_and_creates_draft_fee(self):
        first = await self.client.get(f"{API}/ipr/cases/{self.case_a_id}/fees", params={"page": 1, "page_size": 2})
        self.assertEqual(first.status_code, 200, first.text)
        payload = first.json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(payload["pages"], 2)
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["totals"]["amount"], 3500.0)

        created = await self.client.post(
            f"{API}/ipr/cases/{self.case_a_id}/fees",
            json={"title": "IPR C 新建费用", "amount": 888.0, "fee_type": "官方费用", "handler": ""},
        )
        self.assertEqual(created.status_code, 201, created.text)
        created_data = created.json()["data"]
        self.assertEqual(created_data["case_id"], self.case_a_id)
        self.assertEqual(created_data["case_no"], "IPR-C-001")
        self.assertEqual(created_data["payment_status"], "创建待提交")
        self.assertEqual(created_data["is_locked"], False)

        after = await self.client.get(f"{API}/ipr/cases/{self.case_a_id}/fees")
        self.assertEqual(after.json()["total"], 4)

    async def test_fee_invoice_payment_arrival_unlock_and_delete(self):
        created = await self.client.post(
            f"{API}/ipr/cases/{self.case_a_id}/fees",
            json={"title": "IPR C 操作费用", "amount": 600.0, "fee_type": "官方费用", "handler": ""},
        )
        self.assertEqual(created.status_code, 201, created.text)
        fee_id = created.json()["id"]

        invoice = await self.client.post(
            f"{API}/ipr/cases/{self.case_a_id}/fees/{fee_id}/invoice",
            json={
                "customer": "IPR C 客户", "amount": 600.0, "invoice_title": "IPR C 客户",
                "taxpayer_id": "91310000TEST", "email": "ipr@example.com",
            },
        )
        self.assertEqual(invoice.status_code, 201, invoice.text)
        invoice_body = invoice.json()
        self.assertEqual(invoice_body["module"], "invoice")
        self.assertEqual(invoice_body["data"]["case_fee_ids"], [fee_id])
        self.assertEqual(invoice_body["data"]["case_no"], "IPR-C-001")

        payment = await self.client.post(
            f"{API}/ipr/cases/{self.case_a_id}/fees/{fee_id}/payment-application",
            json={"payment_type_id": self.payment_type_id, "application_date": "2026-08-05", "remark": "test"},
        )
        self.assertEqual(payment.status_code, 201, payment.text)
        payment_body = payment.json()
        self.assertEqual(payment_body["module"], "contract_payment")
        self.assertEqual(payment_body["data"]["fee_id"], fee_id)
        self.assertEqual(payment_body["data"]["payment_type_id"], self.payment_type_id)
        self.assertEqual(payment_body["data"]["payee"], "专利局")
        rows = (await self.client.get(f"{API}/ipr/cases/{self.case_a_id}/fees")).json()["items"]
        row = next(item for item in rows if item["id"] == fee_id)
        self.assertEqual(row["data"]["payment_status"], "待审批")
        self.assertEqual(row["data"]["payment_application_no"], payment_body["serial_no"])

        arrival = await self.client.post(
            f"{API}/ipr/cases/{self.case_a_id}/fees/{fee_id}/arrival",
            json={
                "received_date": "2026-08-05", "amount": 600.0, "payer_name": "IPR C 付款人",
                "bank_reference": "CODEX-IPR-C-BANK-001", "remark": "arrival test",
            },
        )
        self.assertEqual(arrival.status_code, 201, arrival.text)
        arrival_row = arrival.json()
        self.assertEqual(arrival_row["data"]["cashed_amount"], 600.0)
        self.assertEqual(arrival_row["data"]["cashed_date"], "2026-08-05")
        async with self.sessions() as db:
            incoming = await db.scalar(select(IncomingPayment).where(IncomingPayment.bank_reference == "CODEX-IPR-C-BANK-001"))
            self.assertIsNotNone(incoming)
            self.assertEqual(incoming.allocations[0]["fee_id"], fee_id)

        unlocked = await self.client.post(f"{API}/ipr/cases/{self.case_a_id}/fees/{self.fee2_id}/unlock", json={"comment": "unlock"})
        self.assertEqual(unlocked.status_code, 200, unlocked.text)
        self.assertEqual(unlocked.json()["data"]["is_locked"], False)

        deleted = await self.client.delete(f"{API}/ipr/cases/{self.case_a_id}/fees/{self.fee1_id}")
        self.assertEqual(deleted.status_code, 204, deleted.text)
        after_delete = (await self.client.get(f"{API}/ipr/cases/{self.case_a_id}/fees")).json()
        self.assertNotIn(self.fee1_id, [item["id"] for item in after_delete["items"]])

        non_draft = await self.client.delete(f"{API}/ipr/cases/{self.case_a_id}/fees/{self.fee3_id}")
        self.assertEqual(non_draft.status_code, 409)

    async def test_file_generate_package_locks_and_delete_guard(self):
        generate = await self.client.post(
            f"{API}/ipr/cases/{self.case_a_id}/files/{self.source_attachment_id}/generate-application"
        )
        self.assertEqual(generate.status_code, 201, generate.text)
        package = generate.json()
        self.assertEqual(package["category"], "知识产权申请文件包")
        self.assertTrue(package["is_locked"])
        self.assertEqual(package["locked_by"], IDENTITY["username"])
        async with self.sessions() as db:
            package_row = await db.get(FileAttachment, package["id"])
            self.assertIsNotNone(package_row)
            package_path = Path(package_row.path)
        self.assertTrue(package_path.is_file())
        with zipfile.ZipFile(package_path, "r") as archive:
            self.assertIn("ipr-c-source.pdf", archive.namelist())
            self.assertEqual(archive.read("ipr-c-source.pdf"), b"ipr-c-source-content")

        blocked_delete = await self.client.delete(
            f"{API}/ipr/cases/{self.case_a_id}/files/{self.source_attachment_id}"
        )
        self.assertEqual(blocked_delete.status_code, 409)

        unlocked = await self.client.post(
            f"{API}/ipr/cases/{self.case_a_id}/files/{self.source_attachment_id}/unlock"
        )
        self.assertEqual(unlocked.status_code, 200, unlocked.text)
        self.assertFalse(unlocked.json()["is_locked"])

        deleted = await self.client.delete(f"{API}/ipr/cases/{self.case_a_id}/files/{self.source_attachment_id}")
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertFalse(self.upload_root.joinpath("ipr-c-source.pdf").exists())

    async def test_in_progress_update_persists_fields_and_cross_module_links(self):
        updated = await self.client.patch(
            f"{API}/ipr/cases/{self.case_a_id}",
            json={
                "case_phase": "实质审查", "acceptance_date": "2026-02-01",
                "case_source": "展会", "source_date": "2026-01-25",
                "agent": "代理人B", "writer": "撰稿人B", "submitter": "提交人B",
                "inventor": "发明人B", "contract_record_id": self.contract_id,
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        item = updated.json()
        self.assertEqual(item["case_phase"], "实质审查")
        self.assertEqual(item["acceptance_date"], "2026-02-01")
        self.assertEqual(item["case_source"], "展会")
        self.assertEqual(item["agent"], "代理人B")
        self.assertEqual(item["contract_record_id"], self.contract_id)
        self.assertEqual(item["contract_no"], "CODEX-IPR-C-CONTRACT-001")

        linked = await self.client.put(
            f"{API}/ipr/cases/{self.case_a_id}/links",
            json={"contract_record_id": self.contract_id, "payment_record_id": self.payment_id},
        )
        self.assertEqual(linked.status_code, 200, linked.text)
        linked_data = linked.json()["data"]
        self.assertEqual(linked_data["contract_record_id"], self.contract_id)
        self.assertEqual(linked_data["contract_no"], "CODEX-IPR-C-CONTRACT-001")
        self.assertEqual(linked_data["payment_record_id"], self.payment_id)
        self.assertEqual(linked_data["payment_no"], "CODEX-IPR-C-PAY-001")

        invalid_link = await self.client.post(
            f"{API}/ipr/cases/{self.case_c_id}/links",
            json={"contract_record_id": self.payment_id},
        )
        self.assertEqual(invalid_link.status_code, 404, invalid_link.text)

        async with self.sessions() as db:
            events = (await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == self.case_a_id,
                WorkflowEvent.action == "修改知识产权案件基本信息",
            ))).all()
            self.assertTrue(events)


if __name__ == "__main__":
    unittest.main()

"""9.22 rows 2-3: case conflict and receipt links use isolated data."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.clue_conflicts import clue_conflicts
from app.core.cases import _urgent_case_ids
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, SystemParameter, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "CODEX-0922-reviewer", "role": "admin", "role_ids": ["admin"], "department": "测试部"}


class Rows0922Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=IDENTITY["username"], display_name="测试审核人", role="admin",
                     role_ids=["admin"], department="测试部", password_hash="unused", is_active=True),
                SystemParameter(category="customer_type", code="PARTY", name="当事人", is_active=True),
            ])
            await db.commit()
        self.old_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://rows0922.test")
        self.temporary = tempfile.TemporaryDirectory(prefix="CODEX-0922-receipts-")
        self.root_patch = patch("app.areas.finance.receipt_files.UPLOAD_ROOT", Path(self.temporary.name))
        self.root_patch.start()
        self.storage_patch = patch("app.core.storage.UPLOAD_ROOT", Path(self.temporary.name))
        self.storage_patch.start()

    async def asyncTearDown(self):
        self.root_patch.stop()
        self.storage_patch.stop()
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.old_overrides)
        await self.engine.dispose()
        self.temporary.cleanup()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    @staticmethod
    def record(module, serial, customer="CODEX-0922-holder", data=None):
        return BusinessRecord(module=module, serial_no=serial, title=serial, customer=customer,
                              owner=IDENTITY["username"], department="测试部", status="有效", data=data or {})

    async def test_urgent_cases_only_include_my_open_tasks_due_within_fifteen_days(self):
        today = date(2026, 9, 25)
        async with self.sessions() as db:
            cases = [self.record("case", f"CODEX-0922-urgent-{number}") for number in range(5)]
            db.add_all(cases)
            await db.flush()
            tasks = []
            for index, days in enumerate((15, 16, -1, 1, 1)):
                task = self.record("task", f"CODEX-0922-task-{index}", data={
                    "source": "案件任务", "case_id": cases[index].id,
                    "deadline": (today + timedelta(days=days)).isoformat(),
                })
                task.status = "进行中" if index != 3 else "已完成"
                if index == 4:
                    task.owner = "CODEX-0922-other"
                tasks.append(task)
            db.add_all(tasks)
            await db.commit()
            urgent = await _urgent_case_ids(cases, db, IDENTITY["username"], as_of=today)
            self.assertEqual(urgent, {cases[0].id, cases[2].id})

    async def test_customer_generic_edit_rejects_duplicate_identity_and_persists_valid_change(self):
        async with self.sessions() as db:
            first = self.record("customer", "CODEX-0922-customer-1", data={
                "organization_type": "公司企业", "credit_code": "913100000000000001",
            })
            second = self.record("customer", "CODEX-0922-customer-2", data={
                "organization_type": "公司企业", "credit_code": "913100000000000002",
            })
            db.add_all([first, second])
            await db.commit()
            second_id = second.id
        duplicate = await self.client.patch(f"{API}/records/{second_id}", json={"data": {
            "organization_type": "公司企业", "credit_code": "913100000000000001",
        }})
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        valid = await self.client.patch(f"{API}/records/{second_id}", json={"data": {
            "organization_type": "公司企业", "credit_code": "913100000000000003",
        }})
        self.assertEqual(valid.status_code, 200, valid.text)
        async with self.sessions() as db:
            saved = await db.get(BusinessRecord, second_id)
            self.assertEqual(saved.data["credit_code"], "913100000000000003")

    async def test_official_receipt_requires_both_case_numbers_and_reaches_company_files(self):
        serial = "CODEX-0922-receipt-case"
        court_no = "（2026）沪0101民初1号"
        async with self.sessions() as db:
            case = self.record("case", serial, data={"court_case_no": court_no})
            db.add(case)
            await db.commit()
            case_id = case.id
        with patch("app.areas.aws.router.UPLOAD_ROOT", Path(self.temporary.name)):
            wrong = await self.client.post(
                f"{API}/documents/official/upload",
                data={"document_date": "2026-09-25"},
                files={"file": (f"{serial}_（2026）沪0101民初2号.pdf", b"pdf", "application/pdf")},
            )
            self.assertEqual(wrong.status_code, 422, wrong.text)
            accepted = await self.client.post(
                f"{API}/documents/official/upload",
                data={"document_date": "2026-09-25"},
                files={"file": (f"{serial}_{court_no}.pdf", b"pdf", "application/pdf")},
            )
        self.assertEqual(accepted.status_code, 201, accepted.text)
        attachment = accepted.json()["attachment"]
        self.assertEqual(attachment["record_id"], case_id)
        self.assertEqual(attachment["category"], "官方收文")
        for scope in ("official", "company"):
            listing = await self.client.get(f"{API}/documents/receipts", params={"scope": scope})
            self.assertEqual(listing.status_code, 200, listing.text)
            self.assertEqual(listing.json()["total"], 1)
        local_file = Path(self.temporary.name) / "CODEX-0922-notice.pdf"
        local_file.write_bytes(b"pdf")
        async with self.sessions() as db:
            db.add(FileAttachment(
                record_id=case_id, category="案件文档", original_name="CODEX-0922-通知书.pdf",
                stored_name=local_file.name, content_type="application/pdf", size=3,
                path=str(local_file), uploader=IDENTITY["username"], remark="",
            ))
            await db.commit()
        mine = await self.client.get(f"{API}/documents/receipts", params={"scope": "mine"})
        company = await self.client.get(f"{API}/documents/receipts", params={"scope": "company"})
        self.assertEqual(mine.json()["total"], 1)
        self.assertEqual(company.json()["total"], 2)

    async def test_conflict_uses_current_defendant_and_same_holder(self):
        async with self.sessions() as db:
            clue = self.record("clue", "CODEX-0922-clue", data={
                "rights_holder_id": 41, "producer": "目标被告", "shop_name": "店铺甲",
            })
            matching_case = self.record("case", "CODEX-0922-case-match", data={
                "customer_id": 41, "defendants": ["目标被告"],
                "legacy_record": {"AppelleeNames": "过期被告"},
            })
            wrong_holder = self.record("case", "CODEX-0922-case-other", data={
                "customer_id": 42, "defendants": ["目标被告"],
            })
            old_case = self.record("case", "CODEX-0922-case-old", data={
                "customer_id": 41, "legacy_record": {"AppelleeNames": "目标被告"},
            })
            db.add_all([clue, matching_case, wrong_holder, old_case])
            await db.commit()
            result = await clue_conflicts(clue, db)
            self.assertEqual(result["cases"], ["CODEX-0922-case-match", "CODEX-0922-case-old"])
            self.assertTrue(result["case_search_available"])
            clue.data = {"rights_holder_id": 41, "shop_name": "店铺甲"}
            await db.commit()
            result = await clue_conflicts(clue, db)
            self.assertFalse(result["case_search_available"])
            self.assertEqual(result["cases"], [])

    async def test_detail_adds_defendant_with_identity_and_keeps_old_party(self):
        async with self.sessions() as db:
            case = self.record("case", "CODEX-0922-party-case", data={
                "case_type": "民事案件", "case_creation_step": "basic", "plaintiffs": ["旧原告"],
                "defendants": ["旧被告"], "plaintiff": "旧原告", "opponent": "旧被告", "customer_id": 41,
            })
            clue = self.record("clue", "CODEX-0922-party-clue", data={
                "rights_holder_id": 41, "producer": "目标被告",
            })
            db.add_all([case, clue])
            await db.commit()
            case_id = case.id
        payload = {"plaintiffs": ["旧原告"], "defendants": ["旧被告", "目标被告"],
                   "defendant_identities": [{"name": "目标被告", "organization_type": "公司企业",
                                             "identity_no": "913100000000000001"}]}
        result = await self.client.put(f"{API}/cases/{case_id}/litigants-detail", json=payload)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["data"]["defendants"], ["旧被告", "目标被告"])
        self.assertEqual(result.json()["data"]["case_creation_step"], "basic")
        async with self.sessions() as db:
            customer = await db.scalar(select(BusinessRecord).where(
                BusinessRecord.module == "customer", BusinessRecord.title == "目标被告",
            ))
            self.assertIsNotNone(customer)
            self.assertEqual(customer.data["credit_code"], "913100000000000001")
            matched = await clue_conflicts(clue, db)
            self.assertEqual(matched["cases"], ["CODEX-0922-party-case"])

    async def test_detail_requires_identity_for_new_defendant(self):
        async with self.sessions() as db:
            case = self.record("case", "CODEX-0922-name-only-case", data={
                "case_type": "民事案件", "case_creation_step": "basic",
                "plaintiffs": ["旧原告"], "defendants": ["旧被告"],
                "defendant": "旧被告", "customer_id": 41,
            })
            clue = self.record("clue", "CODEX-0922-name-only-clue", data={
                "rights_holder_id": 41, "producer": "新增被告",
            })
            db.add_all([case, clue])
            await db.commit()
            case_id = case.id
        payload = {"plaintiffs": ["旧原告"], "defendants": ["旧被告", "新增被告"]}
        creation = await self.client.put(f"{API}/cases/{case_id}/litigants", json=payload)
        self.assertEqual(creation.status_code, 422, creation.text)
        invalid = await self.client.put(f"{API}/cases/{case_id}/litigants-detail", json={
            **payload,
            "defendant_identities": [{
                "name": "新增被告", "organization_type": "公司企业", "identity_no": "111",
            }],
        })
        self.assertEqual(invalid.status_code, 422, invalid.text)
        missing = await self.client.put(f"{API}/cases/{case_id}/litigants-detail", json=payload)
        self.assertEqual(missing.status_code, 422, missing.text)
        detail = await self.client.put(f"{API}/cases/{case_id}/litigants-detail", json={
            **payload,
            "defendant_identities": [{
                "name": "新增被告", "organization_type": "公司企业", "identity_no": "913100000000000002",
            }],
        })
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["data"]["defendants"], payload["defendants"])
        self.assertEqual(detail.json()["data"]["opponent"], "旧被告、新增被告")
        async with self.sessions() as db:
            party = await db.scalar(select(BusinessRecord).where(
                BusinessRecord.module == "customer", BusinessRecord.title == "新增被告",
            ))
            self.assertIsNotNone(party)
            self.assertEqual(party.data["case_litigant_origin"]["case_id"], case_id)
            self.assertEqual(party.data["credit_code"], "913100000000000002")
            matched = await clue_conflicts(clue, db)
            self.assertEqual(matched["cases"], ["CODEX-0922-name-only-case"])

    async def test_receipt_upload_links_only_selected_fee(self):
        async with self.sessions() as db:
            case = self.record("case", "CODEX-0922-receipt-case", data={"case_type": "民事案件"})
            db.add(case)
            await db.flush()
            fees = [self.record("finance", f"CODEX-0922-fee-{index}", data={
                "case_id": case.id, "case_no": case.serial_no, "fee_type": "官方费用", "amount": 10,
            }) for index in (1, 2)]
            db.add_all(fees)
            await db.commit()
            fee_ids = [fee.id for fee in fees]
        response = await self.client.post(f"{API}/finance/receipt-files/batch",
                                          data={"fee_ids": str(fee_ids[0]), "bill_no": "CODEX-0922-bill",
                                                "bill_date": "2026-09-22"},
                                          files={"file": ("CODEX-0922-receipt.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")})
        self.assertEqual(response.status_code, 201, response.text)
        async with self.sessions() as db:
            selected, untouched = [await db.get(BusinessRecord, fee_id) for fee_id in fee_ids]
            self.assertEqual(len(selected.data["receipt_files"]), 1)
            self.assertNotIn("receipt_files", untouched.data)
            metadata = selected.data["receipt_files"][0]
            attachment = await db.get(FileAttachment, metadata["attachment_id"])
            self.assertEqual(attachment.record_id, selected.id)
            self.assertEqual(attachment.category, "案件票据文件")
            self.assertEqual(attachment.original_name, "CODEX-0922-receipt.pdf")
            self.assertEqual(metadata["bill_no"], "CODEX-0922-bill")
        listing = await self.client.get(f"{API}/attachments", params={
            "record_id": fee_ids[0], "category": "案件票据文件",
        })
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertEqual([item["id"] for item in listing.json()["items"]], [metadata["attachment_id"]])
        download = await self.client.get(f"{API}/attachments/{metadata['attachment_id']}/download")
        self.assertEqual(download.status_code, 200, download.text)
        self.assertEqual(download.content, b"%PDF-1.4\n%%EOF")


if __name__ == "__main__":
    unittest.main()

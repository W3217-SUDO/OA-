"""9.30 第15行：案件只读授权贯通任务与真实关联附件，不扩大独立入口。"""

import tempfile
import unittest
from pathlib import Path

import httpx
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, JobRole, RolePermission, User
from app.security import create_token
from app.core import storage


class CaseRelatedRead0930Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.files = tempfile.TemporaryDirectory(prefix="oa0930-case-read-")
        self.original_upload_root = storage.UPLOAD_ROOT
        storage.UPLOAD_ROOT = Path(self.files.name)
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(RolePermission(role="user", display_name="普通用户", data_scope="本人及共享数据", menu_keys=[], field_keys=[]))
            db.add_all([
                JobRole(code="FINANCE-SUPERVISOR", name="财务主管", permissions=["财务审批"], is_active=True),
                JobRole(code="LEGACY-ROLE-19", name="律所财务", permissions=[], is_active=True),
                JobRole(code="LEGACY-ROLE-4", name="行政流程", permissions=[], is_active=True),
                User(username="oa0930-owner", display_name="案件负责人", role="user", department="法务部", password_hash="x", is_active=True),
                User(username="oa0930-ordinary", display_name="普通人员", role="user", department="其他部门", password_hash="x", is_active=True),
                User(username="oa0930-case-menu", display_name="个人案件人员", role="user", department="其他部门", password_hash="x", profile={"permission_overrides": {"menu_keys": ["case-mine"]}}, is_active=True),
                User(username="oa0930-finance", display_name="财务人员", role="user", department="财务部", password_hash="x", profile={"permission_role_code": "FINANCE-SUPERVISOR"}, is_active=True),
                User(username="oa0930-finance-clerk", display_name="律所财务", role="user", department="财务部", password_hash="x", profile={"permission_role_code": "LEGACY-ROLE-19"}, is_active=True),
                User(username="oa0930-process", display_name="流程人员", role="user", department="行政流程部", password_hash="x", profile={"permission_role_code": "LEGACY-ROLE-4"}, is_active=True),
                User(username="oa0930-admin", display_name="管理员", role="admin", role_ids=["admin"], department="管理部", password_hash="x", is_active=True),
            ])
            customer = BusinessRecord(module="customer", serial_no="OA0930-CU", title="关联客户", customer="关联客户", owner="oa0930-owner", department="法务部", data={})
            contract = BusinessRecord(module="contract", serial_no="OA0930-CT", title="关联合同", customer="关联客户", owner="oa0930-owner", department="法务部", data={})
            unrelated = BusinessRecord(module="customer", serial_no="OA0930-OTHER-CU", title="无关客户", customer="无关客户", owner="oa0930-owner", department="法务部", data={})
            db.add_all([customer, contract, unrelated])
            await db.flush()
            source_case = BusinessRecord(module="case", serial_no="OA0930-SOURCE", title="来源案", customer="关联客户", owner="oa0930-owner", department="法务部", data={"customer_record_id": customer.id, "contract_record_id": contract.id})
            db.add(source_case)
            await db.flush()
            case = BusinessRecord(module="case", serial_no="OA0930-MAIN", title="主案", customer="关联客户", owner="oa0930-owner", department="法务部", data={
                "customer_record_id": customer.id, "customer_no": customer.serial_no,
                "contract_record_id": contract.id, "contract_no": contract.serial_no,
                "merged_sources": [{"id": source_case.id, "serial_no": source_case.serial_no, "data": source_case.data, "customer": source_case.customer}],
            })
            other_case = BusinessRecord(module="case", serial_no="OA0930-OTHER", title="无关案", customer="无关客户", owner="oa0930-owner", department="法务部", data={"customer_record_id": unrelated.id})
            db.add_all([case, other_case])
            await db.flush()
            clue = BusinessRecord(module="clue", serial_no="OA0930-CL", title="来源线索", customer="关联客户", owner="oa0930-owner", department="法务部", data={"case_id": case.id})
            task = BusinessRecord(module="task", serial_no="OA0930-TASK", title="案件任务", customer="关联客户", owner="oa0930-owner", department="法务部", data={"case_id": case.id})
            unrelated_task = BusinessRecord(module="task", serial_no="OA0930-OTHER-TASK", title="无关任务", customer="无关客户", owner="oa0930-owner", department="法务部", data={"case_id": other_case.id})
            db.add_all([clue, task, unrelated_task])
            await db.flush()
            evidence = BusinessRecord(module="evidence", serial_no="OA0930-EV", title="取证资料", customer="关联客户", owner="oa0930-owner", department="法务部", data={"clue_id": clue.id})
            db.add(evidence)
            await db.flush()
            self.ids = {name: record.id for name, record in (
                ("case", case), ("source", source_case), ("customer", customer), ("contract", contract),
                ("clue", clue), ("evidence", evidence), ("task", task), ("other_case", other_case),
                ("other_customer", unrelated), ("other_task", unrelated_task),
            )}
            self.file_ids = {}
            for name in ("case", "source", "customer", "contract", "clue", "evidence", "task", "other_customer"):
                filename = f"{name}.txt"
                path = Path(self.files.name) / filename
                path.write_text(name, encoding="utf-8")
                attachment = FileAttachment(
                    record_id=self.ids[name], category="任务资料附件" if name == "task" else "普通附件",
                    original_name=filename, stored_name=filename, content_type="text/plain", size=path.stat().st_size,
                    path=str(path), uploader="oa0930-owner",
                )
                db.add(attachment)
                await db.flush()
                self.file_ids[name] = attachment.id
            pdf_path = Path(self.files.name) / "related.pdf"
            Image.new("RGB", (16, 16), "white").save(pdf_path, "PDF")
            pdf_file = FileAttachment(
                record_id=contract.id, category="合同文档", original_name="related.pdf", stored_name="related.pdf",
                content_type="application/pdf", size=pdf_path.stat().st_size, path=str(pdf_path), uploader="oa0930-owner",
            )
            db.add(pdf_file)
            await db.flush()
            self.file_ids["pdf"] = pdf_file.id
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://oa0930.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()
        storage.UPLOAD_ROOT = self.original_upload_root
        self.files.cleanup()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def get(self, username, path):
        return await self.client.get(f"{settings.api_prefix}{path}", headers={"Authorization": f"Bearer {create_token(username, 'user')}"})

    async def test_authorized_roles_read_related_documents_and_task(self):
        case_id = self.ids["case"]
        expected = {self.file_ids[name] for name in ("case", "source", "customer", "contract", "clue", "evidence", "pdf")}
        for username in ("oa0930-finance", "oa0930-finance-clerk", "oa0930-process", "oa0930-admin"):
            with self.subTest(username=username):
                documents = await self.get(username, f"/cases/{case_id}/documents?page_size=200")
                self.assertEqual(documents.status_code, 200, documents.text)
                self.assertEqual({item["id"] for item in documents.json()["items"]}, expected)
                for name in ("customer", "contract", "source", "clue", "evidence"):
                    attachment_id = self.file_ids[name]
                    listed = await self.get(username, f"/attachments?record_id={self.ids[name]}&case_id={case_id}")
                    self.assertEqual(listed.status_code, 200, listed.text)
                    self.assertIn(attachment_id, {item["id"] for item in listed.json()["items"]})
                    for path in (f"/attachments/{attachment_id}", f"/attachments/{attachment_id}/preview", f"/attachments/{attachment_id}/download"):
                        response = await self.get(username, f"{path}?case_id={case_id}")
                        self.assertEqual(response.status_code, 200, f"{path}: {response.text}")
                task = await self.get(username, f"/cases/{case_id}/tasks/{self.ids['task']}")
                self.assertEqual(task.status_code, 200, task.text)
                self.assertEqual(task.json()["record"]["id"], self.ids["task"])
                task_file = await self.get(username, f"/cases/{case_id}/tasks/{self.ids['task']}/attachments/{self.file_ids['task']}/download")
                self.assertEqual(task_file.status_code, 200, task_file.text)
                self.assertEqual(task_file.content, b"task")

    async def test_context_does_not_expand_independent_or_unrelated_access(self):
        case_id = self.ids["case"]
        username = "oa0930-finance-clerk"
        for path in (
            f"/attachments?record_id={self.ids['customer']}",
            f"/attachments/{self.file_ids['customer']}/download",
            f"/attachments/{self.file_ids['other_customer']}?case_id={case_id}",
            f"/attachments/{self.file_ids['other_customer']}/download?case_id={case_id}",
            f"/cases/{case_id}/tasks/{self.ids['other_task']}",
            f"/cases/{case_id}/tasks/{self.ids['other_task']}/attachments/{self.file_ids['task']}/download",
        ):
            response = await self.get(username, path)
            self.assertIn(response.status_code, (403, 404), f"{path}: {response.text}")
        ordinary = await self.get("oa0930-ordinary", f"/cases/{case_id}/documents")
        self.assertEqual(ordinary.status_code, 404, ordinary.text)
        unrelated = await self.get("oa0930-ordinary", f"/attachments/{self.file_ids['customer']}/download?case_id={case_id}")
        self.assertEqual(unrelated.status_code, 404, unrelated.text)
        menu_only = await self.get("oa0930-case-menu", f"/attachments/{self.file_ids['customer']}/download?case_id={case_id}")
        self.assertEqual(menu_only.status_code, 404, menu_only.text)
        menu_case_documents = await self.get("oa0930-case-menu", f"/cases/{case_id}/documents")
        self.assertEqual(menu_case_documents.status_code, 404, menu_case_documents.text)
        write = await self.client.patch(
            f"{settings.api_prefix}/records/{case_id}", json={"title": "不应改变"},
            headers={"Authorization": f"Bearer {create_token(username, 'user')}"},
        )
        self.assertIn(write.status_code, (403, 404), write.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, case_id)).title, "主案")

    async def test_pdf_preview_and_missing_file_failure_are_case_scoped(self):
        case_id = self.ids["case"]
        pdf_id = self.file_ids["pdf"]
        metadata = await self.get("oa0930-process", f"/attachments/{pdf_id}/pdf-preview?case_id={case_id}")
        self.assertEqual(metadata.status_code, 200, metadata.text)
        self.assertEqual(metadata.json()["page_count"], 1)
        self.assertIn(f"case_id={case_id}", metadata.json()["page_url_template"])
        page = await self.get("oa0930-process", f"/attachments/{pdf_id}/pdf-preview/pages/1.png?case_id={case_id}")
        self.assertEqual(page.status_code, 200, page.text)
        self.assertTrue(page.content.startswith(b"\x89PNG"))
        denied = await self.get("oa0930-process", f"/attachments/{pdf_id}/pdf-preview?case_id={self.ids['other_case']}")
        self.assertEqual(denied.status_code, 404, denied.text)
        Path(self.files.name, "contract.txt").unlink()
        missing = await self.get("oa0930-process", f"/attachments/{self.file_ids['contract']}/download?case_id={case_id}")
        self.assertEqual(missing.status_code, 404, missing.text)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, WorkflowEvent
from app.security import current_identity


IDENTITY = {
    "username": "CODEX-828-ROW4-admin",
    "display_name": "第4行验收管理员",
    "role": "admin",
    "department": "上海分所",
}


class CaseRelatedAttachmentStatusRow4Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            customer = BusinessRecord(
                module="customer", serial_no="CODEX-828-R4-CUS", title="第4行客户",
                customer="第4行客户", status="正式客户", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={},
            )
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-828-R4-CON", title="第4行合同",
                customer="第4行客户", status="审批中", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={},
            )
            unrelated = BusinessRecord(
                module="contract", serial_no="CODEX-828-R4-OTHER", title="无关合同",
                customer="其他客户", status="已归档", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={},
            )
            db.add_all([customer, contract, unrelated])
            await db.flush()
            case = BusinessRecord(
                module="case", serial_no="CODEX-828-R4-CASE", title="第4行案件",
                customer=customer.title, status="文书准备", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={
                    "customer_record_id": customer.id,
                    "contract_record_id": contract.id,
                    "contract_no": contract.serial_no,
                },
            )
            db.add(case)
            await db.commit()
            self.customer_id = customer.id
            self.contract_id = contract.id
            self.unrelated_id = unrelated.id
            self.case_id = case.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row4.test")
        self.paths: list[Path] = []

    async def asyncTearDown(self):
        for path in self.paths:
            path.unlink(missing_ok=True)
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def upload(self, record_id: int, *, source_case_id: int | None = None, name: str = "row4.txt", category: str = "合同文档"):
        data = {"record_id": str(record_id), "category": category}
        if source_case_id:
            data["source_case_id"] = str(source_case_id)
        response = await self.client.post(
            f"{settings.api_prefix}/attachments",
            data=data,
            files={"file": (name, b"row4 case document", "text/plain")},
        )
        if response.status_code == 201:
            async with self.sessions() as db:
                attachment = await db.get(FileAttachment, response.json()["id"])
                self.assertIsNotNone(attachment)
                self.paths.append(Path(attachment.path))
        return response

    async def test_case_workbench_bypasses_only_related_contract_status_lock(self):
        generic = await self.upload(self.contract_id, name="generic-blocked.txt")
        self.assertEqual(generic.status_code, 409, generic.text)
        self.assertIn("审批中或已归档合同不能上传或删除附件", generic.json()["detail"])

        scoped = await self.upload(self.contract_id, source_case_id=self.case_id)
        self.assertEqual(scoped.status_code, 201, scoped.text)
        attachment_id = scoped.json()["id"]
        async with self.sessions() as db:
            attachment = await db.get(FileAttachment, attachment_id)
            self.assertEqual(attachment.record_id, self.contract_id)

        deleted = await self.client.post(
            f"{settings.api_prefix}/cases/attachments/delete",
            json={"attachment_ids": [attachment_id], "case_id": self.case_id},
        )
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json()["deleted"], 1)

    async def test_archived_related_contract_is_allowed_but_unrelated_target_is_rejected(self):
        async with self.sessions() as db:
            contract = await db.get(BusinessRecord, self.contract_id)
            contract.status = "已归档"
            await db.commit()

        scoped = await self.upload(self.contract_id, source_case_id=self.case_id, name="archived-related.txt")
        self.assertEqual(scoped.status_code, 201, scoped.text)

        unrelated = await self.upload(self.unrelated_id, source_case_id=self.case_id, name="unrelated.txt")
        self.assertEqual(unrelated.status_code, 409, unrelated.text)
        self.assertIn("不属于当前案件关联", unrelated.json()["detail"])

    async def test_context_case_deletes_own_and_direct_contract_attachments_together(self):
        own = await self.upload(self.case_id, category="普通附件", name="CODEX-selection-own.txt")
        self.assertEqual(own.status_code, 201, own.text)
        related = await self.upload(self.contract_id, source_case_id=self.case_id, name="CODEX-selection-related.txt")
        self.assertEqual(related.status_code, 201, related.text)
        attachment_ids = [own.json()["id"], related.json()["id"]]
        deleted = await self.client.post(
            f"{settings.api_prefix}/cases/attachments/delete",
            json={"attachment_ids": attachment_ids, "case_id": self.case_id},
        )
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json(), {"deleted": 2})
        async with self.sessions() as db:
            for attachment_id in attachment_ids:
                self.assertIsNone(await db.get(FileAttachment, attachment_id))
            events = list((await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.action == "批量删除案件文件",
            ))).all())
            self.assertEqual(len(events), 2)
            self.assertTrue(all(event.record_id == self.case_id for event in events))
            self.assertTrue(all(event.operator == IDENTITY["username"] for event in events))
        self.assertTrue(all(path.exists() for path in self.paths))  # 逻辑删除：附件文件本体保留

    async def test_unrelated_contract_rejects_mixed_delete_and_preserves_every_attachment(self):
        async with self.sessions() as db:
            unrelated = await db.get(BusinessRecord, self.unrelated_id)
            unrelated.status = "草稿"
            await db.commit()
        own = await self.upload(self.case_id, category="普通附件", name="CODEX-selection-own.txt")
        self.assertEqual(own.status_code, 201, own.text)
        related = await self.upload(self.contract_id, source_case_id=self.case_id, name="CODEX-selection-related.txt")
        self.assertEqual(related.status_code, 201, related.text)
        unrelated = await self.upload(self.unrelated_id, name="CODEX-selection-unrelated.txt")
        self.assertEqual(unrelated.status_code, 201, unrelated.text)
        attachment_ids = [own.json()["id"], related.json()["id"], unrelated.json()["id"]]
        rejected = await self.client.post(
            f"{settings.api_prefix}/cases/attachments/delete",
            json={"attachment_ids": attachment_ids, "case_id": self.case_id},
        )
        self.assertEqual(rejected.status_code, 409, rejected.text)
        self.assertIn("不属于当前案件关联", rejected.json()["detail"])
        async with self.sessions() as db:
            for attachment_id, record_id in zip(attachment_ids, [self.case_id, self.contract_id, self.unrelated_id]):
                attachment = await db.get(FileAttachment, attachment_id)
                self.assertIsNotNone(attachment)
                self.assertEqual(attachment.record_id, record_id)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(
                WorkflowEvent.action == "批量删除案件文件",
            )), 0)
        self.assertTrue(all(path.is_file() for path in self.paths))


if __name__ == "__main__":
    unittest.main()

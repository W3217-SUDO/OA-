import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import (
    EvidenceUpdateInput,
    delete_investigation_evidence,
    get_investigation_clue_workspace,
    update_evidence_record,
)
from app.models import BusinessRecord, WorkflowEvent


IDENTITY = {"username": "admin", "role": "admin"}


class InvestigationClueWorkspaceRow10Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _seed(self, db: AsyncSession):
        clue = BusinessRecord(
            module="clue", serial_no="CODEX-831-R10-CLUE", title="线索",
            customer="客户", status="已取证", owner="admin", department="上海分所", data={},
        )
        db.add(clue)
        await db.flush()
        evidence = BusinessRecord(
            module="evidence", serial_no="CODEX-831-R10-EVIDENCE", title="取证材料",
            customer="客户", status="已取证", owner="admin", department="上海分所",
            data={"clue_id": clue.id, "clue_no": clue.serial_no, "notary_institution": "旧公证处"},
        )
        db.add(evidence)
        await db.flush()
        clue.data = {"evidence_ids": [evidence.id], "evidence_count": 1}
        await db.commit()
        return clue, evidence

    async def test_workspace_lists_linked_evidence_and_supports_full_edit(self):
        async with self.sessions() as db:
            clue, evidence = await self._seed(db)
            workspace = await get_investigation_clue_workspace(clue.id, IDENTITY, db)
            self.assertEqual([item["serial_no"] for item in workspace["evidence"]], [evidence.serial_no])
            self.assertTrue(workspace["evidence"][0]["can_edit"])

            updated = await update_evidence_record(
                evidence.id,
                EvidenceUpdateInput(
                    notary_institution="新公证处", certificate_no="CODEX-GZ-001",
                    collected_at="2026-08-31", invoice_no="CODEX-FP-001",
                    storage_location="一号库位", evidence_status="已入库",
                ),
                IDENTITY,
                db,
            )
            self.assertEqual(updated["data"]["notary_institution"], "新公证处")
            self.assertEqual(updated["data"]["notarization_no"], "CODEX-GZ-001")
            self.assertEqual(updated["data"]["storage_state"], "已入库")
            self.assertTrue(await db.scalar(
                __import__("sqlalchemy").select(WorkflowEvent.id).where(
                    WorkflowEvent.record_id == evidence.id,
                    WorkflowEvent.action == "修改证据信息",
                )
            ))

    async def test_delete_detaches_evidence_from_clue(self):
        async with self.sessions() as db:
            clue, evidence = await self._seed(db)
            response = await delete_investigation_evidence(evidence.id, IDENTITY, db)
            self.assertEqual(response.status_code, 204)
            self.assertIsNone(await db.get(BusinessRecord, evidence.id))
            await db.refresh(clue)
            self.assertEqual(clue.data["evidence_ids"], [])
            self.assertEqual(clue.data["evidence_count"], 0)


if __name__ == "__main__":
    unittest.main()

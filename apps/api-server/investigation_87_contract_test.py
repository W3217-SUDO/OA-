"""8.7 Excel regressions: collection details and source-task case conversion."""

import unittest
from pathlib import Path
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from app.database import Base
from app.main import (
    BatchClueCaseInput,
    ClueCollectionInput,
    ClueSourceContractBindingInput,
    InvestigationTaskInput,
    RecordInput,
    batch_create_cases_from_clues,
    bind_clue_source_contract,
    create_investigation_record,
    create_investigation_task,
    list_records,
    register_clue_collection,
    _contract_customer_record_dict,
)
from app.models import (
    BusinessRecord,
    FileAttachment,
    LegacyInvestigationClueEvidence,
    LegacyInvestigationClueEvidenceFile,
    LegacyInvestigationClueFile,
    LegacyInvestigationTask,
    User,
)


IDENTITY = {"username": "admin", "role": "admin"}
APP = Path(__file__).resolve().parent / "app" / "main.py"


class Investigation87ContractTest(unittest.IsolatedAsyncioTestCase):
    def test_administrator_published_investigation_view_is_not_owner_scoped(self):
        source = APP.read_text(encoding="utf-8")
        self.assertIn(
            'if investigation_view == "published" and identity.get("role") != "admin":',
            source,
        )

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_collection_keeps_all_legacy_registration_fields(self):
        async with self.sessions() as db:
            clue = BusinessRecord(
                module="clue", serial_no="CODEX-87-COLLECT", title="取证线索", customer="CODEX客户",
                status="待取证", owner="admin", department="上海", data={},
            )
            db.add(clue)
            await db.flush()
            selected = FileAttachment(
                record_id=clue.id, category="取证附件", file_type_code="11",
                original_name="已选择取证.pdf", stored_name="collect-selected.pdf",
                content_type="application/pdf", size=128, path="/uploads/collect-selected.pdf", uploader="admin",
            )
            other = FileAttachment(
                record_id=clue.id, category="线索附件", file_type_code="12",
                original_name="线索照片.jpg", stored_name="clue-other.jpg",
                content_type="image/jpeg", size=64, path="/uploads/clue-other.jpg", uploader="admin",
            )
            db.add_all([selected, other])
            await db.commit()
            result = await register_clue_collection(
                clue.id,
                ClueCollectionInput(
                    collected_at=date.today(), notary_institution="上海市东方公证处",
                    notarization_no="(2026)沪东证字001号", invoice_no="INV-CODEX-87",
                    storage_location="档案室 A-01", evidence_status="已入库", evidence_file_ids=[selected.id],
                ),
                IDENTITY, db,
            )
            evidence = await db.scalar(select(LegacyInvestigationClueEvidence).where(LegacyInvestigationClueEvidence.EvidenceId == -clue.id))
            evidence_files = (await db.scalars(select(LegacyInvestigationClueEvidenceFile).where(LegacyInvestigationClueEvidenceFile.EvidenceGuid == evidence.EvidenceGuid))).all()
            clue_files = (await db.scalars(select(LegacyInvestigationClueFile).where(LegacyInvestigationClueFile.ClueGuid == evidence.ClueGuid))).all()

        self.assertEqual(result["status"], "已取证")
        self.assertEqual(result["data"]["notarization_no"], "(2026)沪东证字001号")
        self.assertEqual(result["data"]["invoice_no"], "INV-CODEX-87")
        self.assertEqual(result["data"]["storage_location"], "档案室 A-01")
        self.assertEqual(result["data"]["evidence_status"], "已入库")
        self.assertEqual(evidence.NotaryOrganization, "上海市东方公证处")
        self.assertEqual(evidence.NotarialNo, "(2026)沪东证字001号")
        self.assertEqual(evidence.InvoiceNo, "INV-CODEX-87")
        self.assertEqual(evidence.EvidenceStatus, 20)
        self.assertEqual([(item.FileId, item.FileName) for item in evidence_files], [(selected.id, "已选择取证.pdf")])
        self.assertEqual([(item.FileId, item.FileName) for item in clue_files], [(other.id, "线索照片.jpg")])

    async def test_collection_reregistration_moves_attachment_without_legacy_duplicate(self):
        async with self.sessions() as db:
            clue = BusinessRecord(
                module="clue", serial_no="CODEX-87-COLLECT-MOVE", title="取证附件迁移线索",
                customer="CODEX客户", status="待取证", owner="admin", department="上海", data={},
            )
            db.add(clue)
            await db.flush()
            attachment = FileAttachment(
                record_id=clue.id, category="线索附件", file_type_code="12",
                original_name="可切换附件.jpg", stored_name="collect-move.jpg",
                content_type="image/jpeg", size=64, path="/uploads/collect-move.jpg", uploader="admin",
            )
            db.add(attachment)
            await db.commit()
            await register_clue_collection(
                clue.id,
                ClueCollectionInput(collected_at=date.today(), notary_institution="上海市东方公证处"),
                IDENTITY, db,
            )
            clue.status = "待取证"
            await db.commit()
            await register_clue_collection(
                clue.id,
                ClueCollectionInput(collected_at=date.today(), notary_institution="上海市东方公证处", evidence_file_ids=[attachment.id]),
                IDENTITY, db,
            )
            evidence_file = await db.scalar(select(LegacyInvestigationClueEvidenceFile).where(LegacyInvestigationClueEvidenceFile.FileId == attachment.id))
            clue_file = await db.scalar(select(LegacyInvestigationClueFile).where(LegacyInvestigationClueFile.FileId == attachment.id))

        self.assertIsNotNone(evidence_file)
        self.assertIsNone(clue_file)

    async def test_clue_number_is_generated_by_server_in_legacy_format(self):
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理员", department="上海", password_hash="x", role="admin"))
            source = BusinessRecord(
                module="investigation", serial_no="DC-CODEX-AUTO-CLUE", title="来源调查任务",
                customer="测试客户", status="进行中", owner="admin", department="上海", data={},
            )
            db.add(source)
            await db.commit()
            result = await create_investigation_record(
                RecordInput(
                    module="clue", serial_no="用户不能指定", title="自动编号线索",
                    owner="fwl", data={"source_task_id": source.id},
                ),
                IDENTITY, db,
            )

        self.assertRegex(result["serial_no"], r"^XS\d{14}$")
        self.assertNotEqual(result["serial_no"], "用户不能指定")
        self.assertEqual(result["owner"], "admin")

    async def test_case_uses_contract_from_source_task_and_enters_waiting_notary(self):
        async with self.sessions() as db:
            contract = BusinessRecord(
                module="contract", serial_no="HT-CODEX-87", title="CODEX调查合同", customer="CODEX客户",
                status="已通过", owner="admin", department="上海", data={},
            )
            db.add(contract)
            await db.flush()
            task = BusinessRecord(
                module="task", serial_no="RW-CODEX-87", title="来源调查任务", customer="CODEX客户",
                status="已完成", owner="admin", department="上海",
                data={"investigation_record_id": 1, "contract_no": contract.serial_no, "contract_name": contract.title},
            )
            db.add(task)
            await db.flush()
            clue = BusinessRecord(
                module="clue", serial_no="XS-CODEX-87", title="自动转案线索", customer="CODEX客户",
                status="已取证", owner="admin", department="上海",
                data={"source_task_id": task.id, "client_position": "原告", "cause_or_charge": "商标侵权"},
            )
            db.add(clue)
            await db.commit()
            result = await batch_create_cases_from_clues(
                BatchClueCaseInput(clue_ids=[clue.id], case_type="民事案件", court="上海市浦东新区人民法院"),
                IDENTITY, db,
            )
            case = await db.get(BusinessRecord, result["created_ids"][0])

        self.assertEqual(result["created"], 1)
        self.assertEqual(case.status, "等待公证书")
        self.assertEqual(case.data["contract_id"], contract.id)
        self.assertEqual(case.data["contract_no"], "HT-CODEX-87")
        self.assertEqual(case.data["clue_no"], "XS-CODEX-87")
        self.assertEqual(case.data["client_position"], "原告")
        self.assertEqual(case.data["cause_or_charge"], "商标侵权")

    async def test_case_without_source_contract_can_still_be_created(self):
        async with self.sessions() as db:
            clue = BusinessRecord(
                module="clue", serial_no="XS-CODEX-87-NO-CONTRACT", title="无合同已取证线索",
                customer="CODEX客户", status="已取证", owner="admin", department="上海",
                data={"cause_or_charge": "商标侵权"},
            )
            db.add(clue)
            await db.commit()
            result = await batch_create_cases_from_clues(
                BatchClueCaseInput(
                    clue_ids=[clue.id], case_type="民事案件", cause_or_charge="商标侵权",
                    handling_lawyer="管理员",
                ),
                IDENTITY, db,
            )
            case = await db.get(BusinessRecord, result["created_ids"][0])

        self.assertEqual(result["created"], 1)
        self.assertEqual(case.status, "等待公证书")
        self.assertIsNone(case.data["contract_id"])
        self.assertEqual(case.customer, "CODEX客户")

    async def test_legacy_clue_binding_repairs_source_task_and_customer_before_case_generation(self):
        async with self.sessions() as db:
            contract = BusinessRecord(
                module="contract", serial_no="HT-CODEX-87-REPAIR", title="CODEX修复合同", customer="CODEX正确客户",
                status="已通过", owner="admin", department="上海", data={},
            )
            db.add(contract)
            await db.flush()
            task = BusinessRecord(
                module="task", serial_no="RW-CODEX-87-REPAIR", title="历史来源任务", customer="历史错误客户",
                status="已完成", owner="admin", department="上海", data={"investigation_record_id": 1},
            )
            db.add(task)
            await db.flush()
            clue = BusinessRecord(
                module="clue", serial_no="XS-CODEX-87-REPAIR", title="历史已取证线索", customer="历史错误客户",
                status="已取证", owner="admin", department="上海", data={"source_task_id": task.id},
            )
            db.add(clue)
            await db.commit()
            result = await bind_clue_source_contract(
                clue.id, ClueSourceContractBindingInput(contract_record_id=contract.id), IDENTITY, db,
            )
            await db.refresh(task)
            await db.refresh(clue)

        self.assertEqual(result["contract"]["serial_no"], "HT-CODEX-87-REPAIR")
        self.assertEqual(task.customer, "CODEX正确客户")
        self.assertEqual(task.data["contract_id"], contract.id)
        self.assertEqual(clue.customer, "CODEX正确客户")
        self.assertEqual(clue.data["contract_no"], "HT-CODEX-87-REPAIR")

    async def test_investigation_child_inherits_parent_schedule_region_and_source(self):
        async with self.sessions() as db:
            investigation = BusinessRecord(
                module="investigation", serial_no="DC-CODEX-PARENT", title="合同调查项目",
                customer="CODEX客户", status="进行中", owner="fwl", department="上海",
                data={
                    "right_type": "商标", "region": "全国", "authorized_from": "2026-08-10",
                    "authorized_to": "2026-09-09", "source_owner": "admin", "assigner": "admin",
                },
            )
            db.add(investigation)
            await db.flush()
            task = BusinessRecord(
                module="task", serial_no="RW-CODEX-CHILD", title="调查子任务",
                customer="CODEX客户", status="待接收", owner="fwl", department="上海",
                data={"investigation_record_id": investigation.id, "investigation_no": investigation.serial_no},
            )
            db.add(task)
            await db.commit()
            result = await _contract_customer_record_dict(task, None, db)

        self.assertEqual(result["data"]["region"], "全国")
        self.assertEqual(result["data"]["authorized_from"], "2026-08-10")
        self.assertEqual(result["data"]["authorized_to"], "2026-09-09")
        self.assertEqual(result["data"]["source_owner"], "admin")

    async def test_subtask_inherits_parent_schedule_and_projects_old_table_fields(self):
        async with self.sessions() as db:
            db.add(User(username="fwl", display_name="范文玲", department="上海", password_hash="x", role="user"))
            contract = BusinessRecord(module="contract", serial_no="HT-CODEX-87-SCHEDULE", title="CODEX合同", customer="CODEX客户", status="已通过", owner="admin", department="上海", data={})
            db.add(contract); await db.flush()
            investigation = BusinessRecord(
                module="investigation", serial_no="DC-CODEX-87-SCHEDULE", title="CODEX调查", customer="CODEX客户", status="进行中", owner="admin", department="上海",
                data={"contract_id": contract.id, "contract_no": contract.serial_no, "authorized_from": "2026-08-10", "authorized_to": "2026-09-09", "province": "浙江省", "city": "杭州市", "district": "西湖区"},
            )
            db.add(investigation); await db.flush()
            parent = BusinessRecord(
                module="task", serial_no="RW-CODEX-87-PARENT", title="父调查任务", customer="CODEX客户", status="进行中", owner="fwl", department="上海",
                data={"investigation_record_id": investigation.id, "investigation_no": investigation.serial_no, "contract_id": contract.id, "contract_no": contract.serial_no, "start_date": "2026-08-15", "end_date": "2026-08-25", "authorized_from": "2026-08-15", "authorized_to": "2026-08-25", "province": "江苏省", "city": "南京市", "district": "玄武区", "region": "江苏省 南京市 玄武区"},
            )
            db.add(parent); await db.commit()
            created = await create_investigation_task(
                investigation.id,
                InvestigationTaskInput(title="子调查任务", owner="fwl", deadline=date(2026, 8, 25), parent_task_id=parent.id),
                IDENTITY, db,
            )
            legacy = await db.scalar(select(LegacyInvestigationTask).where(LegacyInvestigationTask.TaskNo == created["serial_no"][:20]))

        self.assertEqual(created["data"]["investigation_no"], "DC-CODEX-87-SCHEDULE")
        self.assertEqual(created["data"]["parent_task_no"], "RW-CODEX-87-PARENT")
        self.assertEqual(created["data"]["start_date"], "2026-08-15")
        self.assertEqual(created["data"]["end_date"], "2026-08-25")
        self.assertEqual((created["data"]["province"], created["data"]["city"], created["data"]["district"]), ("江苏省", "南京市", "玄武区"))
        self.assertEqual((legacy.InvestigationNo, legacy.Province, legacy.City, legacy.District), ("DC-CODEX-87-SCHEDULE", "江苏省", "南京市", "玄武区"))
        self.assertEqual(legacy.BeginTime.date(), date(2026, 8, 15))
        self.assertEqual(legacy.EndTime.date(), date(2026, 8, 25))

    async def test_investigation_parent_views_separate_published_and_assigned_tasks(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="fwl", display_name="范文玲", department="上海", password_hash="x", role="user"),
                User(username="admin", display_name="管理员", department="上海", password_hash="x", role="admin"),
                BusinessRecord(
                    module="investigation", serial_no="DC-CODEX-ASSIGNED", title="管理员发布给范文玲",
                    customer="CODEX客户", status="进行中", owner="fwl", department="上海",
                    data={"publisher": "admin", "authorized_to": "2026-09-09"},
                ),
                BusinessRecord(
                    module="investigation", serial_no="DC-CODEX-FWL-PUBLISHED", title="范文玲自己发布",
                    customer="CODEX客户", status="进行中", owner="fwl", department="上海",
                    data={"publisher": "fwl", "authorized_to": "2026-09-09"},
                ),
                BusinessRecord(
                    module="investigation", serial_no="DC-CODEX-FWL-LEGACY", title="历史范文玲发布",
                    customer="CODEX客户", status="进行中", owner="fwl", department="上海",
                    data={"authorized_to": "2026-09-09"},
                ),
            ])
            await db.commit()

            published = await list_records(
                module="investigation", keyword="", record_status="", scope="mine", statuses="",
                customer_id=None, customer="", customer_no="", exclude_archived=False,
                investigation_view="published", page=1, page_size=100,
                identity={"username": "fwl", "role": "user"}, db=db,
            )
            assigned = await list_records(
                module="investigation", keyword="", record_status="", scope="mine", statuses="",
                customer_id=None, customer="", customer_no="", exclude_archived=False,
                investigation_view="assigned", page=1, page_size=100,
                identity={"username": "fwl", "role": "user"}, db=db,
            )

        self.assertEqual(
            {item["serial_no"] for item in published["items"]},
            {"DC-CODEX-FWL-PUBLISHED", "DC-CODEX-FWL-LEGACY"},
        )
        self.assertEqual(
            {item["serial_no"] for item in assigned["items"]},
            {"DC-CODEX-ASSIGNED", "DC-CODEX-FWL-PUBLISHED", "DC-CODEX-FWL-LEGACY"},
        )


if __name__ == "__main__":
    unittest.main()

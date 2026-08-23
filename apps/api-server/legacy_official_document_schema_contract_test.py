"""Regression contract for the local legacy official-document compatibility schema."""

from pathlib import Path
from datetime import datetime
import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import _sync_legacy_case, _sync_legacy_contract, _sync_legacy_contract_audit, _sync_legacy_customer, _sync_legacy_investigation, _sync_legacy_investigation_clue, _sync_legacy_investigation_task, _sync_legacy_official_audit, _sync_legacy_official_document, _sync_legacy_projection
from app.models import BusinessRecord, FileAttachment, LegacyCase, LegacyCaseFile, LegacyCaseLog, LegacyCaseParticipant, LegacyContract, LegacyContractAudit, LegacyContractFile, LegacyCustomer, LegacyCustomerContact, LegacyInvestigation, LegacyInvestigationClue, LegacyInvestigationTask, LegacyOfficialDocument, LegacyOfficialDocumentAudit, LegacyOfficialDocumentFile, WorkflowEvent


APP = Path(__file__).resolve().parent / "app" / "main.py"


class LegacyOfficialDocumentSchemaContractTest(unittest.TestCase):
    def test_legacy_table_names_and_column_counts_match_sql_server(self):
        tables = Base.metadata.tables
        self.assertIn("AWS_OfficialDocument", tables)
        self.assertIn("AWS_OfficialDocument_Audit", tables)
        self.assertIn("AWS_OfficialDocument_File", tables)
        self.assertEqual(len(LegacyOfficialDocument.__table__.columns), 36)
        self.assertEqual(len(LegacyOfficialDocumentAudit.__table__.columns), 14)
        self.assertEqual(len(LegacyOfficialDocumentFile.__table__.columns), 13)
        self.assertEqual(len(LegacyCustomer.__table__.columns), 53)
        self.assertEqual(len(LegacyCustomerContact.__table__.columns), 31)
        self.assertEqual(len(LegacyCase.__table__.columns), 143)
        self.assertEqual(list(LegacyCase.__table__.columns.keys())[-1], "OriginalCaseNo")
        self.assertEqual(len(LegacyInvestigation.__table__.columns), 23)
        self.assertEqual(len(LegacyInvestigationTask.__table__.columns), 21)
        self.assertEqual(len(LegacyInvestigationClue.__table__.columns), 44)
        self.assertEqual(len(LegacyCaseFile.__table__.columns), 25)
        self.assertEqual(len(LegacyCaseParticipant.__table__.columns), 8)
        self.assertEqual(len(LegacyCaseLog.__table__.columns), 10)

    def test_legacy_soft_reference_columns_are_indexed(self):
        columns = LegacyOfficialDocument.__table__.c
        for name in ("OfficialDocumentNo", "OfficialDocumentGuid", "CaseNo", "ContractNo", "CustomerNo", "BusinessOwner", "OfficialDocumentStatus", "IsActived"):
            self.assertIn(name, columns)
        self.assertEqual(columns.OfficialDocumentNo.type.length, 20)
        self.assertEqual(columns.CaseNo.type.length, 50)
        self.assertEqual(columns.ContractNo.type.length, 50)
        self.assertEqual(columns.CustomerNo.type.length, 50)

    def test_new_workflow_synchronizes_legacy_status_codes(self):
        source = APP.read_text(encoding="utf-8")
        for status, code in (("草稿", 0), ("待审批", 10), ("待用印", 20), ("已拒绝", 30), ("已撤回", 40), ("已用印", 60)):
            self.assertIn(f'"{status}": {code}', source)
        self.assertIn("await _sync_legacy_official_document(item, identity, db)", source)
        self.assertIn("_sync_legacy_official_audit(item, identity, db, 10", source)
        self.assertIn("_sync_legacy_official_audit(item, identity, db, 40", source)
        self.assertIn("_sync_legacy_official_audit(item, identity, db, 20 if body.approved else 30", source)
        self.assertIn("_sync_legacy_official_audit(item, identity, db, 60", source)


class LegacyOfficialDocumentProjectionRuntimeTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_seal_projection_keeps_legacy_soft_references_files_and_status_history(self):
        identity = {"username": "admin"}
        async with self.sessions() as db:
            customer = BusinessRecord(module="customer", serial_no="KH-001", title="测试客户", customer="测试客户", owner="admin", data={"customer_no": "CUS-001"})
            contract = BusinessRecord(module="contract", serial_no="HT-001", title="测试合同", customer="测试客户", owner="admin", data={"customer_no": "CUS-001"})
            case = BusinessRecord(module="case", serial_no="CASE-001", title="测试案件", customer="测试客户", owner="admin", data={"customer_no": "CUS-001", "contract_no": "HT-001"})
            seal = BusinessRecord(
                module="seal", serial_no="YY-001", title="测试案件用印", customer="测试客户", status="草稿", owner="admin",
                data={"case_no": "CASE-001", "contract_no": "HT-001", "use_type": "案件用印", "copies": 2, "is_electronic_seal": True, "is_offline_print": True},
            )
            db.add_all([customer, contract, case, seal])
            await db.flush()
            db.add(FileAttachment(record_id=seal.id, category="用印文件", original_name="授权书.pdf", stored_name="seal-auth.pdf", content_type="application/pdf", size=256, path="/uploads/seal-auth.pdf", uploader="admin"))
            await db.flush()

            await _sync_legacy_projection(seal, identity, db)
            seal.status = "待审批"
            await _sync_legacy_official_audit(seal, identity, db, 10, "提交")
            seal.status = "待用印"
            seal.data = {**seal.data, "approver": "auditor", "approval_comment": "同意"}
            await _sync_legacy_official_audit(seal, identity, db, 20, "同意")
            seal.status = "已用印"
            await _sync_legacy_official_audit(seal, identity, db, 60, "已完成")
            await db.commit()

            legacy = await db.scalar(select(LegacyOfficialDocument).where(LegacyOfficialDocument.OfficialDocumentNo == "YY-001"))
            self.assertIsNotNone(legacy)
            self.assertEqual(legacy.CaseNo, "CASE-001")
            self.assertEqual(legacy.ContractNo, "HT-001")
            self.assertEqual(legacy.CustomerNo, "CUS-001")
            self.assertEqual(legacy.OfficialDocumentStatus, 60)
            self.assertEqual(legacy.PrintStatus, 1)
            self.assertEqual(legacy.Auditor, "auditor")
            self.assertEqual(legacy.AuditRemark, "同意")

            files = (await db.scalars(select(LegacyOfficialDocumentFile).where(LegacyOfficialDocumentFile.OfficialDocumentGuid == legacy.OfficialDocumentGuid))).all()
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].FileName, "授权书.pdf")
            self.assertEqual(files[0].FileSize, 256)

            audits = (await db.scalars(select(LegacyOfficialDocumentAudit).where(LegacyOfficialDocumentAudit.OfficialDocumentNo == "YY-001").order_by(LegacyOfficialDocumentAudit.AuditRoundId))).all()
            self.assertEqual([audit.AuditStatus for audit in audits], [10, 20, 60])
            self.assertEqual([audit.AuditRoundId for audit in audits], [1, 2, 3])

    async def test_contract_projection_keeps_legacy_identifier_financial_and_approval_fields(self):
        identity = {"username": "admin"}
        async with self.sessions() as db:
            contract = BusinessRecord(
                module="contract", serial_no="SHHT2600001", title="测试服务合同", customer="测试客户", status="草稿", owner="owner01",
                description="合同备注",
                data={"contract_guid": "11111111-1111-1111-1111-111111111111", "customer_id": 7, "customer_no": "CUS-001", "amount": "12345.67", "tax_rate": "6", "contract_type": "专项服务", "charging_type": "按项目", "signed_at": "2026-08-12", "end_date": "2027-08-11"},
            )
            db.add(contract)
            await db.flush()
            db.add(FileAttachment(record_id=contract.id, category="合同附件", original_name="服务合同.pdf", stored_name="contract.pdf", content_type="application/pdf", size=512, path="/uploads/contract.pdf", uploader="owner01"))
            await db.flush()
            await _sync_legacy_contract(contract, identity, db)
            contract.status = "审批中"
            contract.data = {**contract.data, "approval_count": 1, "submitted_at": "2026-08-12T10:00:00"}
            await _sync_legacy_contract_audit(contract, identity, db, 10, "提交")
            contract.status = "审批通过"
            contract.data = {**contract.data, "approved_at": "2026-08-12T11:00:00"}
            await _sync_legacy_contract_audit(contract, identity, db, 20, "同意")
            await db.commit()

            legacy = await db.scalar(select(LegacyContract).where(LegacyContract.ContractNo == "SHHT2600001"))
            self.assertIsNotNone(legacy)
            self.assertEqual(legacy.ContractGuid, "11111111-1111-1111-1111-111111111111")
            self.assertEqual(legacy.CustomerId, 7)
            self.assertEqual(legacy.CustomerNo, "CUS-001")
            self.assertEqual(legacy.BusinessOwner, "owner01")
            self.assertEqual(float(legacy.ContractMoney), 12345.67)
            self.assertEqual(float(legacy.TaxRate), 6.0)
            self.assertIsNone(legacy.ContractType)
            self.assertIsNone(legacy.ChargingType)
            self.assertEqual(legacy.ContractStatus, 20)
            self.assertEqual(legacy.AuditRoundId, 1)
            self.assertEqual(legacy.AuditDate, datetime(2026, 8, 12, 11, 0))
            self.assertEqual(legacy.IsActived, "Y")
            files = (await db.scalars(select(LegacyContractFile).where(LegacyContractFile.ContractGuid == legacy.ContractGuid))).all()
            self.assertEqual([(file.FileName, file.FileSize) for file in files], [("服务合同.pdf", 512)])
            audits = (await db.scalars(select(LegacyContractAudit).where(LegacyContractAudit.ContractNo == "SHHT2600001").order_by(LegacyContractAudit.AuditRoundId))).all()
            self.assertEqual([audit.AuditStatus for audit in audits], [10, 20])

    async def test_customer_projection_preserves_multiple_contacts_and_soft_deletion(self):
        identity = {"username": "admin"}
        async with self.sessions() as db:
            customer = BusinessRecord(
                module="customer", serial_no="SHKH2600001", title="测试客户", customer="测试客户", status="签约", owner="owner01",
                data={
                    "customer_guid": "22222222-2222-2222-2222-222222222222", "phone": "021-12345678", "credit_code": "91310000TEST", "level": "签约客户", "province": "上海", "is_assisted": "是", "fee_reduction": "否",
                    "contacts": [
                        {"id": "contact-a", "name": "张三", "position": "法务经理", "phone": "13800000001", "is_primary": True, "is_valid": True},
                        {"id": "contact-b", "name": "李四", "position": "品牌经理", "phone": "13800000002", "is_primary": False, "is_valid": True},
                    ],
                },
            )
            db.add(customer)
            await db.flush()
            await _sync_legacy_customer(customer, identity, db)
            contacts = (await db.scalars(select(LegacyCustomerContact).where(LegacyCustomerContact.CustomerNo == "SHKH2600001").order_by(LegacyCustomerContact.Contacts))).all()
            self.assertEqual([(contact.Contacts, contact.IsDefault, contact.IsActived) for contact in contacts], [("张三", "Y", "Y"), ("李四", "N", "Y")])

            customer.data = {**customer.data, "contacts": [{**customer.data["contacts"][0], "is_primary": False}, {**customer.data["contacts"][1], "is_primary": True}]}
            await _sync_legacy_customer(customer, identity, db)
            customer.data = {**customer.data, "contacts": [customer.data["contacts"][1]]}
            await _sync_legacy_customer(customer, identity, db)
            customer.status = "已回收"
            await _sync_legacy_customer(customer, identity, db)
            await db.commit()

            legacy = await db.scalar(select(LegacyCustomer).where(LegacyCustomer.CustomerNo == "SHKH2600001"))
            self.assertEqual(legacy.CustomerName, "测试客户")
            self.assertEqual(legacy.LicenseNo, "91310000TEST")
            self.assertEqual(legacy.IsAssisted, "Y")
            self.assertEqual(legacy.IsActived, "N")
            contacts = (await db.scalars(select(LegacyCustomerContact).where(LegacyCustomerContact.CustomerNo == "SHKH2600001").order_by(LegacyCustomerContact.Contacts))).all()
            self.assertEqual([(contact.Contacts, contact.IsDefault, contact.IsActived) for contact in contacts], [("张三", "N", "N"), ("李四", "Y", "Y")])

    async def test_investigation_projection_preserves_contract_parent_child_and_case_links(self):
        identity = {"username": "admin"}
        async with self.sessions() as db:
            investigation = BusinessRecord(module="investigation", serial_no="DC2600001", title="investigation", customer="customer", owner="owner01", status="进行中", data={"contract_no": "SHHT2600001", "authorized_from": "2026-08-01", "authorized_to": "2026-08-31", "authorization_scope": "全国", "customer_review": True})
            db.add(investigation)
            await db.flush()
            task = BusinessRecord(module="task", serial_no="RW2600001", title="task", customer="customer", owner="investigator", status="处理中", data={"investigation_record_id": investigation.id, "investigation_no": investigation.serial_no, "contract_no": "SHHT2600001", "deadline": "2026-08-31", "authorization_scope": "全国"})
            db.add(task)
            await db.flush()
            clue = BusinessRecord(module="clue", serial_no="XS2600001", title="store", customer="customer", owner="investigator", status="已转案件", data={"source_task_id": task.id, "source_task_no": task.serial_no, "investigation_no": investigation.serial_no, "platform": "platform", "product": "product", "source_url": "https://example.test", "converted_case_no": "SHMS2600001", "submitted_at": "2026-08-02T09:00:00"})
            db.add(clue)
            await db.flush()
            await _sync_legacy_investigation(investigation, identity, db)
            await _sync_legacy_investigation_task(task, identity, db)
            await _sync_legacy_investigation_clue(clue, identity, db)
            await db.commit()

            legacy_investigation = await db.scalar(select(LegacyInvestigation).where(LegacyInvestigation.InvestigationNo == "DC2600001"))
            legacy_task = await db.scalar(select(LegacyInvestigationTask).where(LegacyInvestigationTask.TaskNo == "RW2600001"))
            legacy_clue = await db.scalar(select(LegacyInvestigationClue).where(LegacyInvestigationClue.ClueNo == "XS2600001"))
            self.assertEqual(legacy_investigation.ContractNo, "SHHT2600001")
            self.assertEqual(legacy_investigation.NeedToAuditOnCustomer, "Y")
            self.assertEqual(legacy_task.InvestigationNo, "DC2600001")
            self.assertEqual(legacy_task.TaskStatus, 10)
            self.assertEqual(legacy_clue.InvestigationTaskNo, "RW2600001")
            self.assertEqual(legacy_clue.InvestigationNo, "DC2600001")
            self.assertEqual(legacy_clue.CaseNo, "SHMS2600001")

    async def test_case_projection_preserves_legacy_soft_links_and_case_facts(self):
        identity = {"username": "admin"}
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="SHMS2600001", title="case", customer="customer", owner="owner01", status="run",
                data={
                    "customer_no": "SHKH2600001", "contract_no": "SHHT2600001", "case_type_id": 2,
                    "case_phase_id": 101002, "source_person": "source", "handling_lawyers": ["lawyer"],
                    "handling_lawyer_usernames": ["lawyer-a"], "assistant": "assistant", "assistant_username": "lszl2",
                    "plaintiffs": ["plaintiff"], "plaintiff_agents": ["plaintiff-agent"], "defendants": ["defendant"],
                    "defendant_agents": ["defendant-agent"], "investigation_clue_nos": ["XSX2600001"], "notary_nos": "GZ2600001",
                    "court": "court", "court_case_no": "case-court-1", "judge": "judge", "clerk": "clerk",
                    "filing_date": "2026-08-12", "deadline": "2026-09-11", "litigation_amount": "1000.50",
                    "settlement_amount": "800.25", "execution_status_code": 20, "original_case_no": "SHMS2500001",
                },
            )
            db.add(case)
            await db.flush()
            db.add(FileAttachment(record_id=case.id, category="案件文件", file_type_code="602", original_name="起诉状.pdf", stored_name="case-complaint.pdf", content_type="application/pdf", size=1024, path="/uploads/case-complaint.pdf", uploader="owner01", is_transmitted=True))
            db.add(WorkflowEvent(record_id=case.id, action="提交立案", from_status="新案待分配", to_status="待立案审批", operator="owner01", comment="已提交"))
            await db.flush()
            await _sync_legacy_case(case, identity, db)
            case.status = "archived"
            case.data = {**case.data, "archive_no": "DA2600001", "archive_submitted_at": "2026-08-12T10:00:00", "archived_at": "2026-08-12T11:00:00", "archive_reviewer": "admin"}
            await _sync_legacy_case(case, identity, db)
            await db.commit()

            legacy = await db.scalar(select(LegacyCase).where(LegacyCase.CaseNo == "SHMS2600001"))
            self.assertIsNotNone(legacy)
            self.assertEqual(legacy.CustomerNo, "SHKH2600001")
            self.assertEqual(legacy.ContractNo, "SHHT2600001")
            self.assertEqual(legacy.InvestigationClueNos, "XSX2600001")
            self.assertEqual(legacy.AppellantNames, "plaintiff")
            self.assertEqual(legacy.AppelleeNames, "defendant")
            self.assertEqual(legacy.FirstIntanceCourt, "court")
            self.assertEqual(legacy.FirstIntanceCaseNo, "case-court-1")
            self.assertEqual(float(legacy.LitigationAmount), 1000.50)
            self.assertEqual(legacy.ArchiveStatus, 0)
            self.assertEqual(legacy.FileNo, "DA2600001")
            files = (await db.scalars(select(LegacyCaseFile).where(LegacyCaseFile.CaseNo == "SHMS2600001"))).all()
            participants = (await db.scalars(select(LegacyCaseParticipant).where(LegacyCaseParticipant.CaseNo == "SHMS2600001").order_by(LegacyCaseParticipant.SortingIndex))).all()
            logs = (await db.scalars(select(LegacyCaseLog).where(LegacyCaseLog.CaseNo == "SHMS2600001"))).all()
            self.assertEqual([(item.FileName, item.FileSize, item.IsTransmitted) for item in files], [("起诉状.pdf", 1024, "Y")])
            self.assertEqual([item.StaffName for item in participants], ["lawyer-a", "lszl2", "owner01"])
            self.assertEqual([item.Content for item in logs], ["提交立案：已提交"])


if __name__ == "__main__":
    unittest.main()

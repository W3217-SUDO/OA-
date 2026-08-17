"""Backend contract tests for concrete gap F (H/I/J/K backend items).

Fixtures are in-memory, uniquely marked, and removed in ``finally`` blocks.
"""
import uuid
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import DEFAULT_SYSTEM_MENUS, app
from app.models import (
    BusinessRecord,
    CommunicationLog,
    FileAttachment,
    FinanceTransaction,
    IncomingPayment,
    LawFirm,
    LawFirmAudit,
    LawFirmContact,
    ReceivablePlan,
    RolePermission,
    User,
    WorkflowEvent,
)
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "codex-f-admin", "role": "admin", "display_name": "F管理员", "department": "上海分所"}


class BackendGapFContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="test", is_active=True),
                RolePermission(role="admin", display_name="F管理员", data_scope="全所数据", menu_keys=["finance", "platform-finance", "documents", "investigation", "customer-conflict", "reports", "system"], field_keys=["finance.amount"]),
            ])
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://codex-f.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()

    async def _cleanup_records(self, record_ids, *, attachment_ids=(), file_paths=()):
        async with self.sessions() as db:
            for path in file_paths:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass
            if attachment_ids:
                await db.execute(delete(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))
            if record_ids:
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_(record_ids)))
                await db.execute(delete(FileAttachment).where(FileAttachment.record_id.in_(record_ids)))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_(record_ids)))
            await db.commit()

    async def _new_case(self, prefix, db, *, customer=""):
        case = BusinessRecord(module="case", serial_no=f"{prefix}-CASE", title=prefix, customer=customer, status="文书准备", owner=ADMIN["username"], department=ADMIN["department"])
        db.add(case)
        await db.flush()
        return case

    async def test_h1_upload_requires_document_date_and_persists_receipt_metadata(self):
        prefix = f"CODEX-F-H1-{uuid.uuid4().hex[:8]}"
        async with self.sessions() as db:
            case = await self._new_case(prefix, db)
            await db.commit()
            case_id = case.id
            case_no = case.serial_no
        attachment_ids = []
        record_ids = [case_id]
        file_paths = []
        try:
            missing = await self.client.post(f"{API}/documents/official/upload", data={"category": "收文附件", "remark": "x"}, files={"file": ("codex.pdf", b"codex", "application/pdf")})
            self.assertEqual(missing.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
            ok = await self.client.post(
                f"{API}/documents/official/upload",
                data={"document_date": "2026-08-05", "category": "收文附件", "remark": "x", "case_ids": str(case_id)},
                files={"file": ("codex.pdf", b"codex", "application/pdf")},
            )
            self.assertEqual(ok.status_code, status.HTTP_201_CREATED, ok.text)
            body = ok.json()
            record = body["record"]
            data = record["data"]
            self.assertEqual(data["document_date"], "2026-08-05")
            self.assertEqual(data["received_at"], "2026-08-05")
            self.assertEqual(data["uploaded_at"], "2026-08-05")
            self.assertEqual(data["case_ids"], [case_id])
            self.assertEqual(data["case_id"], case_id)
            self.assertEqual(data["case_no"], case_no)
            record_ids.append(record["id"])
            attachment_ids.append(body["attachment"]["id"])
            async with self.sessions() as db:
                attachment = await db.get(FileAttachment, body["attachment"]["id"])
                file_paths.append(attachment.path)
        finally:
            await self._cleanup_records(record_ids, attachment_ids=attachment_ids, file_paths=file_paths)

    async def test_h2_batch_case_ids_links_documents_and_writes_event(self):
        prefix = f"CODEX-F-H2-{uuid.uuid4().hex[:8]}"
        async with self.sessions() as db:
            documents = [
                BusinessRecord(module="document", serial_no=f"{prefix}-DOC-1", title=f"{prefix}-1", customer="", status="待签收", owner=ADMIN["username"], department=ADMIN["department"], data={"direction": "收文"}),
                BusinessRecord(module="document", serial_no=f"{prefix}-DOC-2", title=f"{prefix}-2", customer="", status="待签收", owner=ADMIN["username"], department=ADMIN["department"], data={"direction": "收文"}),
            ]
            cases = [await self._new_case(f"{prefix}-CASE-{index}", db) for index in range(1, 3)]
            db.add_all(documents)
            await db.commit()
            document_ids = [item.id for item in documents]
            case_ids = [item.id for item in cases]
            record_ids = document_ids + case_ids
        try:
            response = await self.client.post(f"{API}/documents/official/batch-case-ids", json={"record_ids": document_ids, "case_ids": case_ids})
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
            body = response.json()
            self.assertEqual(body["updated"], 2)
            self.assertEqual(body["case_ids"], case_ids)
            for item in body["items"]:
                self.assertEqual(item["data"]["case_ids"], case_ids)
            async with self.sessions() as db:
                events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id.in_(document_ids), WorkflowEvent.action == "批量关联案件"))).all())
                self.assertEqual(len(events), 2)
        finally:
            await self._cleanup_records(record_ids)

    async def test_i1_empty_conflict_returns_enterprise_name(self):
        query = f"CODEX-F-I1-{uuid.uuid4().hex[:8]}-不存在企业"
        response = await self.client.get(f"{API}/customers/conflicts", params={"name": query})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertFalse(body["found"])
        self.assertEqual(body["query"], query)
        self.assertEqual(body["enterprise_name"], query)

    async def test_i2_to_i4_investigation_task_contract_auth_scope_attachments_and_two_step(self):
        prefix = f"CODEX-F-I2-{uuid.uuid4().hex[:8]}"
        async with self.sessions() as db:
            clue = BusinessRecord(module="clue", serial_no=f"{prefix}-CLUE", title=prefix, customer="CODEX-F 客户", status="待取证", owner=ADMIN["username"], department=ADMIN["department"], data={"contract_no": "OLD-HT", "contract_name": "旧合同", "authorization_scope": "旧授权范围"})
            db.add(clue)
            await db.flush()
            attachment = FileAttachment(record_id=clue.id, category="调查资料", original_name="codex-a.pdf", stored_name=f"{uuid4().hex}.pdf", content_type="application/pdf", size=1, path="/tmp/codex-f-a.pdf", uploader=ADMIN["username"], remark="附件")
            db.add(attachment)
            await db.commit()
            clue_id, attachment_id = clue.id, attachment.id
        task_id = None
        try:
            response = await self.client.post(f"{API}/investigations/{clue_id}/tasks", json={
                "title": f"{prefix}-任务", "owner": ADMIN["username"], "deadline": (date.today() + timedelta(days=3)).isoformat(),
                "priority": "紧急", "description": "调查任务", "contract_no": f"{prefix}-HT", "contract_name": "专项调查合同",
                "authorization_scope": "华东区域授权", "attachment_ids": [attachment_id],
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.text)
            task = response.json()
            task_id = task["id"]
            self.assertEqual(task["contract_no"], f"{prefix}-HT")
            self.assertEqual(task["contract_name"], "专项调查合同")
            self.assertEqual(task["authorization_scope"], "华东区域授权")
            self.assertEqual(task["attachment_ids"], [attachment_id])
            accepted = await self.client.post(f"{API}/tasks/{task_id}/accept", json={"comment": "接收"})
            self.assertEqual(accepted.status_code, status.HTTP_200_OK, accepted.text)
            self.assertEqual(accepted.json()["status"], "处理中")
            completed = await self.client.post(f"{API}/tasks/{task_id}/complete", json={"comment": "完成"})
            self.assertEqual(completed.status_code, status.HTTP_200_OK, completed.text)
            self.assertEqual(completed.json()["status"], "已完成")
        finally:
            record_ids = [clue_id] + ([task_id] if task_id else [])
            await self._cleanup_records(record_ids, attachment_ids=[attachment_id])

    async def test_i5_to_i6_clue_review_persists_conflict_and_merge_fields(self):
        prefix = f"CODEX-F-I5-{uuid.uuid4().hex[:8]}"
        async with self.sessions() as db:
            clue = BusinessRecord(module="clue", serial_no=f"{prefix}-CLUE", title=prefix, customer="CODEX-F 客户", status="待审批", owner=ADMIN["username"], department=ADMIN["department"])
            merge_case = await self._new_case(prefix, db)
            db.add(clue)
            await db.commit()
            clue_id, case_id = clue.id, merge_case.id
        try:
            response = await self.client.post(f"{API}/investigations/clues/{clue_id}/review", json={
                "approved": True, "comment": "审批通过", "suspected_conflict_clue_nos": [f"{prefix}-OTHER-CLUE"],
                "suspected_conflict_case_nos": [f"{prefix}-CASE"], "supplement_evidence": "补充公证书", "merge_into_case_no": f"{prefix}-CASE",
            })
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
            data = response.json()["data"]
            self.assertEqual(data["suspected_conflict_clue_nos"], [f"{prefix}-OTHER-CLUE"])
            self.assertEqual(data["suspected_conflict_case_nos"], [f"{prefix}-CASE"])
            self.assertEqual(data["supplement_evidence"], "补充公证书")
            self.assertEqual(data["merge_into_case_no"], f"{prefix}-CASE")
            self.assertEqual(data["merge_into_case_id"], case_id)
        finally:
            await self._cleanup_records([clue_id, case_id])

    async def test_i7_to_i9_evidence_registration_list_files_import_and_update(self):
        prefix = f"CODEX-F-I7-{uuid.uuid4().hex[:8]}"
        async with self.sessions() as db:
            clue = BusinessRecord(module="clue", serial_no=f"{prefix}-CLUE", title=prefix, customer="CODEX-F 客户", status="待取证", owner=ADMIN["username"], department=ADMIN["department"])
            db.add(clue)
            await db.flush()
            attachment = FileAttachment(record_id=clue.id, category="网页截图", original_name="codex-screen.png", stored_name=f"{uuid4().hex}.png", content_type="image/png", size=1, path="/tmp/codex-f-screen.png", uploader=ADMIN["username"], remark="截图")
            db.add(attachment)
            await db.commit()
            clue_id, attachment_id = clue.id, attachment.id
        created_ids = []
        try:
            created = await self.client.post(f"{API}/investigations/clues/{clue_id}/evidence", json={
                "title": f"{prefix}-证据", "owner": ADMIN["username"], "source": "调查取证", "description": "证据说明",
                "notarization_no": "GZ-001", "invoice_no": "FP-001", "storage_location": "行政仓 A-01", "storage_state": "待整理",
                "evidence_file_ids": [attachment_id],
            })
            self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
            created_data = created.json()["data"]
            self.assertEqual(created_data["notarization_no"], "GZ-001")
            self.assertEqual(created_data["invoice_no"], "FP-001")
            self.assertEqual(created_data["storage_location"], "行政仓 A-01")
            self.assertEqual(created_data["storage_state"], "待整理")
            self.assertEqual(created_data["evidence_file_ids"], [attachment_id])
            created_ids.append(created.json()["id"])

            single = await self.client.post(f"{API}/evidence/register", json={
                "title": f"{prefix}-单证", "owner": ADMIN["username"], "source": "调查取证", "clue_id": clue_id,
                "notarization_no": "GZ-002", "invoice_no": "FP-002", "storage_location": "B-02", "storage_state": "待整理",
            })
            self.assertEqual(single.status_code, status.HTTP_201_CREATED, single.text)
            created_ids.append(single.json()["id"])

            batch = await self.client.post(f"{API}/evidence/batch-register", json={"items": [
                {"title": f"{prefix}-批1", "owner": ADMIN["username"], "source": "调查取证", "clue_id": clue_id, "storage_location": "C-01"},
                {"title": f"{prefix}-批2", "owner": ADMIN["username"], "source": "调查取证", "clue_id": clue_id, "storage_location": "C-02"},
            ]})
            self.assertEqual(batch.status_code, status.HTTP_201_CREATED, batch.text)
            self.assertEqual(batch.json()["created"], 2)
            created_ids.extend(batch.json()["created_ids"])

            listing = await self.client.get(f"{API}/evidence", params={"keyword": prefix, "page": 1, "page_size": 2})
            self.assertEqual(listing.status_code, status.HTTP_200_OK)
            self.assertEqual(listing.json()["page"], 1)
            self.assertEqual(listing.json()["page_size"], 2)
            self.assertGreaterEqual(listing.json()["total"], 4)

            evidence_id = created_ids[0]
            async with self.sessions() as db:
                evidence_attachment = FileAttachment(record_id=evidence_id, category="证据文件", original_name="codex-e.pdf", stored_name=f"{uuid4().hex}.pdf", content_type="application/pdf", size=1, path="/tmp/codex-f-e.pdf", uploader=ADMIN["username"], remark="证据文件")
                db.add(evidence_attachment)
                await db.commit()
                evidence_attachment_id = evidence_attachment.id
            files = await self.client.get(f"{API}/evidence/{evidence_id}/files")
            self.assertEqual(files.status_code, status.HTTP_200_OK)
            self.assertEqual(files.json()["total"], 1)

            csv_content = f"证据标题,关联线索编号,负责人,材料来源,说明,公证编号,发票号,存放位置,存放状态\r\n{prefix}-导入证据,{prefix}-CLUE,{ADMIN['username']},调查取证,导入说明,GZ-003,FP-003,D-01,待整理\r\n"
            imported = await self.client.post(f"{API}/evidence/import", files={"file": ("evidence.csv", csv_content.encode("utf-8"), "text/csv")})
            self.assertEqual(imported.status_code, status.HTTP_201_CREATED, imported.text)
            self.assertEqual(imported.json()["created"], 1)

            updated = await self.client.put(f"{API}/investigations/evidence/{evidence_id}", json={"notarization_no": "GZ-999", "storage_state": "已整理", "source": "补充取证"})
            self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.text)
            updated_data = updated.json()["data"]
            self.assertEqual(updated_data["notarization_no"], "GZ-999")
            self.assertEqual(updated_data["storage_state"], "已整理")
        finally:
            async with self.sessions() as db:
                imported_ids = list((await db.scalars(select(BusinessRecord.id).where(BusinessRecord.module == "evidence", BusinessRecord.title.like(f"{prefix}%")))).all())
                created_ids = list(dict.fromkeys(created_ids + imported_ids))
            await self._cleanup_records(created_ids + [clue_id], attachment_ids=[attachment_id])

    async def test_i10_parties_are_multi_record_composite(self):
        prefix = f"CODEX-F-I10-{uuid.uuid4().hex[:8]}"
        async with self.sessions() as db:
            record = BusinessRecord(module="investigation", serial_no=f"{prefix}-INV", title=prefix, customer="CODEX-F 客户", status="处理中", owner=ADMIN["username"], department=ADMIN["department"])
            db.add(record)
            await db.commit()
            record_id = record.id
        try:
            response = await self.client.post(f"{API}/investigations/{record_id}/parties", json={
                "producers": [{"name": "生产者甲", "type": "个人"}],
                "indictees": [{"name": "被控方乙", "type": "公司"}],
            })
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
            data = response.json()["record"]["data"]
            self.assertEqual(data["producers"], [{"name": "生产者甲", "type": "个人"}])
            self.assertEqual(data["indictees"], [{"name": "被控方乙", "type": "公司"}])
            listed = await self.client.get(f"{API}/investigations/{record_id}/parties")
            self.assertEqual(listed.status_code, status.HTTP_200_OK)
            self.assertEqual(listed.json()["producers"], [{"name": "生产者甲", "type": "个人"}])
            self.assertEqual(listed.json()["indictees"], [{"name": "被控方乙", "type": "公司"}])
        finally:
            await self._cleanup_records([record_id])

    async def test_j1_warehouse_goods_list_legacy_pagination(self):
        prefix = f"CODEX-F-J1-{uuid.uuid4().hex[:8]}"
        async with self.sessions() as db:
            records = [
                BusinessRecord(module="warehouse", serial_no=f"{prefix}-W-{index}", title=f"{prefix} 物品{index}", customer="CODEX-F 客户", status="在库", owner=ADMIN["username"], department=ADMIN["department"], data={
                    "location": f"A-0{index}", "clue_no": f"{prefix}-CLUE-{index}", "notary_no": f"GZ-{index}",
                    "case_no": f"{prefix}-CASE-{index}", "shop_name": f"{prefix} 店铺{index}", "investigator": ADMIN["username"],
                    "notary_office": "公证处", "rights_holder": "权利方", "evidence_date": "2026-08-01", "warehouse": "行政仓",
                })
                for index in range(1, 4)
            ]
            db.add_all(records)
            await db.commit()
            record_ids = [item.id for item in records]
        try:
            response = await self.client.post(f"{API}/WMS/Warehouse/GoodsList", json={"SearchCondition": {"PageNo": 2, "PageSize": 1}})
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
            body = response.json()
            self.assertEqual(body["PageNo"], 2)
            self.assertEqual(body["PageSize"], 1)
            self.assertEqual(body["TotalItemCount"], 3)
            self.assertEqual(len(body["GoodsList"]), 1)
            row = body["GoodsList"][0]
            self.assertIn("EvidenceNo", row)
            self.assertIn("StorageLocation", row)
            self.assertIn("NotarialNo", row)
            self.assertIn("CaseNo", row)
            self.assertIn("GoodsStatusName", row)
        finally:
            await self._cleanup_records(record_ids)

    async def test_j2_j4_finance_row_level_detail_view_assigned_and_create_claim_flow(self):
        prefix = f"CODEX-F-J2-{uuid.uuid4().hex[:8]}"
        async with self.sessions() as db:
            customer = BusinessRecord(module="customer", serial_no=f"{prefix}-CUST", title=f"{prefix} 客户", customer=f"{prefix} 客户", status="正常", owner=ADMIN["username"], department=ADMIN["department"])
            contract = BusinessRecord(module="contract", serial_no=f"{prefix}-HT", title=f"{prefix} 合同", customer=f"{prefix} 客户", status="审批通过", owner=ADMIN["username"], department=ADMIN["department"], data={"amount": 1000})
            db.add_all([customer, contract])
            await db.flush()
            case = BusinessRecord(module="case", serial_no=f"{prefix}-CASE", title=f"{prefix} 案件", customer=f"{prefix} 客户", status="文书准备", owner=ADMIN["username"], department=ADMIN["department"], data={"contract_id": contract.id})
            db.add(case)
            await db.flush()
            plan = ReceivablePlan(contract_record_id=contract.id, phase="首付款", due_date=date(2026, 8, 20), amount=500, received_amount=0, status="待收款", payer=f"{prefix} 客户")
            db.add(plan)
            await db.commit()
            customer_id, contract_id, case_id, plan_id = customer.id, contract.id, case.id, plan.id
        payment_id = None
        try:
            created = await self.client.post(f"{API}/finance/incoming-payments", json={
                "received_date": "2026-08-05", "amount": 200, "payer_name": f"{prefix} 付款方", "bank_reference": f"{prefix}-BANK-1",
                "customer": f"{prefix} 客户", "contract_no": f"{prefix}-HT", "case_no": f"{prefix}-CASE",
                "bank_source": "CMB", "claim": True, "remark": "回款登记",
            })
            self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
            payment = created.json()
            payment_id = payment["id"]
            self.assertEqual(payment["status"], "待分配")
            self.assertEqual(payment["claimed_customer"], f"{prefix} 客户")
            self.assertEqual(payment["contract_no"], f"{prefix}-HT")
            self.assertEqual(payment["case_no"], f"{prefix}-CASE")
            self.assertEqual(payment["bank_source"], "CMB")

            detail = await self.client.get(f"{API}/finance/incoming-payments/{payment_id}")
            self.assertEqual(detail.status_code, status.HTTP_200_OK)
            self.assertEqual(detail.json()["receipt_no"], payment["receipt_no"])

            allocated = await self.client.post(f"{API}/finance/incoming-payments/{payment_id}/allocate", json={
                "allocations": [{"receivable_plan_id": plan_id, "amount": 200, "case_no": f"{prefix}-CASE", "payment_method": "银行转账"}],
                "comment": "分配",
            })
            self.assertEqual(allocated.status_code, status.HTTP_200_OK, allocated.text)
            self.assertEqual(allocated.json()["status"], "已分配")

            view = await self.client.get(f"{API}/finance/incoming-payments/{payment_id}/view-assigned")
            self.assertEqual(view.status_code, status.HTTP_200_OK)
            view_body = view.json()
            self.assertEqual(view_body["total"], 1)
            self.assertEqual(view_body["items"][0]["contract"]["serial_no"], f"{prefix}-HT")
            self.assertEqual(view_body["items"][0]["case"]["serial_no"], f"{prefix}-CASE")
            self.assertEqual(view_body["payment"]["id"], payment_id)
        finally:
            async with self.sessions() as db:
                if payment_id:
                    payment = await db.get(IncomingPayment, payment_id)
                    if payment:
                        await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == contract_id, FinanceTransaction.voucher_no == payment.bank_reference))
                        await db.execute(delete(IncomingPayment).where(IncomingPayment.id == payment_id))
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_([customer_id, contract_id, case_id])))
                await db.execute(delete(ReceivablePlan).where(ReceivablePlan.id == plan_id))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_([customer_id, contract_id, case_id])))
                await db.commit()

    async def test_j3_j5_j6_menu_seeds_bank_source_and_excel_export(self):
        prefix = f"CODEX-F-J3-{uuid.uuid4().hex[:8]}"
        menu_keys = {item[0] for item in DEFAULT_SYSTEM_MENUS}
        self.assertIn("platform-finance-overview-cmb", menu_keys)
        self.assertIn("platform-finance-overview-gdicbc", menu_keys)
        self.assertIn("reports-large-screen", menu_keys)
        async with self.sessions() as db:
            payment = IncomingPayment(receipt_no=f"{prefix}-RECEIPT", received_date=date(2026, 8, 5), amount=88, payer_name=f"{prefix} 付款方", bank_reference=f"{prefix}-BANK", status="待认领", bank_source="GDICBC", operator=ADMIN["username"], remark="银行来源")
            db.add(payment)
            await db.commit()
            payment_id = payment.id
        try:
            export = await self.client.get(f"{API}/finance/incoming-payments/export")
            self.assertEqual(export.status_code, status.HTTP_200_OK)
            self.assertIn("application/vnd.ms-excel", export.headers.get("content-type", ""))
            self.assertIn(f"{prefix}-RECEIPT".encode("utf-8"), export.content)
            self.assertIn("GDICBC".encode("utf-8"), export.content)
        finally:
            async with self.sessions() as db:
                await db.execute(delete(IncomingPayment).where(IncomingPayment.id == payment_id))
                await db.commit()

    async def test_k1_communication_history_filter_by_customer(self):
        prefix = f"CODEX-F-K1-{uuid.uuid4().hex[:8]}"
        async with self.sessions() as db:
            first = BusinessRecord(module="customer", serial_no=f"{prefix}-C1", title=f"{prefix} 客户一", customer=f"{prefix} 客户一", status="正常", owner=ADMIN["username"], department=ADMIN["department"])
            second = BusinessRecord(module="customer", serial_no=f"{prefix}-C2", title=f"{prefix} 客户二", customer=f"{prefix} 客户二", status="正常", owner=ADMIN["username"], department=ADMIN["department"])
            db.add_all([first, second])
            await db.flush()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            logs = [
                CommunicationLog(customer_record_id=first.id, customer_name=first.title, contact="甲", phone="1", content="第一沟通", occurred_at=now, operator=ADMIN["username"]),
                CommunicationLog(customer_record_id=second.id, customer_name=second.title, contact="乙", phone="2", content="第二沟通", occurred_at=now, operator=ADMIN["username"]),
            ]
            db.add_all(logs)
            await db.commit()
            first_id, second_id = first.id, second.id
            log_ids = [item.id for item in logs]
        try:
            response = await self.client.get(f"{API}/communications", params={"customer_record_id": first_id, "mine_only": "false"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            body = response.json()
            self.assertEqual(body["total"], 1)
            self.assertEqual(body["items"][0]["customer_record_id"], first_id)
            missing = await self.client.get(f"{API}/communications", params={"customer_record_id": 99999999, "mine_only": "false"})
            self.assertEqual(missing.json()["total"], 0)
        finally:
            async with self.sessions() as db:
                await db.execute(delete(CommunicationLog).where(CommunicationLog.id.in_(log_ids)))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_([first_id, second_id])))
                await db.commit()

    async def test_k2_k4_k6_law_firm_fields_nested_contact_and_audits(self):
        prefix = f"CODEX-F-K2-{uuid.uuid4().hex[:8]}"
        law_firm_id = None
        contact_ids = []
        try:
            created = await self.client.post(f"{API}/law-firms", json={
                "code": f"LF-{prefix}", "name": f"{prefix} 律所", "firm_type": "专利代理", "firm_level": "重点",
                "registered_address": "上海市", "default_contact": {"name": "联系人甲", "phone": "13800000000"},
            })
            self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
            body = created.json()
            law_firm_id = body["id"]
            self.assertEqual(body["firm_type"], "专利代理")
            self.assertEqual(body["firm_level"], "重点")
            self.assertEqual(len(body["contacts"]), 1)
            self.assertEqual(body["default_contact"]["name"], "联系人甲")
            self.assertEqual(body["default_contact_id"], body["contacts"][0]["id"])
            contact_ids.append(body["contacts"][0]["id"])
            audits = await self.client.get(f"{API}/law-firms/{law_firm_id}/audits")
            self.assertEqual(audits.status_code, status.HTTP_200_OK)
            self.assertEqual(audits.json()["total"], 1)
            self.assertEqual(audits.json()["items"][0]["action"], "新建律所档案")
        finally:
            if law_firm_id:
                async with self.sessions() as db:
                    await db.execute(delete(LawFirmAudit).where(LawFirmAudit.law_firm_id == law_firm_id))
                    await db.execute(delete(LawFirmContact).where(LawFirmContact.id.in_(contact_ids)))
                    await db.execute(delete(LawFirm).where(LawFirm.id == law_firm_id))
                    await db.commit()

    async def test_k3_law_firm_license_upload_multipart(self):
        prefix = f"CODEX-F-K3-{uuid.uuid4().hex[:8]}"
        law_firm_id = None
        attachment_id = None
        file_path = None
        try:
            created = await self.client.post(
                f"{API}/law-firms",
                data={"code": f"LF-{prefix}", "name": f"{prefix} 律所", "firm_type": "律师事务所", "firm_level": "普通"},
                files={"file": ("license.png", b"codex-license", "image/png")},
            )
            self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
            body = created.json()
            law_firm_id = body["id"]
            self.assertIsNotNone(body["license_attachment_id"])
            self.assertEqual(body["license"]["original_name"], "license.png")
            attachment_id = body["license_attachment_id"]
            async with self.sessions() as db:
                attachment = await db.get(FileAttachment, attachment_id)
                file_path = attachment.path if attachment else None
        finally:
            if law_firm_id:
                async with self.sessions() as db:
                    if attachment_id:
                        attachment = await db.get(FileAttachment, attachment_id)
                        if attachment:
                            file_path = attachment.path
                        await db.execute(delete(FileAttachment).where(FileAttachment.id == attachment_id))
                    await db.execute(delete(LawFirmAudit).where(LawFirmAudit.law_firm_id == law_firm_id))
                    await db.execute(delete(LawFirm).where(LawFirm.id == law_firm_id))
                    await db.commit()
            if file_path:
                try:
                    Path(file_path).unlink(missing_ok=True)
                except OSError:
                    pass

    async def test_k5_law_firm_server_side_pagination(self):
        prefix = f"CODEX-F-K5-{uuid.uuid4().hex[:8]}"
        async with self.sessions() as db:
            firms = [LawFirm(code=f"LF-{prefix}-{index}", name=f"{prefix} 律所{index}", firm_type="律师事务所", firm_level="普通", created_by=ADMIN["username"], updated_by=ADMIN["username"]) for index in range(1, 4)]
            db.add_all(firms)
            await db.commit()
            firm_ids = [item.id for item in firms]
        try:
            response = await self.client.get(f"{API}/law-firms", params={"page": 2, "page_size": 2, "include_inactive": "true"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            body = response.json()
            self.assertEqual(body["page"], 2)
            self.assertEqual(body["page_size"], 2)
            self.assertGreaterEqual(body["total"], 3)
            self.assertEqual(len(body["items"]), 1)
        finally:
            async with self.sessions() as db:
                await db.execute(delete(LawFirmAudit).where(LawFirmAudit.law_firm_id.in_(firm_ids)))
                await db.execute(delete(LawFirmContact).where(LawFirmContact.law_firm_id.in_(firm_ids)))
                await db.execute(delete(LawFirm).where(LawFirm.id.in_(firm_ids)))
                await db.commit()
if __name__ == "__main__":
    unittest.main()

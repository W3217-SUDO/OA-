"""9.18 批次接口与持久化回归，仅使用独立内存数据库。"""
import unittest
from datetime import date, timedelta
from sqlalchemy import delete, select
from fastapi import HTTPException
import finance_0916_batch_test as fixtures
from finance_0916_batch_test import API, IDENTITY
from app.models import BusinessRecord, IncomingPayment, WorkflowEvent, HearingSchedule, RolePermission, User


class Batch0918Test(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.FinanceBatchTest.asyncSetUp
    asyncTearDown = fixtures.FinanceBatchTest.asyncTearDown

    async def add_clue(self, **changes):
        async with self.sessions() as db:
            clue = BusinessRecord(module="clue", serial_no=changes.pop("serial_no", "CODEX-0918-clue"),
                title="线索", customer="Batch customer", owner=IDENTITY["username"],
                status=changes.pop("status", "已取证"), data=changes)
            db.add(clue); await db.commit()
            return clue.id

    async def test_court_required_and_partial_update(self):
        url = f"{API}/cases/{self.case_id}/court-info"
        for level in ("first", "second", "execution", "retrial"):
            response = await self.client.put(url, json={f"{level}_court_filing_date": "2026-09-18"})
            self.assertEqual(response.status_code, 422, response.text)
            response = await self.client.put(url, json={f"{level}_court_name": "法院"})
            self.assertEqual(response.status_code, 200, response.text)
            response = await self.client.put(url, json={f"{level}_court_filing_date": "2026-09-18"})
            self.assertEqual(response.status_code, 200, response.text)
            response = await self.client.put(url, json={f"{level}_court_name": " "})
            self.assertEqual(response.status_code, 422, response.text)

    async def test_source_contract_certificate_warehouse_and_manual_priority(self):
        clue_id = await self.add_clue(certificate_no="公证一", storage_location="一仓/16", investigation_no="CODEX-0918-investigation")
        async with self.sessions() as db:
            db.add(BusinessRecord(module="investigation", serial_no="CODEX-0918-investigation", title="调查", customer="Batch customer", owner=IDENTITY["username"], data={"contract_id": 999999, "contract_no": "CODEX-0916-contract", "contract_name": "同名合同"}))
            contract = await db.get(BusinessRecord, self.contract_id)
            contract.title = "同名合同"
            db.add(BusinessRecord(module="contract", serial_no="CODEX-0918-same-name", title="同名合同", customer="Batch customer", owner=IDENTITY["username"], data={}))
            case = await db.get(BusinessRecord, self.case_id)
            case.data = {**case.data, "investigation_clue_ids": [clue_id]}; await db.commit()
        result = await self.client.get(f"{API}/cases/{self.case_id}/relations")
        self.assertEqual(result.status_code, 200, result.text)
        data = result.json()["case_data"]
        self.assertEqual(data["contract_id"], self.contract_id)
        self.assertEqual(data["notary_no"], "公证一")
        self.assertEqual(data["warehouse_location"], "一仓/16")
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.data = {**case.data, "notary_no": "人工公证", "deposit_address": "人工库位"}; await db.commit()
        result = await self.client.get(f"{API}/cases/{self.case_id}/relations")
        self.assertEqual(result.json()["case_data"]["notary_no"], "人工公证")
        self.assertNotIn("warehouse_location", result.json()["case_data"])

    async def test_party_candidates_company_keyword(self):
        async with self.sessions() as db:
            db.add(BusinessRecord(module="customer", serial_no="CODEX-0918-party", title="当事人关键词", owner="another", status="有效", data={}))
            await db.commit()
        result = await self.client.get(f"{API}/case-litigant-candidates", params={"keyword": "关键词"})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual([row["title"] for row in result.json()["items"]], ["当事人关键词"])
        self.assertNotIn("data", result.json()["items"][0])

    async def test_clue_eligibility_and_preserved_binding(self):
        from app.core.case_relations import validate_case_clues
        eligible = await self.add_clue()
        invalid = await self.add_clue(serial_no="CODEX-0918-unapproved", status="待审核")
        used = await self.add_clue(serial_no="CODEX-0918-used", converted_case_id=999)
        result = await self.client.get(f"{API}/cases/{self.case_id}/clue-candidates")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual([row["id"] for row in result.json()["items"]], [eligible])
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            for clue_id in (invalid, used):
                with self.assertRaises(HTTPException):
                    await validate_case_clues(case, [await db.get(BusinessRecord, clue_id)], case.customer, db)
            case.data = {**case.data, "investigation_clue_ids": [invalid]}
            await validate_case_clues(case, [await db.get(BusinessRecord, invalid)], case.customer, db)

    async def test_selected_clue_task_and_cross_case_rejection(self):
        clue_id = await self.add_clue(certificate_no="公证选中")
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.data = {**case.data, "investigation_clue_ids": [clue_id]}; await db.commit()
        body = {"title": "公证书领取", "owner": IDENTITY["username"], "deadline": str(date.today()+timedelta(days=10)),
                "source": "案件任务", "case_no": "CODEX-0916-case", "clue_ids": [clue_id]}
        result = await self.client.post(f"{API}/tasks", json=body)
        self.assertEqual(result.status_code, 201, result.text)
        async with self.sessions() as db:
            task = await db.get(BusinessRecord, result.json()["id"])
            self.assertEqual(task.data["clue_ids"], [clue_id])
            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == task.id))
            self.assertIn("协作人(无)", event.comment)
            self.assertIn("公证选中", event.comment)
        result = await self.client.post(f"{API}/tasks", json={**body, "clue_ids": [99999]})
        self.assertEqual(result.status_code, 409, result.text)

    async def test_merge_all_relations_and_keep_main_values(self):
        clue_id = await self.add_clue(certificate_no="来源公证")
        async with self.sessions() as db:
            source = BusinessRecord(module="case", serial_no="CODEX-0918-source", title="来源案件", customer="Batch customer", owner=IDENTITY["username"], status="一审准备开庭", data={"case_type": "民事争议", "contract_no": "来源合同", "investigation_clue_ids": [clue_id]})
            db.add(source); await db.flush(); source_id = source.id
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, "case_id": 99999, "case_no": source.serial_no}
            task = BusinessRecord(module="task", serial_no="CODEX-0918-source-task", title="任务", owner=IDENTITY["username"], data={"case_id": source.id, "case_no": source.serial_no, "case_ids": [source.id]})
            db.add_all([task, WorkflowEvent(record_id=source.id, action="来源历史", operator=IDENTITY["username"]),
                HearingSchedule(case_record_id=source.id, hearing_date=date.today(), hearing_time="09:00", court="来源法院", hearing_lawyer=IDENTITY["username"])])
            await db.commit(); task_id = task.id
        result = await self.client.post(f"{API}/cases/{self.case_id}/merge", json={"source_case_no": "CODEX-0918-source"})
        self.assertEqual(result.status_code, 200, result.text)
        original_id = self.case_id
        self.case_id = result.json()["target"]["id"]
        self.assertNotEqual(self.case_id, original_id)
        self.assertNotEqual(result.json()["target"]["serial_no"], "CODEX-0916-case")
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            self.assertNotEqual(case.data.get("contract_no"), "来源合同")
            self.assertEqual(next(item for item in case.data["merged_sources"] if item["id"] == source_id)["data"]["contract_no"], "来源合同")
            self.assertIn(clue_id, case.data["investigation_clue_ids"])
            self.assertEqual((await db.get(BusinessRecord, self.fee_id)).data["case_id"], self.case_id)
            self.assertEqual((await db.get(BusinessRecord, task_id)).data["case_ids"], [self.case_id])
            self.assertEqual((await db.get(BusinessRecord, source_id)).status, "已合并")
            self.assertEqual((await db.scalar(select(HearingSchedule))).case_record_id, self.case_id)
            self.assertIsNotNone(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id, WorkflowEvent.action == "来源历史")))

    async def test_merge_three_contract_and_five_case_documents(self):
        from app.models import FileAttachment
        async with self.sessions() as db:
            contract = BusinessRecord(module="contract", serial_no="CODEX-0918-doc-contract",
                title="来源合同", customer="Batch customer", owner=IDENTITY["username"], data={})
            db.add(contract)
            await db.flush()
            source = BusinessRecord(module="case", serial_no="CODEX-0918-doc-source",
                title="来源案件", customer="Batch customer", owner=IDENTITY["username"],
                status="一审准备开庭", data={"case_type": "民事争议", "contract_id": contract.id,
                    "contract_no": contract.serial_no})
            db.add(source)
            await db.flush()
            files = [FileAttachment(record_id=record.id, category=category,
                original_name=f"{category}-{i}.txt", stored_name=f"CODEX-0918-doc-{record.id}-{i}",
                path="isolated-unused", size=1, uploader=IDENTITY["username"])
                for record, category, count in ((contract, "合同附件", 3), (source, "案件资料", 5))
                for i in range(count)]
            db.add_all(files)
            await db.commit()
            contract_id = contract.id
            file_ids = {file.id for file in files}
        result = await self.client.post(f"{API}/cases/{self.case_id}/merge",
            json={"source_case_no": "CODEX-0918-doc-source"})
        self.assertEqual(result.status_code, 200, result.text)
        original_id = self.case_id
        self.case_id = result.json()["target"]["id"]
        self.assertNotEqual(self.case_id, original_id)
        self.assertNotEqual(result.json()["target"]["serial_no"], "CODEX-0916-case")
        response = await self.client.get(f"{API}/cases/{self.case_id}/documents")
        self.assertEqual(response.status_code, 200, response.text)
        files = response.json()["items"]
        self.assertEqual({file["id"] for file in files}, file_ids)
        self.assertEqual(sum(file["document_category"] == "合同文档" for file in files), 3)
        self.assertEqual(sum(file["document_category"] == "案件资料" for file in files), 5)
        for file in files:
            expected = contract_id if file["document_category"] == "合同文档" else self.case_id
            self.assertEqual(file["record_id"], expected)
            metadata = await self.client.get(f"{API}/attachments/{file['id']}")
            self.assertEqual(metadata.status_code, 200, metadata.text)
        async with self.sessions() as db:
            self.assertEqual(len((await db.scalars(select(FileAttachment))).all()), 8)

    async def test_non_draft_fee_delete_and_accounting_guards(self):
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id); fee.status = "已审批"
            await db.commit()
        result = await self.client.delete(f"{API}/finance/fees/{self.fee_id}")
        self.assertEqual(result.status_code, 409, result.text)
        async with self.sessions() as db:
            await db.execute(delete(IncomingPayment)); await db.commit()
        result = await self.client.delete(f"{API}/finance/fees/{self.fee_id}")
        self.assertEqual(result.status_code, 204, result.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, self.fee_id)).status, "已删除")
            self.assertIsNotNone(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.fee_id, WorkflowEvent.action == "删除费用")))

    async def test_personal_dashboard_same_queue_and_unique_case(self):
        async with self.sessions() as db:
            await db.execute(delete(IncomingPayment))
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, "fee_type": "官方费用", "refund_requested_amount": 50, "refund_status": "R10"}
            db.add(BusinessRecord(module="finance", serial_no="CODEX-0918-refund2", title="第二条退费", owner=IDENTITY["username"], data={**fee.data}))
            await db.commit()
        result = await self.client.get(f"{API}/dashboard/personal-queues/refund-pending")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["total"], 1)
        metrics = await self.client.get(f"{API}/dashboard", params={"section": "metrics"})
        self.assertEqual(metrics.status_code, 200, metrics.text)
        refund = next(item for item in metrics.json()["metrics"] if item["key"] == "refund-pending")
        self.assertEqual(refund["value"], "1件")

    async def test_fee_explicit_role_action_even_with_page_capability(self):
        from app.core.cases import _case_action_granted
        from app.core.permissions import _system_permission_tree
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == IDENTITY["username"]))
            user.role = "user"; user.role_ids = ["user"]
            role = RolePermission(role="user", display_name="回归律师", menu_keys=["case-mine"], field_keys=[], data_scope="本人及共享数据")
            db.add(role); await db.commit()
            identity = {**IDENTITY, "role": "user", "role_ids": ["user"], "_page_menu_capability": True}
            self.assertFalse(await _case_action_granted(identity, db, "case.fee.update"))
            self.assertFalse(await _case_action_granted(identity, db, "case.fee.delete"))
            role.menu_keys = ["case-mine", "@action:case.fee.update"]; await db.commit()
            self.assertTrue(await _case_action_granted(identity, db, "case.fee.update"))
            self.assertFalse(await _case_action_granted(identity, db, "case.fee.delete"))
            tree = await _system_permission_tree(db, role)
            self.assertIn("case.fee.update", str(tree))

    async def test_personal_queue_without_company_or_finance_menu(self):
        from app.core.dashboard_personal_queues import personal_queues
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == IDENTITY["username"]))
            user.role = "user"; user.role_ids = ["user"]
            db.add(RolePermission(role="user", display_name="回归律师", menu_keys=["dashboard", "case-mine"], field_keys=[], data_scope="本人及共享数据"))
            await db.execute(delete(IncomingPayment))
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.owner = "another"
            fee.data = {**fee.data, "fee_type": "官方费用", "refund_requested_amount": 50, "refund_status": "R10"}
            db.add(BusinessRecord(module="case", serial_no="CODEX-0918-other-case", title="无关案件", customer="Batch customer", owner="another", status="待上诉", data={}))
            await db.commit()
            queues = await personal_queues({**IDENTITY, "role": "user", "role_ids": ["user"]}, db)
            self.assertEqual(len(queues["refund-pending"]), 1)
            self.assertEqual(queues["appeal-pending"], [])

    async def test_scoped_repair_preview_apply_idempotence_and_restore(self):
        import io
        import json
        import tempfile
        from argparse import Namespace
        from contextlib import redirect_stdout
        from pathlib import Path
        from unittest.mock import patch
        from scripts import repair_case_relations as migration
        clue_id = await self.add_clue(investigation_no="CODEX-0918-repair-investigation")
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.data = {**case.data, "investigation_clue_ids": [clue_id]}
            db.add(BusinessRecord(module="investigation", serial_no="CODEX-0918-repair-investigation", title="调查", customer=case.customer, owner=IDENTITY["username"], data={"contract_no": "CODEX-0916-contract", "contract_id": 99999}))
            source = BusinessRecord(module="case", serial_no="CODEX-0918-repair-source", title="旧合并来源", customer=case.customer, owner=IDENTITY["username"], status="已合并", data={"case_type": "民事争议", "merged_into_case_no": case.serial_no})
            db.add(source); await db.flush()
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, "case_id": 99999, "case_no": source.serial_no, "contract_id": 99999, "contract_no": "CODEX-0916-contract"}
            await db.commit()
        spec = {"source_contract_cases": ["CODEX-0916-case"], "existing_merges": [{"source": "CODEX-0918-repair-source", "target": "CODEX-0916-case"}], "fee_contracts": [{"fee_no": "CODEX-0916-fee", "contract_no": "CODEX-0916-contract"}]}
        with tempfile.TemporaryDirectory(prefix="oa0918-") as directory:
            root = Path(directory); spec_file = root / "spec.json"; backup_file = root / "backup.json"; receipt_file = root / "receipt.json"
            spec_file.write_text(json.dumps(spec), encoding="utf-8")
            with patch.object(migration, "SessionLocal", self.sessions):
                output = io.StringIO()
                with redirect_stdout(output):
                    await migration.run(Namespace(mode="plan", input=str(spec_file)))
                backup_file.write_text(output.getvalue(), encoding="utf-8")
                backup = json.loads(output.getvalue())
                self.assertIn("business_records", backup["tables"])
                async with self.sessions() as db:
                    self.assertNotIn("contract_no", (await db.get(BusinessRecord, self.case_id)).data)
                output = io.StringIO()
                with redirect_stdout(output):
                    await migration.run(Namespace(mode="apply", input=str(backup_file)))
                receipt_file.write_text(output.getvalue(), encoding="utf-8")
                async with self.sessions() as db:
                    case = await db.get(BusinessRecord, self.case_id)
                    self.assertEqual(case.data["contract_no"], "CODEX-0916-contract")
                    self.assertEqual((await db.get(BusinessRecord, self.fee_id)).data["case_id"], self.case_id)
                    second = await migration.plan(spec, db)
                    self.assertEqual(second["tables"], {})
                    await db.rollback()
                with redirect_stdout(io.StringIO()):
                    await migration.run(Namespace(mode="restore", input=str(backup_file), receipt=str(receipt_file)))
                async with self.sessions() as db:
                    self.assertNotIn("contract_no", (await db.get(BusinessRecord, self.case_id)).data)
                    self.assertEqual((await db.get(BusinessRecord, self.fee_id)).data["case_id"], 99999)

    async def test_paid_invoiced_fees_cannot_be_deleted(self):
        async with self.sessions() as db:
            await db.execute(delete(IncomingPayment))
            await db.commit()
        for field, message in (("paid_amount", "取消付款"), ("invoiced_amount", "作废关联发票")):
            async with self.sessions() as db:
                fee = await db.get(BusinessRecord, self.fee_id)
                fee.status = "已审批"
                fee.data = {**fee.data, "paid_amount": 0, "invoiced_amount": 0, field: 10}
                await db.commit()
            result = await self.client.delete(f"{API}/finance/fees/{self.fee_id}")
            self.assertEqual(result.status_code, 409, result.text)
            self.assertIn(message, result.text)
            async with self.sessions() as db:
                self.assertEqual((await db.get(BusinessRecord, self.fee_id)).status, "已审批")


if __name__ == "__main__":
    unittest.main()

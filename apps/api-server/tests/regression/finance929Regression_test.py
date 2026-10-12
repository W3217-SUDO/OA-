"""9.29 第2、3、8–12行：隔离数据库中的真实鉴权、API及持久化回归。"""
import asyncio
import io
import os
from pathlib import Path
import unittest
from datetime import date
from unittest.mock import patch
from zipfile import ZipFile

import httpx
from fastapi import HTTPException, Request
from sqlalchemy import delete, event, func, select, text

if not os.environ.get("OA_FINANCE_TEST_DB") or not os.environ.get("UPLOAD_ROOT"):
    raise RuntimeError("测试必须显式配置外部 OA_FINANCE_TEST_DB 和 UPLOAD_ROOT")
test_db = Path(os.environ["OA_FINANCE_TEST_DB"]).resolve()
if "apps" in test_db.parts or test_db.name != "finance-test.db":
    raise RuntimeError("测试数据库必须放在独立证据目录")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + test_db.as_posix()
os.environ["SEED_DEMO_DATA"] = "false"

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import (BusinessRecord, ContractApprovalStep, ContractObject, FileAttachment, FinanceTransaction, IncomingPayment,
                        LegacyOfficialDocument, JobRole, SystemParameter, User, WorkflowEvent)
from app.security import create_token, current_identity
from app.core.case_invoice_files import invoice_file_rows
from app.core.constants import FIELD_KEYS, UPLOAD_ROOT

PREFIX = "CODEX-929-"


@event.listens_for(engine.sync_engine, "connect")
def enable_foreign_keys(connection, _):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Finance929Regression(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://finance929.test")
        self.serial = 0
        async with SessionLocal() as db:
            for username, role, menus in [
                ("admin", "admin", []), ("applicant", "applicant929", ["finance-invoice-mine", "contract-mine", "case-files-invoice"]),
                ("firm", "firm929", ["finance-invoice-pending"]),
                ("platform", "platform929", ["platform-finance-invoice-pending"]),
                ("viewer", "viewer929", ["finance-invoice-mine"]),
                ("auditor", "auditor", ["finance-invoice-company"]),
            ]:
                db.add(User(username=PREFIX + username, display_name="测试" + username, role=role if role in {"admin", "auditor"} else "user",
                            profile={"permission_role_code": role} if role != "admin" else {},
                            department="回归测试部", password_hash="not-a-login-password", is_active=True))
                if role != "admin":
                    db.add(JobRole(code=role, name=role, permissions=menus,
                                   field_keys=list(FIELD_KEYS), field_keys_configured=True, data_scope="本人及共享数据"))
            db.add(User(username=PREFIX + "default-user", display_name="默认普通人", role="user", password_hash="test", is_active=True))
            await db.commit()
        self.actor("admin")

    async def asyncTearDown(self):
        await self.client.aclose()
        async with engine.begin() as connection:
            await connection.execute(text("PRAGMA foreign_keys=OFF"))
            for table in reversed(Base.metadata.sorted_tables):
                await connection.execute(delete(table))
            count = await connection.scalar(select(func.count()).select_from(BusinessRecord))
            self.assertEqual(count, 0, "测试业务必须清零")
        for path in UPLOAD_ROOT.iterdir():
            if path.is_file():
                path.unlink()
        await engine.dispose()

    def actor(self, username):
        self.client.headers["Authorization"] = "Bearer " + create_token(PREFIX + username, "user")

    async def api(self, method, path, *, code=200, **kwargs):
        response = await self.client.request(method, "/api/v1" + path, **kwargs)
        self.assertEqual(response.status_code, code, response.text)
        return response

    async def record(self, module, *, data=None, status="草稿", owner="admin", serial=None):
        self.serial += 1
        async with SessionLocal() as db:
            row = BusinessRecord(module=module, serial_no=serial or f"{PREFIX}{module}-{self.serial}",
                title=PREFIX + module, customer=PREFIX + "客户", owner=PREFIX + owner,
                department="回归测试部", status=status, data=data or {})
            db.add(row)
            await db.commit()
            return row

    async def update(self, row, **data):
        async with SessionLocal() as db:
            item = await db.get(BusinessRecord, row.id)
            item.data = {**item.data, **data}
            await db.commit()
            row.data = dict(item.data)

    async def sources(self, scope="律所", external=True):
        contract = await self.record("contract", serial=f"SH{PREFIX}{scope}-{self.serial}", status="审批中",
            data={"contract_body": scope, "external_contract_numbers": ["EXT-929"] if external else []})
        case = await self.record("case", status="一审阶段", data={"case_creation_step": "completed", "contract_id": contract.id,
            "contract_no": contract.serial_no, "case_type": "民事", "case_team_usernames": [PREFIX + "admin"]})
        fee = await self.record("finance", data={"case_id": case.id, "case_no": case.serial_no, "case_type": "民事",
            "contract_id": contract.id, "contract_no": contract.serial_no, "expense_scope": scope,
            "fee_type": "官方费用", "amount": 100, "paid_amount": 0, "invoice_amount": 0})
        return contract, case, fee

    def invoice_body(self, contract, case, fees):
        return {"customer": case.customer, "case_no": case.serial_no, "case_record_id": case.id,
                "contract_record_id": contract.id, "case_fee_ids": [fee.id for fee in fees],
                "amount": 80, "invoice_title": "回归抬头", "taxpayer_id": "TEST929", "email": "test@example.invalid"}

    async def upload(self, name, content=b"%PDF-1.4 CODEX-929", category="案件发票文件"):
        return (await self.api("POST", "/attachments", code=201,
            files={"file": (name, content, "application/octet-stream")}, data={"category": category})).json()

    async def test_r02_invoice_number_multifee_persistence_download_and_retry(self):
        contract, case, fee = await self.sources()
        second = await self.record("finance", data={**fee.data, "amount": 200})
        invoice = await self.record("invoice", status="已开票", owner="applicant",
            data={"invoice_no": "929001", "case_fee_ids": [fee.id, second.id], "amount": 300})
        uploaded = await self.upload("929001.pdf")
        result = (await self.api("POST", "/cases/invoice-files/import", json={"attachment_ids": [uploaded["id"]]})).json()
        self.assertEqual((result["matched"], result["unmatched"]), (1, 0))
        async with SessionLocal() as db:
            files = list((await db.scalars(select(FileAttachment))).all())
            self.assertEqual({item.record_id for item in files}, {fee.id, second.id})
            self.assertEqual({item.invoice_record_id for item in files}, {invoice.id})
            self.assertEqual(len({item.path for item in files}), 2)
            self.assertTrue(all(Path(item.path).read_bytes() == b"%PDF-1.4 CODEX-929" for item in files))
            self.assertEqual((await db.get(BusinessRecord, fee.id)).data["invoice_amount"], 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(FinanceTransaction)), 0)
        self.assertEqual(set(result["result_attachment_ids"]), {item.id for item in files})
        self.assertEqual(result["items"][0]["source_attachment_id"], uploaded["id"])
        self.assertEqual(result["items"][0]["result_attachment_ids"], result["result_attachment_ids"])
        for item in files:
            listed = (await self.api("GET", "/attachments", params={"record_id": item.record_id, "category": "案件发票文件"})).json()
            self.assertEqual([row["id"] for row in listed["items"]], [item.id])
            self.assertEqual((await self.api("GET", f"/attachments/{item.id}/download")).content, b"%PDF-1.4 CODEX-929")
        rows = (await self.api("GET", "/cases/invoice-files", params={"attachment_ids": result["result_attachment_ids"]})).json()["items"]
        self.assertEqual({row["invoice_no"] for row in rows}, {"929001"})
        self.assertEqual({row["applicant"] for row in rows}, {PREFIX + "applicant"})
        await self.api("POST", "/cases/invoice-files/import", code=409, json={"attachment_ids": [uploaded["id"]]})
        await self.api("DELETE", f"/attachments/{uploaded['id']}", code=204)
        remaining = next(item for item in files if item.id != uploaded["id"])
        self.assertEqual((await self.api("GET", f"/attachments/{remaining.id}/download")).content, b"%PDF-1.4 CODEX-929")

    async def test_r02_legacy_numeric_id_survives_merge_and_source_isolation(self):
        _, _, fee = await self.sources()
        await self.update(fee, legacy_case_fee_id=42911, legacy_source="source-A", merged_from_case_no="OLD-929")
        await self.record("finance", data={**fee.data, "legacy_source": "source-B"})
        invoice = await self.record("invoice", status="已开票", data={"invoice_no": "929002", "legacy_source": "source-A",
            "legacy_objects": [{"CaseFeeId": 42911, "CaseNo": "OLD-929", "InvoicedAmount": 100, "IsActived": "T"}]})
        uploaded = await self.upload("929002.pdf")
        self.assertEqual((await self.api("POST", "/cases/invoice-files/import", json={"attachment_ids": [uploaded["id"]]})).json()["matched"], 1)
        async with SessionLocal() as db:
            attachment = await db.scalar(select(FileAttachment))
            self.assertEqual((attachment.record_id, attachment.invoice_record_id), (fee.id, invoice.id))

    async def test_r02_zip_invalid_member_and_ambiguous_number_are_atomic(self):
        _, _, fee = await self.sources()
        await self.record("invoice", status="已开票", data={"invoice_no": "929003", "case_fee_ids": [fee.id]})
        stream = io.BytesIO()
        with ZipFile(stream, "w") as archive:
            archive.writestr("929003.pdf", b"invoice")
            archive.writestr("unknown.pdf", b"unknown")
        uploaded = await self.upload("invoices.zip", stream.getvalue())
        result = (await self.api("POST", "/cases/invoice-files/import", json={"attachment_ids": [uploaded["id"]]})).json()
        self.assertEqual((result["matched"], result["unmatched"]), (0, 1))
        self.assertEqual(result["result_attachment_ids"], [uploaded["id"]])
        self.assertEqual(result["items"][0]["result_attachment_ids"], [uploaded["id"]])
        failed_rows = (await self.api("GET", "/cases/invoice-files", params={"attachment_ids": result["result_attachment_ids"]})).json()["items"]
        self.assertEqual([row["id"] for row in failed_rows], [uploaded["id"]])
        self.assertIn("unknown.pdf", failed_rows[0]["match_status"])
        async with SessionLocal() as db:
            attachment = await db.get(FileAttachment, uploaded["id"])
            self.assertIsNone(attachment.record_id)
            self.assertIn("unknown.pdf", attachment.remark)
            self.assertEqual(len(list(UPLOAD_ROOT.iterdir())), 1)
        await self.record("invoice", status="已开票", data={"invoice_no": "929003", "case_fee_ids": [fee.id]})
        ambiguous = await self.upload("929003.pdf")
        batch = {"attachment_ids": [uploaded["id"], ambiguous["id"]]}
        result = (await self.api("POST", "/cases/invoice-files/import", json=batch)).json()
        self.assertEqual(result["matched"], 0)
        self.assertEqual(result["processed"], 2)
        self.assertEqual(set(result["result_attachment_ids"]), set(batch["attachment_ids"]))
        self.actor("viewer")
        await self.api("POST", "/cases/invoice-files/import", code=403, json=batch)

    async def test_r02_partial_disk_failure_rolls_back_and_removes_partial_file(self):
        _, _, fee = await self.sources()
        await self.record("invoice", status="已开票", data={"invoice_no": "929004", "case_fee_ids": [fee.id]})
        uploaded = await self.upload("929004.pdf")
        real_write = Path.write_bytes
        def fail_after_partial(path, content):
            real_write(path, b"partial")
            raise OSError("CODEX simulated disk failure")
        with patch.object(Path, "write_bytes", fail_after_partial):
            with self.assertRaises(OSError):
                await self.client.post("/api/v1/cases/invoice-files/import", json={"attachment_ids": [uploaded["id"]]})
        async with SessionLocal() as db:
            attachment = await db.get(FileAttachment, uploaded["id"])
            self.assertIsNone(attachment.record_id)
            self.assertEqual(len(list(UPLOAD_ROOT.iterdir())), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.action == "导入案件发票文件")), 0)

    async def test_r02_valid_zip_and_concurrent_retry_create_one_copy_per_positive_fee(self):
        _, _, fee = await self.sources()
        unused = await self.record("finance", data=fee.data)
        await self.record("invoice", status="已开票", data={"invoice_no": "929005", "case_fee_ids": [fee.id, unused.id],
            "case_fee_allocations": [{"fee_id": fee.id, "amount": 100}, {"fee_id": unused.id, "amount": 0}]})
        await self.record("invoice", status="已开票", data={"invoice_no": "929006", "case_fee_ids": [fee.id]})
        stream = io.BytesIO()
        with ZipFile(stream, "w") as archive:
            archive.writestr("one/929005.pdf", b"invoice-A")
            archive.writestr("two/929006.pdf", b"invoice-B")
        uploaded = await self.upload("valid.zip", stream.getvalue())
        batch = {"attachment_ids": [uploaded["id"]]}
        responses = await asyncio.gather(self.client.post("/api/v1/cases/invoice-files/import", json=batch),
                                         self.client.post("/api/v1/cases/invoice-files/import", json=batch))
        self.assertEqual(sorted(response.status_code for response in responses), [200, 409], [r.text for r in responses])
        result = next(response.json() for response in responses if response.status_code == 200)
        self.assertEqual(result["processed"], 1)
        async with SessionLocal() as db:
            files = list((await db.scalars(select(FileAttachment))).all())
            self.assertEqual(len(files), 2)
            self.assertEqual({item.record_id for item in files}, {fee.id})
            self.assertEqual({Path(item.path).read_bytes() for item in files}, {b"invoice-A", b"invoice-B"})
        self.assertEqual(set(result["result_attachment_ids"]), {item.id for item in files})
        self.assertEqual(result["items"][0]["result_attachment_ids"], result["result_attachment_ids"])
        rows = (await self.api("GET", "/cases/invoice-files", params={"attachment_ids": result["result_attachment_ids"]})).json()["items"]
        self.assertEqual({row["invoice_no"] for row in rows}, {"929005", "929006"})

    async def test_r02_explicit_batch_excludes_history_and_all_other_pending_files(self):
        _, _, fee = await self.sources()
        await self.record("invoice", status="已开票", data={"invoice_no": "929007", "case_fee_ids": [fee.id]})
        history = await self.upload("929007.pdf", b"historical-content")
        await self.api("POST", "/cases/invoice-files/import", json={"attachment_ids": [history["id"]]})
        old_pending = await self.upload("929007.pdf", b"previous-tab-content")
        self.actor("applicant")
        other_pending = await self.upload("929007.pdf", b"other-user-content")
        self.actor("admin")
        current = await self.upload("929007.pdf", b"current-tab-content")
        await self.api("GET", "/cases/invoice-files", code=422)
        current_rows = (await self.api("GET", "/cases/invoice-files", params={"attachment_ids": [current["id"]]})).json()
        self.assertEqual([row["id"] for row in current_rows["items"]], [current["id"]])
        self.assertEqual(current_rows["total"], 1)
        result = (await self.api("POST", "/cases/invoice-files/import", json={"attachment_ids": [current["id"]]})).json()
        self.assertEqual((result["processed"], result["matched"], result["result_attachment_ids"]), (1, 1, [current["id"]]))
        rows = (await self.api("GET", "/cases/invoice-files", params={"attachment_ids": result["result_attachment_ids"]})).json()["items"]
        self.assertEqual([row["id"] for row in rows], [current["id"]])
        async with SessionLocal() as db:
            for upload, content in [(old_pending, b"previous-tab-content"), (other_pending, b"other-user-content")]:
                item = await db.get(FileAttachment, upload["id"])
                self.assertIsNone(item.record_id)
                self.assertIsNone(item.invoice_record_id)
                self.assertEqual(item.remark, upload["remark"])
                self.assertEqual(Path(item.path).read_bytes(), content)
            item = await db.get(FileAttachment, history["id"])
            self.assertEqual((item.record_id, Path(item.path).read_bytes()), (fee.id, b"historical-content"))
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.action == "导入案件发票文件")), 2)
        ids = [history["id"], current["id"]]
        pages = [(await self.api("GET", "/cases/invoice-files", params={"attachment_ids": ids, "page": page, "page_size": 1})).json()
                 for page in (1, 2)]
        self.assertTrue(all(page["total"] == 2 and page["pages"] == 2 for page in pages))
        self.assertEqual({row["id"] for page in pages for row in page["items"]}, set(ids))

    async def test_r02_invalid_or_mixed_source_ids_reject_whole_request(self):
        _, _, fee = await self.sources()
        await self.record("invoice", status="已开票", data={"invoice_no": "929008", "case_fee_ids": [fee.id]})
        current = await self.upload("929008.pdf")
        wrong_category = await self.upload("929008.pdf", category="普通附件")
        self.actor("applicant")
        other = await self.upload("929008.pdf")
        self.actor("admin")
        linked = await self.upload("929008.pdf")
        await self.api("POST", "/cases/invoice-files/import", json={"attachment_ids": [linked["id"]]})
        invoice_linked = await self.upload("929008.pdf")
        async with SessionLocal() as db:
            source = await db.get(FileAttachment, invoice_linked["id"])
            source.invoice_record_id = (await db.get(FileAttachment, linked["id"])).invoice_record_id
            await db.commit()
        await self.api("POST", "/cases/invoice-files/import", code=422)
        for body in [{}, {"attachment_ids": []}, {"attachment_ids": [0]}, {"attachment_ids": [-1]},
                     {"attachment_ids": [True]}, {"attachment_ids": [1.5]}, {"attachment_ids": [str(current["id"])]},
                     {"attachment_ids": [current["id"], current["id"]]}]:
            with self.subTest(body=body):
                await self.api("POST", "/cases/invoice-files/import", code=422, json=body)
        for bad_id, code in [(999999, 404), (wrong_category["id"], 409), (other["id"], 403),
                             (linked["id"], 409), (invoice_linked["id"], 409)]:
            with self.subTest(bad_id=bad_id):
                await self.api("POST", "/cases/invoice-files/import", code=code,
                               json={"attachment_ids": [current["id"], bad_id]})
        for ids, code in [([current["id"], 999999], 404), ([current["id"], other["id"]], 403),
                          ([current["id"], wrong_category["id"]], 409), ([current["id"], current["id"]], 422),
                          ([0], 422), (["invalid"], 422)]:
            with self.subTest(get_ids=ids):
                await self.api("GET", "/cases/invoice-files", code=code, params={"attachment_ids": ids})
        async with SessionLocal() as db:
            for upload in [current, other, wrong_category]:
                item = await db.get(FileAttachment, upload["id"])
                self.assertIsNone(item.record_id)
                self.assertEqual(item.remark, upload["remark"])
                self.assertEqual(Path(item.path).read_bytes(), b"%PDF-1.4 CODEX-929")
            self.assertEqual(await db.scalar(select(func.count()).select_from(FileAttachment)), 5)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.action == "导入案件发票文件")), 1)

    async def test_r02_result_mapping_keeps_all_zip_copies_and_failed_sources(self):
        _, _, fee = await self.sources()
        second = await self.record("finance", data=fee.data)
        for number, fees in [("929009", [fee.id, second.id]), ("929010", [fee.id])]:
            await self.record("invoice", status="已开票", data={"invoice_no": number, "case_fee_ids": fees})
        stream = io.BytesIO()
        with ZipFile(stream, "w") as archive:
            archive.writestr("first/929009.pdf", b"multi-fee")
            archive.writestr("second/929010.pdf", b"single-fee")
        good = await self.upload("mapped.zip", stream.getvalue())
        failed = await self.upload("unmatched.pdf")
        result = (await self.api("POST", "/cases/invoice-files/import", json={"attachment_ids": [good["id"], failed["id"]]})).json()
        self.assertEqual((result["processed"], result["matched"], result["unmatched"]), (2, 1, 1))
        per_source = {item["source_attachment_id"]: item for item in result["items"]}
        self.assertEqual(len(per_source[good["id"]]["result_attachment_ids"]), 3)
        self.assertEqual(per_source[failed["id"]]["result_attachment_ids"], [failed["id"]])
        self.assertEqual(result["result_attachment_ids"], [value for item in result["items"] for value in item["result_attachment_ids"]])
        async with SessionLocal() as db:
            files = list((await db.scalars(select(FileAttachment))).all())
            self.assertEqual(len(files), 4)
            self.assertEqual(set(result["result_attachment_ids"]), {item.id for item in files})
            copies = [item for item in files if item.id in per_source[good["id"]]["result_attachment_ids"]]
            self.assertEqual(sorted(Path(item.path).read_bytes() for item in copies), [b"multi-fee", b"multi-fee", b"single-fee"])
            self.assertIsNone((await db.get(FileAttachment, failed["id"])).record_id)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.action == "导入案件发票文件")), 3)
        rows = (await self.api("GET", "/cases/invoice-files", params={"attachment_ids": result["result_attachment_ids"]})).json()["items"]
        self.assertEqual({row["id"] for row in rows}, set(result["result_attachment_ids"]))

    async def test_r02_explicit_results_preserve_record_scope_and_field_permissions(self):
        _, _, private_fee = await self.sources()
        await self.record("invoice", status="已开票", data={"invoice_no": "929011", "case_fee_ids": [private_fee.id]})
        private_file = await self.upload("929011.pdf")
        await self.api("POST", "/cases/invoice-files/import", json={"attachment_ids": [private_file["id"]]})
        own_fee = await self.record("finance", owner="applicant", data={"fee_type": "官方费用", "amount": 37})
        await self.record("invoice", status="已开票", owner="applicant",
                          data={"invoice_no": "929012", "case_fee_ids": [own_fee.id], "amount": 37})
        self.actor("applicant")
        own_file = await self.upload("929012.pdf")
        result = (await self.api("POST", "/cases/invoice-files/import", json={"attachment_ids": [own_file["id"]]})).json()
        params = {"attachment_ids": result["result_attachment_ids"]}
        row = (await self.api("GET", "/cases/invoice-files", params=params)).json()["items"][0]
        self.assertEqual((row["fee_amount"], row["invoice_amount"], row["invoice_no"]), (37, 37, "929012"))
        visible = (await self.api("GET", "/cases/invoice-files",
                       params={"attachment_ids": [own_file["id"], private_file["id"]]})).json()
        self.assertEqual({item["id"] for item in visible["items"]}, {own_file["id"], private_file["id"]})
        # 页面菜单能力原本扩大查询范围；核心读取器仍须保留未提升身份的数据及字段权限。
        request = Request({"type": "http", "path": "/api/v1/auth/me", "headers": []})
        token = create_token(PREFIX + "applicant", "user")
        async with SessionLocal() as db:
            identity = await current_identity(request, token, db)
            self.assertFalse(identity["_page_menu_capability"])
            self.assertNotIn("admin", identity["role_ids"])
            rows = await invoice_file_rows(identity, db, 1, 200, [own_file["id"]])
            self.assertEqual(rows["items"][0]["fee_amount"], 37)
            with self.assertRaises(HTTPException) as denied:
                await invoice_file_rows(identity, db, 1, 200, [own_file["id"], private_file["id"]])
            self.assertEqual(denied.exception.status_code, 403)
        async with SessionLocal() as db:
            role = await db.scalar(select(JobRole).where(JobRole.code == "applicant929"))
            role.field_keys = [key for key in FIELD_KEYS if key != "finance.amount"]
            await db.commit()
        async with SessionLocal() as db:
            identity = await current_identity(request, token, db)
            row = (await invoice_file_rows(identity, db, 1, 200, [own_file["id"]]))["items"][0]
        self.assertIsNone(row["fee_amount"])
        self.assertIsNone(row["invoice_amount"])
        self.assertEqual(row["invoice_no"], "929012")
        self.actor("viewer")
        await self.api("GET", "/cases/invoice-files", code=403, params=params)

    async def test_r03_default_and_manual_contract_selection_persist_as_fee_contract(self):
        contract, case, _ = await self.sources()
        other = await self.record("contract", status="审批中", data={"contract_body": "律所"})
        for selected in (contract, other):
            body = {"title": "CODEX-929-R03费用", "customer": case.customer, "amount": 50,
                    "fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "一审诉讼费",
                    "handler": PREFIX + "admin", "case_record_id": case.id, "case_no": case.serial_no,
                    "contract_record_id": selected.id}
            created = (await self.api("POST", "/finance/fees", code=201, json=body)).json()
            async with SessionLocal() as db:
                persisted = await db.get(BusinessRecord, created["id"])
                self.assertEqual((persisted.data["contract_id"], persisted.data["contract_no"]), (selected.id, selected.serial_no))
            candidates = (await self.api("GET", f"/contracts/{selected.id}/payment-candidates")).json()["items"]
            self.assertIn(created["id"], {row["case_fee_id"] for row in candidates})
        body.pop("contract_record_id")
        await self.api("POST", "/finance/fees", code=422, json=body)

    async def test_r08_approval_only_deleted_real_dependencies_block_and_batch_atomic(self):
        empty = await self.record("contract", status="审批中")
        blocked = await self.record("contract", status="审批中")
        await self.record("task", data={"contract_no": blocked.serial_no})
        async with SessionLocal() as db:
            db.add(ContractApprovalStep(contract_record_id=empty.id, step_order=1, approver=PREFIX + "admin", status="待审批"))
            await db.commit()
        failed = (await self.api("POST", "/contracts/company/delete", json={"contract_ids": [empty.id, blocked.id]})).json()
        self.assertFalse(failed["IsSuccess"])
        async with SessionLocal() as db:
            self.assertIsNotNone(await db.get(BusinessRecord, empty.id))
        success = (await self.api("POST", "/contracts/company/delete", json={"contract_ids": [empty.id]})).json()
        self.assertTrue(success["IsSuccess"], success)
        for module, key, value in [("case", "contract_id", "id"), ("clue", "contract_nos", "nos"),
                                   ("finance", "contract_record_id", "id"), ("invoice", "contract_ids", "ids")]:
            contract = await self.record("contract", status="审批中")
            relation = contract.id if value == "id" else [contract.id] if value == "ids" else [contract.serial_no]
            await self.record(module, data={key: relation})
            result = (await self.api("POST", "/contracts/company/delete", json={"contract_ids": [contract.id]})).json()
            self.assertFalse(result["IsSuccess"], module)
        owned = await self.record("contract", status="审批中")
        self.actor("applicant")
        response = (await self.api("POST", "/contracts/company/delete", json={"contract_ids": [owned.id]})).json()
        self.assertFalse(response["IsSuccess"], "页面提权不能授予删除别人的合同")

    async def test_r08_only_untouched_subordinate_seal_draft_is_removed(self):
        for state in ("草稿", "待审批"):
            contract = await self.record("contract", status="审批中", data={"sync_seal": True})
            seal = await self.record("seal", status=state, data={"contract_record_id": contract.id,
                "contract_no": contract.serial_no, "use_type": "合同用印"})
            await self.update(contract, seal_application_ids=[seal.id])
            legacy_id = -self.serial
            async with SessionLocal() as db:
                db.add(WorkflowEvent(record_id=seal.id, action="创建合同用印申请", to_status=state, operator=PREFIX + "admin"))
                db.add(LegacyOfficialDocument(OfficialDocumentId=legacy_id, OfficialDocumentNo=seal.serial_no,
                    OfficialDocumentGuid=f"draft-{seal.id}", IsActived="Y", PrintStatus=0))
                await db.commit()
            result = (await self.api("POST", "/contracts/company/delete", json={"contract_ids": [contract.id]})).json()
            self.assertEqual(result["IsSuccess"], state == "草稿", result)
            async with SessionLocal() as db:
                self.assertEqual(await db.get(BusinessRecord, seal.id) is None, state == "草稿")
                legacy = await db.get(LegacyOfficialDocument, legacy_id)
                self.assertEqual(legacy.IsActived, "N" if state == "草稿" else "Y")

    async def test_r08_relational_case_objects_and_receipt_allocations_block(self):
        contract = await self.record("contract", status="审批中")
        case = await self.record("case")
        async with SessionLocal() as db:
            db.add(ContractObject(contract_record_id=contract.id, case_record_id=case.id, amount=100, fee_type="官方费用",
                                  created_by=PREFIX + "admin", updated_by=PREFIX + "admin"))
            await db.commit()
        result = (await self.api("POST", "/contracts/company/delete", json={"contract_ids": [contract.id]})).json()
        self.assertFalse(result["IsSuccess"])
        other = await self.record("contract", status="审批中")
        async with SessionLocal() as db:
            db.add(IncomingPayment(receipt_no="CODEX-929-R08-ALLOC", received_date=date(2026, 9, 30), amount=100,
                payer_name="测试", operator=PREFIX + "admin", allocations=[{"contract_id": other.id, "amount": 100}]))
            await db.commit()
        result = (await self.api("POST", "/contracts/company/delete", json={"contract_ids": [other.id]})).json()
        self.assertFalse(result["IsSuccess"])

    async def test_r09_r11_create_update_submit_policy_and_historical_read(self):
        contract, case, fee = await self.sources(external=False)
        body = self.invoice_body(contract, case, [fee])
        response = await self.api("POST", "/finance/invoices", code=409, json=body)
        self.assertIn("外部合同号", response.text)
        await self.update(contract, external_contract_numbers=["EXT-929"])
        created = (await self.api("POST", "/finance/invoices", code=201, json=body)).json()
        await self.update(contract, external_contract_numbers=[])
        await self.api("PUT", f"/finance/invoices/{created['id']}", code=409, json=body)
        await self.api("POST", f"/finance/invoices/{created['id']}/submit", code=409, json={"comment": "回归"})
        async with SessionLocal() as db:
            self.assertEqual((await db.get(BusinessRecord, created["id"])).status, "草稿")
        await self.update(contract, external_contract_numbers=["EXT-929"])
        internal = await self.record("finance", data={**fee.data, "expense_scope": "内部", "fee_type": "内部费用"})
        await self.api("POST", "/finance/invoices", code=409, json=self.invoice_body(contract, case, [internal]))
        historic = await self.record("invoice", data={**body, "case_fee_ids": [internal.id]}, status="草稿")
        await self.api("POST", f"/finance/invoices/{historic.id}/submit", code=409, json={"comment": "回归"})
        detail = (await self.api("GET", f"/finance/invoices/{historic.id}")).json()
        self.assertEqual(detail["id"], historic.id)
        candidates = (await self.api("GET", f"/contracts/{contract.id}/invoice-candidates")).json()["items"]
        self.assertNotIn(internal.id, {row["fee_id"] for row in candidates})

    async def test_r09_non_sh_contract_and_legacy_external_number_boundaries(self):
        contract, case, fee = await self.sources(external=False)
        body = self.invoice_body(contract, case, [fee])
        async with SessionLocal() as db:
            item = await db.get(BusinessRecord, contract.id)
            item.data = {"contract_body": "律所", "ref_contract_no": "LEGACY-EXT"}
            await db.commit()
        invoice = (await self.api("POST", "/finance/invoices", code=201, json=body)).json()
        await self.update(contract, external_contract_numbers=[], ref_contract_no="LEGACY-EXT")
        await self.api("POST", f"/finance/invoices/{invoice['id']}/submit", code=409, json={"comment": "显式清空不能复活旧号"})
        async with SessionLocal() as db:
            item = await db.get(BusinessRecord, contract.id)
            item.serial_no = "OTHER-CODEX-929"
            fee_item = await db.get(BusinessRecord, fee.id)
            fee_item.data = {**fee_item.data, "contract_no": item.serial_no}
            await db.commit()
        await self.api("POST", f"/finance/invoices/{invoice['id']}/submit", json={"comment": "非SH不强制"})

    async def test_r10_payment_candidates_use_fee_contract_and_exclude_internal(self):
        contract, case, fee = await self.sources()
        other = await self.record("contract", data={"contract_body": "律所"}, status="审批中")
        foreign_fee = await self.record("finance", data={**fee.data, "contract_id": other.id, "contract_no": other.serial_no})
        internal = await self.record("finance", data={**fee.data, "expense_scope": "内部", "fee_type": "内部费用"})
        current = (await self.api("GET", f"/contracts/{contract.id}/payment-candidates")).json()["items"]
        other_rows = (await self.api("GET", f"/contracts/{other.id}/payment-candidates")).json()["items"]
        self.assertEqual({row["case_fee_id"] for row in current}, {fee.id})
        self.assertEqual({row["case_fee_id"] for row in other_rows}, {foreign_fee.id})
        self.assertNotIn(internal.id, {row["case_fee_id"] for row in current})
        async with SessionLocal() as db:
            payment_type = SystemParameter(category="payment_type", code="CODEX-929-R10", name="测试付款单位",
                extra={"payee": "测试收款人", "account_bank": "测试银行", "account": "929000"}, is_active=True)
            db.add(payment_type)
            await db.commit()
        payload = {"payment_type_id": payment_type.id, "application_date": "2026-09-30", "lines": [{"case_fee_id": internal.id, "amount": 30}]}
        await self.api("POST", f"/contracts/{contract.id}/payment-applications", code=404, json=payload)
        payload["lines"][0]["case_fee_id"] = fee.id
        payment = (await self.api("POST", f"/contracts/{contract.id}/payment-applications", code=201, json=payload)).json()
        await self.api("POST", f"/contract-payment-applications/{payment['id']}/review", json={"approved": False, "comment": "回归驳回"})
        await self.update(fee, expense_scope="内部", fee_type="内部费用")
        await self.api("POST", f"/contract-payment-applications/{payment['id']}/submit", code=404, json={"comment": "重提回归"})
        async with SessionLocal() as db:
            self.assertEqual((await db.get(BusinessRecord, payment["id"])).status, "已驳回")
            self.assertEqual(await db.scalar(select(func.count()).select_from(FinanceTransaction)), 0)

    async def test_r12_real_role_scope_list_export_review_issue_and_persistence(self):
        contract, case, fee = await self.sources()
        self.actor("applicant")
        created = (await self.api("POST", "/finance/invoices", code=201, json=self.invoice_body(contract, case, [fee]))).json()
        item_id = created["id"]
        await self.api("POST", f"/finance/invoices/{item_id}/submit", json={"comment": "提交回归"})
        mine = (await self.api("GET", "/finance/invoices", params={"scope": "mine"})).json()["items"]
        self.assertIn(item_id, {row["id"] for row in mine})
        self.actor("viewer")
        await self.api("GET", "/finance/invoices", code=403, params={"scope": "pending"})
        await self.api("POST", f"/finance/invoices/{item_id}/review", code=403, json={"approved": True, "comment": "拒绝提权"})
        self.actor("default-user")
        await self.api("GET", "/finance/invoices", code=403, params={"scope": "pending"})
        await self.api("POST", f"/finance/invoices/{item_id}/review", code=403, json={"approved": True, "comment": "默认菜单不可审核"})
        self.actor("platform")
        self.assertEqual((await self.api("GET", "/finance/invoices", params={"scope": "pending"})).json()["items"], [])
        await self.api("POST", f"/finance/invoices/{item_id}/review", code=403, json={"approved": True, "comment": "跨板块拒绝"})
        exported = await self.api("GET", "/finance/invoices/export", params={"scope": "pending"})
        self.assertNotIn(created["serial_no"], exported.text)
        self.actor("firm")
        pending = (await self.api("GET", "/finance/invoices", params={"scope": "pending"})).json()["items"]
        self.assertEqual([row["id"] for row in pending], [item_id])
        self.assertTrue(pending[0]["data"]["can_review"])
        await self.api("POST", f"/finance/invoices/{item_id}/review", json={"approved": True, "comment": "通过回归"})
        pending = (await self.api("GET", "/finance/invoices", params={"scope": "pending"})).json()["items"]
        self.assertTrue(pending[0]["data"]["can_issue"])
        self.actor("auditor")
        await self.api("POST", f"/finance/invoices/{item_id}/issue", code=403,
                       json={"invoice_no": "929008", "invoice_date": "2026-09-30"})
        self.actor("firm")
        await self.api("POST", f"/finance/invoices/{item_id}/issue", json={"invoice_no": "929008", "invoice_date": "2026-09-30"})
        self.assertEqual((await self.api("GET", "/finance/invoices", params={"scope": "pending"})).json()["items"], [])
        async with SessionLocal() as db:
            persisted = await db.get(BusinessRecord, item_id)
            self.assertEqual((persisted.status, persisted.data["invoice_no"]), ("已开票", "929008"))

    async def test_r12_platform_review_rejection_stays_in_applicant_history(self):
        contract, case, fee = await self.sources(scope="平台")
        self.actor("applicant")
        created = (await self.api("POST", "/finance/invoices", code=201, json=self.invoice_body(contract, case, [fee]))).json()
        item_id = created["id"]
        await self.api("POST", f"/finance/invoices/{item_id}/submit", json={"comment": "平台提交"})
        self.actor("firm")
        self.assertEqual((await self.api("GET", "/finance/invoices", params={"scope": "pending"})).json()["items"], [])
        await self.api("POST", f"/finance/invoices/{item_id}/review", code=403, json={"approved": False, "comment": "跨板块拒绝"})
        self.actor("platform")
        pending = (await self.api("GET", "/finance/invoices", params={"scope": "pending"})).json()["items"]
        self.assertEqual([item["id"] for item in pending], [item_id])
        await self.api("POST", f"/finance/invoices/{item_id}/review", json={"approved": False, "comment": "平台资料需补齐"})
        self.actor("applicant")
        mine = (await self.api("GET", "/finance/invoices", params={"scope": "mine"})).json()["items"]
        self.assertEqual((mine[0]["status"], mine[0]["data"]["review_comment"]), ("已驳回", "平台资料需补齐"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

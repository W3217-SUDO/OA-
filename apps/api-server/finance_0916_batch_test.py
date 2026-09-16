"""9.16 batch regression through the real API, using a disposable in-memory DB."""
import unittest
from datetime import date
import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User, HrSubrecord, IncomingPayment, SystemParameter, WorkflowEvent
from app.security import current_identity

API = settings.api_prefix
IDENTITY = {"username": "CODEX-0916-admin", "role": "admin", "department": "test"}

class FinanceBatchTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="Current manager", role="admin", department="test", password_hash="unused", is_active=True))
            employee = BusinessRecord(module="hr", serial_no="CODEX-0916-employee", title="Current manager", owner=IDENTITY["username"], status="在职", data={"username": IDENTITY["username"], "is_active": True})
            customer = BusinessRecord(module="customer", serial_no="CODEX-0916-customer", title="Batch customer", owner=IDENTITY["username"], status="有效", data={})
            db.add_all([employee, customer]); await db.flush()
            contract = BusinessRecord(module="contract", serial_no="CODEX-0916-contract", title="Batch contract", customer=customer.title, owner=IDENTITY["username"], status="已审批", data={"contract_body":"律所"})
            db.add(contract); await db.flush()
            self.contract_id = contract.id
            db.add(HrSubrecord(employee_id=employee.id, kind="commission", created_by=IDENTITY["username"], updated_by=IDENTITY["username"], data={"start_date": "2020-01-01", "hearing_rate": .1, "document_rate": .05}))
            case = BusinessRecord(module="case", serial_no="CODEX-0916-case", title="Batch case", customer=customer.title, owner=IDENTITY["username"], department="test", status="一审立案受理", data={"case_type": "民事争议", "case_creation_step": "completed", "customer_record_id": customer.id, "hearing_lawyer_usernames": [IDENTITY["username"]], "handling_lawyer_usernames": [IDENTITY["username"]], "assistant_usernames": [IDENTITY["username"]]})
            db.add(case); await db.flush()
            fee = BusinessRecord(module="finance", serial_no="CODEX-0916-fee", title="律师代理费", customer=customer.title, owner=IDENTITY["username"], department="test", status="草稿", data={"fee_type": "代理费", "expense_subtype": "律师代理费", "expense_scope": "律所", "amount": 100, "case_id": case.id, "case_no": case.serial_no})
            db.add(fee); await db.flush()
            receipt = IncomingPayment(receipt_no="CODEX-0916-receipt", received_date=date(2026,9,16), amount=100, allocated_amount=100, payer_name="Batch payer", claimed_customer=customer.title, operator=IDENTITY["username"], status="已分配", bank_source="招商银行", allocations=[{"case_id": case.id, "case_no": case.serial_no, "amount": 100}])
            db.add(receipt); await db.flush()
            settlement = BusinessRecord(module="finance_settlement", serial_no="CODEX-0916-settlement", title="Batch settlement", customer=customer.title, owner=IDENTITY["username"], department="test", status="已付款", data={"receipt_id": receipt.id, "review_comment": "old approval", "receipt_amount": 100, "allocation_details": []})
            root = SystemParameter(category="fee_type", code="OFFICIAL", name="官费", extra={})
            leaf = SystemParameter(category="fee_type", code="CODEX-0916-type", name="一审诉讼费", extra={"parent_code":"OFFICIAL"})
            db.add_all([settlement, root, leaf]); await db.commit()
            self.case_id, self.fee_id, self.customer_id, self.settlement_id, self.leaf_id = case.id, fee.id, customer.id, settlement.id, leaf.id
        async def database():
            async with self.sessions() as db:
                yield db
        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://batch.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    async def test_required_people_preview_and_save_are_atomic(self):
        preview = await self.client.get(f"{API}/cases/{self.case_id}/commission-preview", params={"source_fee_id":self.fee_id})
        self.assertEqual(preview.status_code,200,preview.text)
        item = preview.json()["items"][0]
        for field in ["hearing_lawyer_usernames", "handling_lawyer_usernames", "assistant_usernames"]:
            async with self.sessions() as db:
                case = await db.get(BusinessRecord,self.case_id); original = dict(case.data)
                case.data = {**original,field:[]}; await db.commit()
                before = await db.scalar(select(func.count()).select_from(BusinessRecord))
            result = await self.client.get(f"{API}/cases/{self.case_id}/commission-preview", params={"source_fee_id":self.fee_id})
            self.assertEqual(result.status_code,422,result.text)
            result = await self.client.post(f"{API}/cases/{self.case_id}/commissions",json={"source_fee_id":self.fee_id,"items":[{"preview_key":item["preview_key"],"actual_amount":10}]})
            self.assertEqual(result.status_code,422,result.text)
            async with self.sessions() as db:
                self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord)),before)
                case = await db.get(BusinessRecord,self.case_id); case.data=original; await db.commit()

    async def test_rollback_comment_pending_rejection_and_repeated_action(self):
        path=f"{API}/finance/general-settlements/applications/payment"
        body={"application_ids":[self.settlement_id],"action":"rollback","comment":"actual rollback"}
        result=await self.client.post(path,json=body); self.assertEqual(result.status_code,200,result.text)
        result=await self.client.get(f"{API}/finance/general-settlements/pending")
        self.assertEqual(result.status_code,200,result.text)
        row=result.json()["items"][0]
        self.assertEqual(row["data"]["rejection_comment"],"actual rollback")
        self.assertEqual(row["data"]["customer_manager"],"Current manager")
        rejected=await self.client.get(f"{API}/finance/general-settlements/applications",params={"status":"已拒绝,已驳回"})
        self.assertEqual(rejected.json()["total"],0)
        repeated=await self.client.post(path,json=body); self.assertEqual(repeated.status_code,409)
        async with self.sessions() as db:
            row=await db.get(BusinessRecord,self.settlement_id)
            self.assertEqual(row.status,"已退回"); self.assertEqual(row.data["review_comment"],"old approval")
            self.assertEqual(row.data["rollback_comment"],"actual rollback")
            events=(await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id==row.id))).all()
            self.assertEqual(len(events),1)

    async def test_catalog_and_edit_save_type_identity(self):
        result=await self.client.get(f"{API}/system/parameters/options",params={"category":"fee_type"})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(len(result.json()["items"]),2)
        result=await self.client.put(f"{API}/finance/fees/{self.fee_id}",json={"title":"一审诉讼费","fee_type":"官方费用","fee_type_id":self.leaf_id,"expense_scope":"律所","expense_subtype":"一审诉讼费","amount":100,"handler":IDENTITY["username"],"case_record_id":self.case_id,"contract_record_id":self.contract_id,"case_no":"CODEX-0916-case","customer":"Batch customer"})
        self.assertEqual(result.status_code,200,result.text)
        async with self.sessions() as db:
            fee=await db.get(BusinessRecord,self.fee_id)
            self.assertEqual(fee.data["fee_type_id"],self.leaf_id)
            self.assertEqual(fee.data["fee_type_code"],"CODEX-0916-type")
            self.assertEqual(fee.data["expense_subtype"],"一审诉讼费")

    async def test_bank_filter_does_not_mix_receipts(self):
        for bank,total in [("cmb",1),("icbc",0),("citic",0),("boc",0)]:
            result=await self.client.get(f"{API}/finance/incoming-payments",params={"bank_source":bank})
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json()["total"],total)

    async def test_invalid_person_and_post_preview_are_blocked(self):
        async with self.sessions() as db:
            case=await db.get(BusinessRecord,self.case_id)
            case.data={**case.data,"assistant_usernames":["missing-account"]}; await db.commit()
        result=await self.client.post(f"{API}/cases/{self.case_id}/commission-preview",json={"amount":100})
        self.assertEqual(result.status_code,422,result.text)
        self.assertIn("律师助理",result.text)

    async def test_complete_people_create_persists_and_rollback_can_apply_again(self):
        preview=await self.client.get(f"{API}/cases/{self.case_id}/commission-preview",params={"source_fee_id":self.fee_id})
        item=preview.json()["items"][0]
        result=await self.client.post(f"{API}/cases/{self.case_id}/commissions",json={"source_fee_id":self.fee_id,"items":[{"preview_key":item["preview_key"],"actual_amount":10}]})
        self.assertEqual(result.status_code,201,result.text)
        async with self.sessions() as db:
            stored=await db.get(BusinessRecord,result.json()["items"][0]["id"])
            self.assertEqual(stored.data["amount"],10)
        result=await self.client.post(f"{API}/finance/general-settlements/applications/payment",json={"application_ids":[self.settlement_id],"action":"rollback","comment":"rollback before reapply"})
        self.assertEqual(result.status_code,200,result.text)
        pending=(await self.client.get(f"{API}/finance/general-settlements/pending")).json()["items"]
        result=await self.client.post(f"{API}/finance/general-settlements/apply",json={"receipt_ids":[pending[0]["id"]],"comment":"apply again"})
        self.assertEqual(result.status_code,201,result.text)
        pending=(await self.client.get(f"{API}/finance/general-settlements/pending")).json()["items"]
        self.assertEqual(pending,[])

    async def test_new_catalog_leaf_and_exact_query(self):
        async with self.sessions() as db:
            leaf=await db.get(SystemParameter,self.leaf_id)
            leaf.name="目录新增费用"; await db.commit()
        payload={"title":"目录新增费用","fee_type":"官方费用","fee_type_id":self.leaf_id,"expense_scope":"律所","expense_subtype":"目录新增费用","amount":100,"handler":IDENTITY["username"],"case_record_id":self.case_id,"contract_record_id":self.contract_id,"case_no":"CODEX-0916-case","customer":"Batch customer"}
        result=await self.client.put(f"{API}/finance/fees/{self.fee_id}",json=payload)
        self.assertEqual(result.status_code,200,result.text)
        for types,total in [("目录新增费用",1),("目录新增",0),("一审诉讼费,目录新增费用",1),("官方费用",1)]:
            result=await self.client.get(f"{API}/finance/payment-applications/query",params={"fee_type":types})
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json()["total"],total,result.text)
        result=await self.client.put(f"{API}/finance/fees/{self.fee_id}",json={**payload,"fee_type":"代理费"})
        self.assertEqual(result.status_code,422,result.text)
        async with self.sessions() as db:
            fee=await db.get(BusinessRecord,self.fee_id)
            self.assertEqual(fee.data["fee_type"],"官方费用")

    async def test_rollback_blank_and_archive_guard_leave_original_status(self):
        path=f"{API}/finance/general-settlements/applications/payment"
        body={"application_ids":[self.settlement_id],"action":"rollback","comment":""}
        result=await self.client.post(path,json=body); self.assertEqual(result.status_code,422)
        async with self.sessions() as db:
            db.add(BusinessRecord(module="finance_archive_settlement",serial_no="CODEX-0916-archive",title="archive",owner=IDENTITY["username"],status="已支付",data={"source_application_id":self.settlement_id}))
            await db.commit()
        result=await self.client.post(path,json={**body,"comment":"must be blocked"}); self.assertEqual(result.status_code,409,result.text)
        async with self.sessions() as db:
            row=await db.get(BusinessRecord,self.settlement_id)
            self.assertEqual(row.status,"已付款")
            self.assertNotIn("rollback_comment",row.data)

    async def test_current_multiple_customer_managers_and_audit_rejection(self):
        async with self.sessions() as db:
            db.add(User(username="CODEX-0916-second",display_name="Second manager",role="user",password_hash="unused",is_active=True))
            customer=await db.get(BusinessRecord,self.customer_id)
            customer.data={"customer_managers":[IDENTITY["username"],"CODEX-0916-second"]}
            row=await db.get(BusinessRecord,self.settlement_id);row.status="待审批";await db.commit()
        result=await self.client.post(f"{API}/finance/general-settlements/applications/review",json={"application_ids":[self.settlement_id],"approved":False,"comment":"audit refusal"})
        self.assertEqual(result.status_code,200,result.text)
        result=await self.client.get(f"{API}/finance/general-settlements/applications",params={"status":"已拒绝,已驳回","customer_manager":"Second manager"})
        self.assertEqual(result.json()["total"],1,result.text)
        self.assertEqual(result.json()["items"][0]["data"]["customer_manager"],"Current manager、Second manager")
        pending=await self.client.get(f"{API}/finance/general-settlements/pending")
        self.assertEqual(pending.json()["items"][0]["data"]["rejection_comment"],"audit refusal")

if __name__ == "__main__": unittest.main()

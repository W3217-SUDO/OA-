import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User, WorkflowEvent, FinanceTransaction, IncomingPayment, LegacyFinanceRecord
from sqlalchemy import select, delete, func
from datetime import date
from app.security import current_identity

API = settings.api_prefix
IDENTITY = {"username": "row17-admin", "role": "admin", "display_name": "Row17 Admin", "department": "Admin"}
SUBTYPES = ["\u4ea7\u54c1\u8d2d\u4e70\u8d39", "\u7ffb\u8bd1\u8d39", "\u6295\u8d44\u63d0\u6210", "\u8c03\u6863\u8d39", "\u624b\u7eed\u8d39", "\u4efb\u52a1\u8c03\u671f\u6263\u6b3e", "\u670d\u52a1\u8d39(\u8c03\u67e5)", "\u670d\u52a1\u8d39(\u5f00\u5ead)", "\u670d\u52a1\u8d39(\u6848\u6e90)", "\u670d\u52a1\u8d39(\u6587\u4e66)", "\u670d\u52a1\u8d39(\u54c1\u7ba1)"]

class CaseInternalFeeRow17Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="x", is_active=True))
            case = BusinessRecord(module="case", serial_no="CODEX-828-R17-CASE", title="Row17 Case", customer="Row17 Customer", status="\u6587\u4e66\u51c6\u5907", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "\u6c11\u4e8b\u4e89\u8bae", "case_creation_step": "completed"})
            db.add(case); await db.commit(); await db.refresh(case); self.case_id = case.id
        async def override_db():
            async with self.sessions() as db: yield db
        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row17.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.sessions() as db:
            ids=list((await db.scalars(select(BusinessRecord.id))).all())
            await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id.in_(ids)))
            await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_(ids)))
            await db.execute(delete(LegacyFinanceRecord).where(LegacyFinanceRecord.legacy_id.like("CODEX1021INTERNAL-%")))
            await db.execute(delete(IncomingPayment).where(IncomingPayment.receipt_no.like("CODEX1021INTERNAL-%")))
            await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_(ids)))
            await db.execute(delete(User).where(User.username.in_([IDENTITY["username"],"CODEX1021INTERNAL-OTHER"])))
            await db.commit()
            for model in [BusinessRecord,FinanceTransaction,WorkflowEvent,IncomingPayment,LegacyFinanceRecord,User]:
                self.assertEqual(await db.scalar(select(func.count()).select_from(model)),0)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    async def test_all_internal_fee_types_save_without_contract(self):
        for index, subtype in enumerate(SUBTYPES):
            response = await self.client.post(f"{API}/finance/fees", json={
                "title": f"Row17 {subtype}", "customer": "Row17 Customer", "amount": 170 + index,
                "fee_type": "\u5185\u90e8\u8d39\u7528", "expense_scope": "\u5185\u90e8", "expense_subtype": subtype,
                "case_no": "CODEX-828-R17-CASE", "case_record_id": self.case_id, "handler": IDENTITY["username"],
                "payee": IDENTITY["username"], "base_amount": 1000 + index, "reference_commission": 100 + index,
            })
            self.assertEqual(response.status_code, 201, response.text)
            data = response.json()["data"]
            self.assertEqual(data["expense_subtype"], subtype)
            self.assertIsNone(data["contract_id"])
            self.assertEqual(data["payee"], IDENTITY["username"])
            self.assertEqual(data["base_amount"], 1000 + index)
            self.assertEqual(data["reference_commission"], 100 + index)


    async def create_payment_selection(self, *, historical=False, refund=False):
        async with self.sessions() as db:
            source = BusinessRecord(module="finance", serial_no="CODEX1021INTERNAL-SOURCE", title="代理费",
                customer="Row17 Customer", status="草稿", owner=IDENTITY["username"], department="Admin",
                data={"amount":1000, "fee_type":"代理费", "expense_scope":"律所", "refund_fee":refund,
                      "case_id":self.case_id, "case_no":"CODEX-828-R17-CASE"})
            db.add(source); await db.flush()
            ids=[]
            for index,value in enumerate([20,50,50,50,100]):
                data={"amount":value,"fee_type":"内部费用","expense_scope":"内部","commission_type":"案源提成",
                    "case_id":self.case_id,"case_no":"CODEX-828-R17-CASE","source_fee_id":source.id,
                    "handler":IDENTITY["username"],"payee":IDENTITY["username"],"commission_created_by":IDENTITY["username"],
                    "commission_created_at":"2026-10-21T12:00:00","payment_application_no":"CODEX1021INTERNAL-CREATED",
                    "payment_requested_amount":value if historical else 0,"applicant":IDENTITY["username"],
                    "commission_lifecycle":"case_agency_refund" if refund else "case_agency_fee", "is_refund":refund}
                if not historical: data["internal_payment_submitted"]=False
                item=BusinessRecord(module="finance",serial_no=f"CODEX1021INTERNAL-{index}",title="提成",customer="Row17 Customer",
                    status="待审批" if refund else "待到账",owner=IDENTITY["username"],department="Admin",data=data)
                db.add(item);await db.flush();ids.append(item.id)
                db.add(WorkflowEvent(record_id=item.id,action="创建案件提成",to_status=item.status,operator=IDENTITY["username"]))
            await db.commit()
            return ids, source.id

    def payment_body(self, ids):
        return {"lines":[{"fee_id":item_id,"amount":value,"payment_payee":IDENTITY["username"],"payment_account":"CODEX-ACCOUNT"}
                        for item_id,value in zip(ids,[20,50,50,50,100])],"comment":"CODEX1021INTERNAL"}

    async def test_batch_first_application_is_atomic_and_preserves_lifecycle(self):
        ids,source_id=await self.create_payment_selection(historical=True)
        preview=await self.client.post(f"{API}/finance/internal-applications/payment-preview",json={"fee_ids":ids})
        self.assertEqual(preview.status_code,200,preview.text)
        self.assertTrue(all(not item["submitted"] for item in preview.json()["items"]))
        body=self.payment_body(ids)
        invalid={**body,"lines":[*body["lines"][:-1],{**body["lines"][-1],"amount":101}]}
        failed=await self.client.post(f"{API}/finance/internal-applications/payment-requests",json=invalid)
        self.assertEqual(failed.status_code,409,failed.text)
        async with self.sessions() as db:
            self.assertFalse((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.action=="提交内部费用付款申请"))).all())
        result=await self.client.post(f"{API}/finance/internal-applications/payment-requests",json=body)
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()["submitted"],5)
        repeat=await self.client.post(f"{API}/finance/internal-applications/payment-requests",json=body)
        self.assertEqual(repeat.status_code,409,repeat.text)
        async with self.sessions() as db:
            rows=(await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids)))).all()
            self.assertTrue(all(item.status=="待到账" for item in rows))
            self.assertEqual(sum(item.data["payment_requested_amount"] for item in rows),270)
            self.assertEqual(len((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.action=="提交内部费用付款申请"))).all()),5)
        withdrawn=await self.client.post(f"{API}/finance/internal-applications/{ids[0]}/withdraw",json={"reason":"CODEX1021INTERNAL清理验证"})
        self.assertEqual(withdrawn.status_code,200,withdrawn.text)
        self.assertEqual(set(withdrawn.json()["fee_ids"]),set(ids))

    async def archive_case(self):
        async with self.sessions() as db:
            case=await db.get(BusinessRecord,self.case_id)
            case.status="已归档"
            await db.commit()

    async def test_unsubmitted_not_reviewed_and_refund_visible_after_explicit_apply(self):
        ids,_=await self.create_payment_selection(refund=True)
        before=await self.client.get(f"{API}/finance/internal-review-requests",params={"kind":"refund"})
        self.assertEqual(before.status_code,200,before.text)
        self.assertFalse(set(ids)&{item["id"] for item in before.json()["items"]})
        direct=await self.client.post(f"{API}/finance/internal-applications/batch-review",params={"kind":"refund"},json={"fee_ids":ids,"approved":True})
        self.assertEqual(direct.status_code,409,direct.text)
        response=await self.client.post(f"{API}/finance/internal-applications/payment-requests",json=self.payment_body(ids))
        self.assertEqual(response.status_code,200,response.text)
        # 10.22 第 6 行：案件未归档时退费提成在“内部提成-待归档”，不进退费审核队列。
        pending=await self.client.get(f"{API}/finance/internal-review-requests",params={"kind":"refund"})
        self.assertFalse(set(ids)&{item["id"] for item in pending.json()["items"]})
        archive=await self.client.get(f"{API}/finance/internal-fees",params={"scope":"archive"})
        self.assertEqual(archive.status_code,200,archive.text)
        self.assertIn(response.json()["application_no"],[item["serial_no"] for item in archive.json()["items"]])
        await self.archive_case()
        after=await self.client.get(f"{API}/finance/internal-review-requests",params={"kind":"refund"})
        self.assertEqual(after.status_code,200,after.text)
        group=next(item for item in after.json()["items"] if item["serial_no"]==response.json()["application_no"])
        self.assertEqual(group["data"]["amount"],270)
        self.assertEqual(len(group["data"]["application_items"]),5)

    async def test_pending_settlement_distinguishes_commission_from_source_and_cash(self):
        from app.core.internal_requests import pending_case_fee_settlements
        ids,source_id=await self.create_payment_selection()
        async with self.sessions() as db:
            rows=await pending_case_fee_settlements(IDENTITY,db)
            source=next(row for row in rows if row["id"]==source_id)
            self.assertEqual(source["data"]["amount"],270)
            self.assertEqual(source["data"]["cashed_amount"],0)
            fee=await db.get(BusinessRecord,source_id)
            fee.data={**fee.data,"received_amount":1000,"cashed_amount":1000}
            db.add(IncomingPayment(receipt_no="CODEX1021INTERNAL-RECEIPT",received_date=date.today(),amount=1000,
                payer_name="Row17 Customer",status="已分配",claimed_customer="Row17 Customer",claimant=IDENTITY["username"],
                operator=IDENTITY["username"],allocated_amount=1000,allocations=[{"fee_record_id":source_id,"amount":1000}]))
            await db.commit()
        async with self.sessions() as db:
            rows=await pending_case_fee_settlements(IDENTITY,db)
            source=next(row for row in rows if row["id"]==source_id)
            self.assertEqual(source["data"]["amount"],270)
            self.assertEqual(source["data"]["cashed_amount"],1000)

    async def test_duplicate_selection_and_paid_fee_fail_without_writes(self):
        ids,_=await self.create_payment_selection()
        body=self.payment_body(ids)
        bad={**body,"lines":[body["lines"][0],body["lines"][0]]}
        response=await self.client.post(f"{API}/finance/internal-applications/payment-requests",json=bad)
        self.assertEqual(response.status_code,422,response.text)
        async with self.sessions() as db:
            db.add(FinanceTransaction(finance_record_id=ids[-1],transaction_type="付款",amount=1,transaction_date=date.today(),operator=IDENTITY["username"]))
            await db.commit()
        response=await self.client.post(f"{API}/finance/internal-applications/payment-requests",json=body)
        self.assertEqual(response.status_code,409,response.text)
        async with self.sessions() as db:
            self.assertTrue(all(not item.data.get("internal_payment_submitted") for item in
                (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids)))).all()))


    async def test_refund_queue_newest_application_first_and_excludes_normal(self):
        ids,_=await self.create_payment_selection(refund=True)
        async with self.sessions() as db:
            for index,item_id in enumerate(ids):
                item=await db.get(BusinessRecord,item_id)
                item.data={**item.data,"payment_application_no":f"CODEX1021INTERNAL-APP-{index}",
                    "internal_payment_submitted":True,"internal_payment_submitted_at":f"2026-10-{index+10:02d}T12:00:00"}
            await db.commit()
        await self.archive_case()
        response=await self.client.get(f"{API}/finance/internal-review-requests",params={"kind":"refund","page_size":2})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual([item["id"] for item in response.json()["items"]],ids[::-1][:2])
        self.assertEqual(response.json()["total"],5)
        normal=await self.client.get(f"{API}/finance/internal-review-requests",params={"kind":"commission"})
        self.assertEqual(normal.status_code,200,normal.text)
        self.assertFalse(set(ids)&{item["id"] for item in normal.json()["items"]})

    async def test_other_user_cannot_apply_selected_case_fees(self):
        ids,_=await self.create_payment_selection()
        async with self.sessions() as db:
            db.add(User(username="CODEX1021INTERNAL-OTHER",display_name="其他",department="Other",role="employee",password_hash="x",is_active=True))
            await db.commit()
        app.dependency_overrides[current_identity]=lambda:{"username":"CODEX1021INTERNAL-OTHER","role":"employee","department":"Other"}
        response=await self.client.post(f"{API}/finance/internal-applications/payment-requests",json=self.payment_body(ids))
        self.assertIn(response.status_code,[403,404],response.text)
        async with self.sessions() as db:
            self.assertFalse((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.action=="提交内部费用付款申请"))).all())


    async def test_expense_approval_alone_is_not_a_payment_application(self):
        ids,_=await self.create_payment_selection()
        async with self.sessions() as db:
            item=await db.get(BusinessRecord,ids[0])
            item.status="已审批"
            item.data={key:value for key,value in item.data.items() if key not in {
                "commission_created_at","commission_lifecycle","commission_created_by","applicant","payment_application_no"}}
            db.add(WorkflowEvent(record_id=item.id,action="提交费用审批",to_status="待审批",operator=IDENTITY["username"]))
            db.add(WorkflowEvent(record_id=item.id,action="费用审批通过",to_status="已审批",operator=IDENTITY["username"]))
            await db.commit()
        response=await self.client.post(f"{API}/finance/internal-applications/payment-preview",json={"fee_ids":ids[:1]})
        self.assertEqual(response.status_code,200,response.text)
        self.assertFalse(response.json()["items"][0]["submitted"])
        result=await self.client.post(f"{API}/finance/internal-applications/payment-requests",json={"lines":self.payment_body(ids)["lines"][:1]})
        self.assertEqual(result.status_code,200,result.text)


    async def test_legacy_missing_commission_is_unknown_not_zero_in_totals(self):
        from app.core.internal_requests import pending_case_fee_settlements
        from app.core.internal_finance_query import internal_page
        ids,source_id=await self.create_payment_selection()
        async with self.sessions() as db:
            for item_id in ids:
                item=await db.get(BusinessRecord,item_id)
                item.status="已作废"
            source=await db.get(BusinessRecord,source_id)
            source.data={**source.data,"legacy_case_fee_id":"CODEX1021INTERNAL-LEGACY"}
            db.add(LegacyFinanceRecord(source_table="FAM_AR_CaseFee",legacy_id="CODEX1021INTERNAL-LEGACY",
                record_kind="case_fee",primary_amount=1000,is_active=True,
                source_payload={"SettlementStatus":"1","CashedAmount":1000}))
            await db.commit()
        async with self.sessions() as db:
            rows=await pending_case_fee_settlements(IDENTITY,db)
            self.assertEqual(len(rows),1)
            self.assertIsNone(rows[0]["data"]["amount"])
            self.assertEqual(rows[0]["data"]["cashed_amount"],1000)
            response=internal_page(rows,1,20,amount_visible=True)
            self.assertFalse(response["amount_totals_complete"])
            self.assertEqual(response["missing_commission_amount_count"],1)
            self.assertIsNone(response["total_amount"])
            self.assertEqual(response["total_cashed_amount"],1000)

if __name__ == "__main__": unittest.main()

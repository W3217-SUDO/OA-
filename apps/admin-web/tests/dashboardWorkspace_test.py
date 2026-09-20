"""控制台完整业务入口：真实接口、角色范围与固定筛选。"""
import unittest
from datetime import datetime
from sqlalchemy import select
import finance_0916_batch_test as fixtures
from finance_0916_batch_test import API, IDENTITY
from app.main import app
from app.security import current_identity, create_token
from app.models import BusinessRecord, User, JobRole
from app.core.dashboard_metrics import dashboard_metrics


class DashboardWorkspaceTest(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = fixtures.FinanceBatchTest.asyncTearDown

    async def asyncSetUp(self):
        await fixtures.FinanceBatchTest.asyncSetUp(self)
        async with self.sessions() as db:
            db.add(JobRole(code="LEGACY-ROLE-7", name="财务审核管理", is_active=True))
            for name, profile in (("mine", {}), ("audit", {"permission_role_code": "LEGACY-ROLE-7"}), ("empty", {})):
                db.add(User(username="CODEX-dashboard-"+name, display_name=name, role="user", password_hash="unused", is_active=True, profile=profile))
            self.ids = {}
            self.fees = {}
            for owner in ("mine", "other"):
                for key, phase in (("evidence-supplement", "一审补充证据"), ("opinion-supplement", "一审补充代理意见"), ("appeal-pending", "待上诉"), ("execution-pending", "一审待执行")):
                    case = BusinessRecord(module="case", serial_no=f"CODEX-dashboard-{owner}-{key}", title=key, owner="CODEX-dashboard-"+owner, status=phase, data={"case_type":"民事争议", "contract_id":self.contract_id, "case_phase_changed_at":"2020-01-01"}, created_at=datetime(2020,1,1), updated_at=datetime(2020,1,1))
                    db.add(case); await db.flush()
                    self.ids[owner,key]=case.id
                    fee=BusinessRecord(module="finance", serial_no=f"CODEX-dashboard-fee-{owner}-{key}", title="一审诉讼费", owner=IDENTITY["username"], status="草稿", data={"fee_type":"官方费用", "expense_subtype":"一审诉讼费", "amount":100, "refund_requested_amount":50, "case_id":case.id, "case_no":case.serial_no, "contract_id":self.contract_id})
                    db.add(fee); await db.flush();self.fees[owner,key]=fee.id
            await db.commit()
        app.dependency_overrides.pop(current_identity)

    def login(self, name):
        username = IDENTITY["username"] if name=="admin" else "CODEX-dashboard-"+name
        self.client.headers["Authorization"]="Bearer "+create_token(username,"user")
        return username

    async def test_eight_entries_roles_and_amounts(self):
        for name,count in (("mine",4),("audit",8),("admin",8),("empty",0)):
            username=self.login(name)
            async with self.sessions() as db:
                metrics=await dashboard_metrics({"username":username, "role":"user"},db)
            by_key={x["key"]:x for x in metrics["metrics"]}
            self.assertEqual(len(by_key),8)
            for key,item in by_key.items():self.assertEqual(item["route"],"dashboard-queue-"+key)
            for key,path in (("official-fee-unpaid","/finance/fees/query"),("refund-pending","/finance/case-fees/refunds")):
                response=await self.client.get(API+path,params={"dashboard_queue":key,"scope":"company","unpaid_official":False})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()["total"],count,response.text)
                self.assertEqual(len(response.json()["cases"]),count)
                self.assertEqual(by_key[key]["value"],f"{count}件")
                if name=="mine":self.assertTrue(all(row["id"] in [v for (owner,_),v in self.fees.items() if owner=="mine"] for row in response.json()["items"]))
            response=await self.client.get(API+"/receivables/detail",params={"dashboard_queue":"official-fee-unreceived"})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()["official_unreceived"],count*100)
            self.assertEqual(by_key["official-fee-unreceived"]["value"],f"{count*100:.2f}元")
            for key in ("evidence-supplement","opinion-supplement","appeal-pending","execution-pending"):
                response=await self.client.post(API+"/cases/search",json={"dashboard_queue":key,"scope":"company","page_size":1})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()["total"],count//4,(name,key,response.text))
                self.assertEqual(by_key[key]["value"],f"{count//4}件")
                if name=="mine":self.assertEqual(response.json()["items"][0]["id"],self.ids["mine",key])
            response=await self.client.post(API+"/cases/search",json={"dashboard_queue":"urgent-cases","scope":"company"})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(by_key["urgent-cases"]["value"],f'{response.json()["total"]}件')

    async def test_filters_export_invalid_scope_and_read_does_not_grant_write(self):
        self.login("mine")
        for path,key in (("/finance/fees/query","official-fee-unpaid"),("/finance/case-fees/refunds","refund-pending")):
            response=await self.client.get(API+path,params={"dashboard_queue":key,"case_no":"other"})
            self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()["total"],0)
            response=await self.client.get(API+path+"/export",params={"dashboard_queue":key})
            self.assertEqual(response.status_code,200,response.text);self.assertNotIn("CODEX-dashboard-other",response.text)
            response=await self.client.get(API+path,params={"dashboard_queue":"invalid"})
            self.assertEqual(response.status_code,422,response.text)
        response=await self.client.post(API+"/cases/search",json={"dashboard_queue":"invalid"})
        self.assertEqual(response.status_code,422,response.text)
        async with self.sessions() as db:
            user=await db.scalar(select(User).where(User.username=="CODEX-dashboard-mine"))
            user.profile={"permission_role":"missing-role"};await db.commit()
        response=await self.client.post(API+"/finance/case-fees/refunds/status",json={"ids":[self.fees["other","appeal-pending"]],"status":"R20"})
        self.assertGreaterEqual(response.status_code,400,response.text)

    async def test_refund_counts_cases_and_status_operation_persists(self):
        username=self.login("admin")
        async with self.sessions() as db:
            fee=await db.get(BusinessRecord,self.fees["mine","appeal-pending"])
            db.add(BusinessRecord(module="finance",serial_no="CODEX-dashboard-duplicate",title=fee.title,owner=fee.owner,status=fee.status,data=dict(fee.data)))
            await db.commit()
            metrics=await dashboard_metrics({"username":username,"role":"admin"},db)
        self.assertEqual(next(x for x in metrics["metrics"] if x["key"]=="refund-pending")["value"],"8件")
        response=await self.client.get(API+"/finance/case-fees/refunds",params={"dashboard_queue":"refund-pending"})
        self.assertEqual(response.json()["total"],9)
        fee_id=self.fees["mine","appeal-pending"]
        response=await self.client.post(API+"/finance/case-fees/refunds/status",json={"ids":[fee_id],"status":"R20"})
        self.assertEqual(response.status_code,200,response.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord,fee_id)).data["refund_status"],"R20")

    async def test_disabled_audit_role_does_not_grant_all_scope(self):
        self.login("audit")
        async with self.sessions() as db:
            role=await db.scalar(select(JobRole).where(JobRole.code=="LEGACY-ROLE-7"));role.is_active=False;await db.commit()
        response=await self.client.get(API+"/finance/fees/query",params={"dashboard_queue":"official-fee-unpaid"})
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()["total"],0)

if __name__=="__main__":unittest.main()

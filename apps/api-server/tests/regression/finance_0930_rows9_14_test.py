"""9.30 内部财务入口的隔离 API 验证。"""

import unittest
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FinanceTransaction, IncomingPayment, User, WorkflowEvent
from app.security import current_identity


class Finance930Rows9To14Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.identity = {"username": "finance-applicant", "display_name": "申请人", "role": "admin", "department": "上海分所"}
        async with self.sessions() as db:
            db.add(User(username="finance-applicant", display_name="申请人", role="admin",
                        department="上海分所", password_hash="x", is_active=True))
            case = BusinessRecord(module="case", serial_no="T930-CASE", title="测试案件",
                                  customer="测试客户", status="一审", owner="finance-applicant",
                                  department="上海分所", data={"plaintiff": "原告甲", "defendant": "被告乙",
                                                              "case_source": "案源人", "quality_manager": "品管人"})
            db.add(case)
            await db.flush()
            self.case_id = case.id

            normal = self._record("T930-AGENCY", "代理费", "草稿",
                                  {"fee_type": "代理费", "expense_scope": "律所", "amount": 100})
            refund = self._record("T930-REFUND", "律师代理费（退费）", "草稿",
                                  {"fee_type": "代理费", "expense_scope": "律所", "refund_fee": True,
                                   "expense_subtype": "律师代理费(退费)", "amount": 50})
            db.add_all([normal, refund])
            await db.flush()
            self.normal_source_id, self.refund_source_id = normal.id, refund.id
            self.normal_commissions = []
            self.refund_commissions = []
            for suffix, source, application, status, target in (
                ("N1", normal, "T930-NORMAL", "待审批", self.normal_commissions),
                ("N2", normal, "T930-NORMAL", "待审批", self.normal_commissions),
                ("R1", refund, "T930-REFUND-APP", "待结算", self.refund_commissions),
                ("R2", refund, "T930-REFUND-APP", "待结算", self.refund_commissions),
            ):
                fee = self._record(f"T930-{suffix}", "提成", status, {
                    "fee_type": "内部费用", "expense_scope": "内部", "amount": 10,
                    "commission_type": "案源提成",
                    **({"source_fee_id": source.id, "commission_lifecycle": "case_agency_fee"} if suffix.startswith("R") else {}),
                    "payment_application_no": application,
                    "applicant": "finance-applicant", "payee": suffix,
                }, owner=f"payee-{suffix}")
                db.add(fee)
                await db.flush()
                target.append(fee.id)
            pending = self._record("T930-NP", "待结算提成", "待结算", {
                "fee_type": "内部费用", "expense_scope": "内部", "amount": 3,
                "commission_type": "调查提成", "commission_lifecycle": "case_agency_fee",
                "source_fee_id": normal.id, "payment_application_no": "T930-PENDING",
                "applicant": "finance-applicant",
            })
            db.add(pending)
            other = self._record("T930-OTHER", "内部交通费", "待审批", {
                "fee_type": "内部费用", "expense_scope": "内部", "amount": 5,
                "applicant": "finance-applicant",
            })
            db.add(other)
            await db.flush()
            self.other_id = other.id
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://finance930.test")

    def _record(self, serial, title, status, data, owner="finance-applicant"):
        return BusinessRecord(module="finance", serial_no=serial, title=title, customer="测试客户",
                              status=status, owner=owner, department="上海分所",
                              data={"case_id": self.case_id, "case_no": "T930-CASE", **data})

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    async def test_payment_and_review_queues_are_disjoint(self):
        external = await self.client.get(f"{settings.api_prefix}/records", params={
            "module": "finance", "finance_view": "external", "page_size": 100,
        })
        self.assertEqual(external.status_code, 200, external.text)
        self.assertEqual({row["id"] for row in external.json()["items"]},
                         {self.normal_source_id, self.refund_source_id})
        first_page = await self.client.get(f"{settings.api_prefix}/records", params={
            "module": "finance", "finance_view": "external", "page_size": 1,
        })
        self.assertEqual(first_page.status_code, 200, first_page.text)
        self.assertEqual(first_page.json()["total"], 2)
        self.assertIn(first_page.json()["items"][0]["id"],
                      {self.normal_source_id, self.refund_source_id})
        payments = await self.client.get(f"{settings.api_prefix}/finance/payment-applications/query")
        self.assertEqual(payments.status_code, 200, payments.text)
        self.assertEqual({row["id"] for row in payments.json()["items"]},
                         {self.normal_source_id, self.refund_source_id})
        results = {}
        for kind in ("commission", "other", "refund"):
            response = await self.client.get(f"{settings.api_prefix}/finance/internal-review-requests", params={"kind": kind})
            self.assertEqual(response.status_code, 200, response.text)
            results[kind] = response.json()["items"]
        self.assertEqual(len(results["commission"]), 1)
        self.assertEqual(len(results["commission"][0]["data"]["application_items"]), 2)
        self.assertEqual([row["id"] for row in results["other"]], [self.other_id])
        self.assertEqual(len(results["refund"]), 1)
        self.assertEqual(results["refund"][0]["status"], "待审批")
        self.assertEqual(results["refund"][0]["title"], "测试案件")

    async def test_legacy_external_fee_without_classification_keys_survives_pagination(self):
        async with self.sessions() as db:
            legacy = self._record("T930-LEGACY-EXTERNAL", "旧外部费用", "待付款", {"amount": 12})
            db.add(legacy)
            await db.commit()
            legacy_id = legacy.id
        response = await self.client.get(f"{settings.api_prefix}/records", params={
            "module": "finance", "finance_view": "external", "page_size": 1,
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 3)
        listed_ids = set()
        for page in (1, 2, 3):
            listed = await self.client.get(f"{settings.api_prefix}/records", params={
                "module": "finance", "finance_view": "external", "page_size": 1, "page": page,
            })
            self.assertEqual(listed.status_code, 200, listed.text)
            listed_ids.add(listed.json()["items"][0]["id"])
        self.assertEqual(listed_ids, {self.normal_source_id, self.refund_source_id, legacy_id})
        payments = await self.client.get(f"{settings.api_prefix}/finance/payment-applications/query", params={
            "page_size": 1,
        })
        self.assertEqual(payments.status_code, 200, payments.text)
        self.assertEqual(payments.json()["total"], 3)
        payment_ids = set()
        for page in (1, 2, 3):
            listed = await self.client.get(f"{settings.api_prefix}/finance/payment-applications/query", params={
                "page_size": 1, "page": page,
            })
            self.assertEqual(listed.status_code, 200, listed.text)
            payment_ids.add(listed.json()["items"][0]["id"])
        self.assertEqual(payment_ids, listed_ids)

    async def test_refund_commissions_review_from_positive_refund_source(self):
        response = await self.client.post(f"{settings.api_prefix}/finance/internal-applications/batch-review", params={
            "kind": "refund",
        }, json={
            "fee_ids": self.refund_commissions[:1], "approved": True, "comment": "确认退费提成",
        })
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            for item_id in self.refund_commissions:
                item = await db.get(BusinessRecord, item_id)
                self.assertEqual(item.status, "已审批")
                self.assertTrue(item.data["is_refund"])
                self.assertEqual(item.data["commission_lifecycle"], "case_agency_refund")
        result = await self.client.get(f"{settings.api_prefix}/finance/internal-review-requests", params={"kind": "refund"})
        self.assertEqual(result.json()["items"], [])

    async def test_review_expands_application_and_rejects_wrong_queue_atomically(self):
        wrong = await self.client.post(f"{settings.api_prefix}/finance/internal-applications/batch-review", params={
            "kind": "other",
        }, json={"fee_ids": self.normal_commissions[:1], "approved": True, "comment": "审核"})
        self.assertEqual(wrong.status_code, 409)
        async with self.sessions() as db:
            self.assertEqual([(await db.get(BusinessRecord, item_id)).status
                              for item_id in self.normal_commissions], ["待审批", "待审批"])
        reviewed = await self.client.post(f"{settings.api_prefix}/finance/internal-applications/batch-review", params={
            "kind": "commission",
        }, json={"fee_ids": self.normal_commissions[:1], "approved": False, "comment": "整单驳回"})
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(set(reviewed.json()["fee_ids"]), set(self.normal_commissions))
        async with self.sessions() as db:
            self.assertEqual([(await db.get(BusinessRecord, item_id)).status
                              for item_id in self.normal_commissions], ["已驳回", "已驳回"])

    async def test_case_fee_pending_has_legacy_fields_and_manual_marker(self):
        async with self.sessions() as db:
            for index, (received, amount, payer) in enumerate((
                (date(2026, 9, 27), 20, "回款单位甲"),
                (date(2026, 9, 29), 35, "回款单位乙"),
            ), start=1):
                db.add(IncomingPayment(
                    receipt_no=f"T930-RECEIPT-{index}", received_date=received,
                    amount=amount, payer_name=payer, status="已分配", claimed_customer="测试客户",
                    case_no="T930-CASE", allocated_amount=amount, operator="finance-applicant",
                    allocations=[{"fee_record_id": self.normal_source_id,
                                  "case_no": "T930-CASE", "amount": amount}],
                ))
            await db.commit()
        result = await self.client.get(f"{settings.api_prefix}/finance/settlements/pending")
        self.assertEqual(result.status_code, 200, result.text)
        items = result.json()["items"]
        self.assertEqual([row["id"] for row in items], [self.normal_source_id])
        self.assertEqual(items[0]["data"]["plaintiff"], "原告甲")
        self.assertEqual(items[0]["data"]["opponent"], "被告乙")
        self.assertEqual(items[0]["data"]["quality_manager"], "品管人")
        self.assertEqual(items[0]["data"]["cashed_amount"], 55)
        self.assertEqual(items[0]["data"]["cashed_date"], "2026-09-29")
        self.assertEqual(items[0]["data"]["received_payer_name"], "回款单位乙")
        marked = await self.client.post(f"{settings.api_prefix}/finance/settlements/mark-commission-paid", json={
            "fee_ids": [self.normal_source_id], "comment": "已发放",
        })
        self.assertEqual(marked.status_code, 200, marked.text)
        after = await self.client.get(f"{settings.api_prefix}/finance/settlements/pending")
        self.assertEqual(after.json()["items"], [])
        duplicate = await self.client.post(f"{settings.api_prefix}/finance/settlements/mark-commission-paid", json={
            "fee_ids": [self.normal_source_id],
        })
        self.assertEqual(duplicate.status_code, 409)

    async def test_whole_application_withdraw_and_failure_are_atomic(self):
        response = await self.client.post(
            f"{settings.api_prefix}/finance/internal-applications/{self.normal_commissions[0]}/withdraw",
            json={"reason": "申请人撤回"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(set(response.json()["fee_ids"]), set(self.normal_commissions))
        async with self.sessions() as db:
            for item_id in self.normal_commissions:
                item = await db.get(BusinessRecord, item_id)
                self.assertEqual(item.status, "已撤回")
                events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == item_id,
                                                                  WorkflowEvent.action == "内部请款单撤回"))).all()
                self.assertEqual(len(events), 1)
        self.identity = {**self.identity, "username": "another-admin"}
        denied = await self.client.post(
            f"{settings.api_prefix}/finance/internal-applications/{self.refund_commissions[0]}/withdraw",
            json={"reason": "越权撤回"},
        )
        self.assertEqual(denied.status_code, 403)
        async with self.sessions() as db:
            db.add(FinanceTransaction(
                finance_record_id=self.refund_commissions[1], transaction_type="付款",
                amount=1, transaction_date=date(2026, 9, 30), operator="finance-applicant",
            ))
            await db.commit()
        self.identity = {**self.identity, "username": "finance-applicant"}
        blocked = await self.client.post(
            f"{settings.api_prefix}/finance/internal-applications/{self.refund_commissions[0]}/withdraw",
            json={"reason": "混合付款状态"},
        )
        self.assertEqual(blocked.status_code, 409)
        async with self.sessions() as db:
            statuses = [(await db.get(BusinessRecord, item_id)).status for item_id in self.refund_commissions]
        self.assertEqual(statuses, ["待结算", "待结算"])

    async def test_rollback_expands_application_and_requires_applicant_username(self):
        self.identity = {**self.identity, "username": "申请人", "display_name": "申请人"}
        denied = await self.client.post(
            f"{settings.api_prefix}/finance/internal-applications/{self.normal_commissions[0]}/rollback",
            json={"reason": "同名越权"},
        )
        self.assertEqual(denied.status_code, 403)
        self.identity = {**self.identity, "username": "finance-applicant"}
        result = await self.client.post(
            f"{settings.api_prefix}/finance/internal-applications/{self.normal_commissions[0]}/rollback",
            json={"reason": "申请人回滚"},
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(set(result.json()["fee_ids"]), set(self.normal_commissions))
        async with self.sessions() as db:
            self.assertEqual([(await db.get(BusinessRecord, item_id)).status
                              for item_id in self.normal_commissions], ["草稿", "草稿"])

    async def test_generic_single_actions_cannot_change_internal_application(self):
        fee_id = self.normal_commissions[0]
        actions = (
            (f"/finance/fees/{fee_id}/cancel", {"reason": "绕过申请人"}),
            (f"/finance/fees/{fee_id}/rollback", {"comment": "绕过整单"}),
            (f"/finance/fees/{fee_id}/approve", {"comment": "单笔通过"}),
            (f"/finance/fees/{fee_id}/review", {"approved": False, "comment": "单笔拒绝"}),
            ("/finance/fees/batch-review", {"fee_ids": [fee_id], "approved": True, "comment": "部分审批"}),
            ("/finance/fees/batch-review", {"fee_ids": [fee_id, self.normal_source_id],
                                             "approved": True, "comment": "混合审批"}),
        )
        async with self.sessions() as db:
            event_count = len((await db.scalars(select(WorkflowEvent))).all())
        for path, payload in actions:
            response = await self.client.post(f"{settings.api_prefix}{path}", json=payload)
            self.assertEqual(response.status_code, 409, (path, response.text))
            async with self.sessions() as db:
                self.assertEqual([(await db.get(BusinessRecord, item_id)).status
                                  for item_id in self.normal_commissions], ["待审批", "待审批"])
                self.assertEqual((await db.get(BusinessRecord, self.normal_source_id)).status, "草稿")
                self.assertEqual(len((await db.scalars(select(WorkflowEvent))).all()), event_count)

    async def test_application_submit_and_void_update_every_member(self):
        async with self.sessions() as db:
            for fee_id in self.normal_commissions:
                item = await db.get(BusinessRecord, fee_id)
                item.status = "草稿"
                item.data = {**item.data, "handler": "finance-applicant"}
            await db.commit()
        submitted = await self.client.post(
            f"{settings.api_prefix}/finance/fees/{self.normal_commissions[0]}/submit",
            json={"comment": "整单提交"},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(set(submitted.json()["fee_ids"]), set(self.normal_commissions))
        async with self.sessions() as db:
            self.assertEqual([(await db.get(BusinessRecord, fee_id)).status
                              for fee_id in self.normal_commissions], ["待审批", "待审批"])
            for fee_id in self.normal_commissions:
                self.assertEqual(len((await db.scalars(select(WorkflowEvent).where(
                    WorkflowEvent.record_id == fee_id, WorkflowEvent.action == "提交费用审批",
                ))).all()), 1)
        self.identity = {**self.identity, "username": "another-admin"}
        denied = await self.client.post(
            f"{settings.api_prefix}/finance/fees/{self.normal_commissions[0]}/submit",
            json={"comment": "非申请人提交"},
        )
        self.assertEqual(denied.status_code, 403, denied.text)
        self.identity = {**self.identity, "username": "finance-applicant"}
        async with self.sessions() as db:
            for fee_id in self.normal_commissions:
                item = await db.get(BusinessRecord, fee_id)
                item.status = "已驳回"
            await db.commit()
        voided = await self.client.post(
            f"{settings.api_prefix}/finance/fees/{self.normal_commissions[0]}/void",
            json={"comment": "整单作废"},
        )
        self.assertEqual(voided.status_code, 200, voided.text)
        self.assertEqual(set(voided.json()["fee_ids"]), set(self.normal_commissions))
        async with self.sessions() as db:
            for fee_id in self.normal_commissions:
                item = await db.get(BusinessRecord, fee_id)
                self.assertEqual(item.status, "已作废")
                self.assertEqual(item.data["payment_status"], "已作废")
                self.assertEqual(len((await db.scalars(select(WorkflowEvent).where(
                    WorkflowEvent.record_id == fee_id, WorkflowEvent.action == "请款单作废",
                ))).all()), 1)

    async def test_application_submit_and_void_fail_without_partial_writes(self):
        async with self.sessions() as db:
            for fee_id in self.normal_commissions:
                item = await db.get(BusinessRecord, fee_id)
                item.status = "草稿"
                item.data = {**item.data, "handler": "finance-applicant"}
            second = await db.get(BusinessRecord, self.normal_commissions[1])
            second.status = "待审批"
            await db.commit()
            event_count = len((await db.scalars(select(WorkflowEvent))).all())
        blocked_submit = await self.client.post(
            f"{settings.api_prefix}/finance/fees/{self.normal_commissions[0]}/submit",
            json={"comment": "不得部分提交"},
        )
        self.assertEqual(blocked_submit.status_code, 409, blocked_submit.text)
        async with self.sessions() as db:
            self.assertEqual([(await db.get(BusinessRecord, fee_id)).status
                              for fee_id in self.normal_commissions], ["草稿", "待审批"])
            self.assertEqual(len((await db.scalars(select(WorkflowEvent))).all()), event_count)
            for fee_id in self.normal_commissions:
                item = await db.get(BusinessRecord, fee_id)
                item.status = "已驳回"
            db.add(FinanceTransaction(
                finance_record_id=self.normal_commissions[1], transaction_type="付款",
                amount=1, transaction_date=date(2026, 9, 30), operator="finance-applicant",
            ))
            await db.commit()
            event_count = len((await db.scalars(select(WorkflowEvent))).all())
        blocked_void = await self.client.post(
            f"{settings.api_prefix}/finance/fees/{self.normal_commissions[0]}/void",
            json={"comment": "不得部分作废"},
        )
        self.assertEqual(blocked_void.status_code, 409, blocked_void.text)
        async with self.sessions() as db:
            self.assertEqual([(await db.get(BusinessRecord, fee_id)).status
                              for fee_id in self.normal_commissions], ["已驳回", "已驳回"])
            self.assertEqual(len((await db.scalars(select(WorkflowEvent))).all()), event_count)

    async def test_application_submit_rejects_mixed_internal_fee_categories(self):
        async with self.sessions() as db:
            for fee_id in self.normal_commissions:
                item = await db.get(BusinessRecord, fee_id)
                item.status = "草稿"
                item.data = {**item.data, "handler": "finance-applicant"}
            other = await db.get(BusinessRecord, self.normal_commissions[1])
            other.data = {key: value for key, value in other.data.items()
                          if key != "commission_type"}
            await db.commit()
            event_count = len((await db.scalars(select(WorkflowEvent))).all())
        response = await self.client.post(
            f"{settings.api_prefix}/finance/fees/{self.normal_commissions[0]}/submit",
            json={"comment": "混合类别不应提交"},
        )
        self.assertEqual(response.status_code, 409, response.text)
        async with self.sessions() as db:
            self.assertEqual([(await db.get(BusinessRecord, fee_id)).status
                              for fee_id in self.normal_commissions], ["草稿", "草稿"])
            self.assertEqual(len((await db.scalars(select(WorkflowEvent))).all()), event_count)

    async def test_ordinary_applicant_can_withdraw_when_payee_owns_fee(self):
        async with self.sessions() as db:
            db.add(User(username="finance-standard", display_name="普通申请人", role="user",
                        department="其他部门", password_hash="x", is_active=True))
            for fee_id in self.normal_commissions:
                item = await db.get(BusinessRecord, fee_id)
                item.data = {**item.data, "applicant": "finance-standard"}
            await db.commit()
        self.identity = {"username": "finance-standard", "display_name": "普通申请人",
                         "role": "user", "department": "其他部门"}
        listed = await self.client.get(f"{settings.api_prefix}/finance/internal-fees",
                                       params={"scope": "applications", "page": 1, "page_size": 20})
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn("T930-NORMAL", {row["serial_no"] for row in listed.json()["items"]})
        withdrawn = await self.client.post(
            f"{settings.api_prefix}/finance/internal-applications/{self.normal_commissions[0]}/withdraw",
            json={"reason": "普通申请人撤回"},
        )
        self.assertEqual(withdrawn.status_code, 200, withdrawn.text)
        async with self.sessions() as db:
            self.assertEqual([(await db.get(BusinessRecord, fee_id)).status
                              for fee_id in self.normal_commissions], ["已撤回", "已撤回"])

    async def test_standalone_internal_fee_submit_and_external_actions_remain_available(self):
        async with self.sessions() as db:
            standalone = self._record("T930-STANDALONE", "独立内部费用", "草稿", {
                "fee_type": "内部费用", "expense_scope": "内部", "amount": 5,
                "handler": "finance-applicant",
            })
            payment = self._record("T930-CASE-PAYMENT", "独立内部付款", "草稿", {
                "fee_type": "内部费用", "expense_scope": "内部", "amount": 5,
                "handler": "finance-applicant",
            })
            external = await db.get(BusinessRecord, self.normal_source_id)
            external.status = "待审批"
            external_cancel = self._record("T930-EXTERNAL-CANCEL", "外部费用撤回", "待审批", {
                "fee_type": "代理费", "expense_scope": "律所", "amount": 5,
            })
            external_rollback = self._record("T930-EXTERNAL-ROLLBACK", "外部费用回滚", "待审批", {
                "fee_type": "代理费", "expense_scope": "律所", "amount": 5,
            })
            db.add_all([standalone, payment, external_cancel, external_rollback])
            await db.commit()
            standalone_id, payment_id = standalone.id, payment.id
            external_cancel_id, external_rollback_id = external_cancel.id, external_rollback.id
        submitted = await self.client.post(f"{settings.api_prefix}/finance/fees/{standalone_id}/submit",
                                           json={"comment": "任务中心提交"})
        self.assertEqual(submitted.status_code, 200, submitted.text)
        payment_request = await self.client.post(f"{settings.api_prefix}/finance/fees/{payment_id}/submit", json={
            "amount": 2, "payment_payee": "测试收款人", "payment_account": "TEST-ACCOUNT",
            "comment": "案件费用提交付款",
        })
        self.assertEqual(payment_request.status_code, 200, payment_request.text)
        approved = await self.client.post(f"{settings.api_prefix}/finance/fees/{self.normal_source_id}/approve",
                                          json={"comment": "外部费审批"})
        self.assertEqual(approved.status_code, 200, approved.text)
        cancelled = await self.client.post(f"{settings.api_prefix}/finance/fees/{external_cancel_id}/cancel",
                                           json={"reason": "外部费撤回"})
        rolled_back = await self.client.post(f"{settings.api_prefix}/finance/fees/{external_rollback_id}/rollback",
                                             json={"comment": "外部费回滚"})
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(rolled_back.status_code, 200, rolled_back.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, standalone_id)).status, "待审批")
            self.assertEqual((await db.get(BusinessRecord, payment_id)).status, "待审批")
            self.assertEqual((await db.get(BusinessRecord, self.normal_source_id)).status, "已审批")
            self.assertEqual((await db.get(BusinessRecord, external_cancel_id)).status, "已撤回")
            self.assertEqual((await db.get(BusinessRecord, external_rollback_id)).status, "草稿")

    async def test_standalone_internal_fee_generic_followup_actions_remain_available(self):
        async with self.sessions() as db:
            ids = []
            for suffix in ("REVIEW", "CANCEL", "ROLLBACK"):
                item = self._record(f"T930-STANDALONE-{suffix}", "独立内部费用", "待审批", {
                    "fee_type": "内部费用", "expense_scope": "内部", "amount": 5,
                    "handler": "finance-applicant",
                })
                db.add(item)
                await db.flush()
                ids.append(item.id)
            await db.commit()
        queue = await self.client.get(f"{settings.api_prefix}/finance/internal-review-requests",
                                      params={"kind": "other"})
        self.assertEqual(queue.status_code, 200, queue.text)
        self.assertTrue(set(ids).issubset({row["id"] for row in queue.json()["items"]}))
        reviewed = await self.client.post(f"{settings.api_prefix}/finance/fees/{ids[0]}/review",
                                          json={"approved": True, "comment": "独立费审批"})
        cancelled = await self.client.post(f"{settings.api_prefix}/finance/fees/{ids[1]}/cancel",
                                           json={"reason": "独立费撤回"})
        rolled_back = await self.client.post(f"{settings.api_prefix}/finance/fees/{ids[2]}/rollback",
                                             json={"comment": "独立费回滚"})
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(rolled_back.status_code, 200, rolled_back.text)
        async with self.sessions() as db:
            self.assertEqual([(await db.get(BusinessRecord, fee_id)).status for fee_id in ids],
                             ["已审批", "已撤回", "草稿"])

    async def test_unnumbered_applicant_request_still_requires_applicant_route(self):
        async with self.sessions() as db:
            item = self._record("T930-APPLICANT-SINGLE", "内部请款", "待审批", {
                "fee_type": "内部费用", "expense_scope": "内部", "amount": 5,
                "applicant": "finance-applicant",
            }, owner="payee-owner")
            db.add(item)
            await db.commit()
            fee_id = item.id
        blocked = await self.client.post(f"{settings.api_prefix}/finance/fees/{fee_id}/cancel",
                                         json={"reason": "单笔旁路"})
        self.assertEqual(blocked.status_code, 409, blocked.text)
        withdrawn = await self.client.post(
            f"{settings.api_prefix}/finance/internal-applications/{fee_id}/withdraw",
            json={"reason": "申请人撤回"},
        )
        self.assertEqual(withdrawn.status_code, 200, withdrawn.text)
        self.assertEqual(withdrawn.json()["fee_ids"], [fee_id])
        async with self.sessions() as db:
            item = await db.get(BusinessRecord, fee_id)
            self.assertEqual(item.status, "已撤回")
            item.status = "草稿"
            item.data = {**item.data, "handler": "finance-applicant"}
            await db.commit()
        submitted = await self.client.post(
            f"{settings.api_prefix}/finance/fees/{fee_id}/submit",
            json={"comment": "无编号申请单提交"},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(submitted.json()["application_no"], "T930-APPLICANT-SINGLE")
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, fee_id)).status, "待审批")

    async def test_archived_settled_historical_commission_can_be_reviewed(self):
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.status = "已归档"
            source = await db.get(BusinessRecord, self.normal_source_id)
            source.data = {
                **(source.data or {}), "received_amount": 100, "cashed_amount": 100,
                "received_at": "2026-09-29", "cashed_date": "2026-09-29",
            }
            db.add(IncomingPayment(
                receipt_no="T930-HISTORY-RECEIPT", received_date=date(2026, 9, 29),
                amount=100, payer_name="测试客户", bank_reference="T930-HISTORY-BANK",
                status="已分配", claimed_customer="测试客户", claimant="finance-applicant",
                operator="finance-applicant", allocated_amount=100,
                allocations=[{"fee_record_id": self.normal_source_id, "case_no": "T930-CASE", "amount": 100}],
            ))
            db.add(BusinessRecord(
                module="finance_settlement", serial_no="T930-SETTLED", title="一般结算",
                customer="测试客户", status="已付款", owner="finance-applicant",
                department="上海分所", data={"allocation_details": [{"fee_id": self.normal_source_id}]},
            ))
            historical_ids = []
            for suffix in ("A", "B"):
                item = self._record(f"T930-HISTORY-{suffix}", "历史提成", "待归档", {
                    "fee_type": "内部费用", "expense_scope": "内部", "amount": 3,
                    "commission_type": "案源提成",
                    **({"commission_lifecycle": "case_agency_fee"} if suffix == "A" else {}),
                    "source_fee_id": self.normal_source_id,
                    "payment_application_no": "T930-HISTORY", "applicant": "finance-applicant",
                })
                db.add(item)
                await db.flush()
                historical_ids.append(item.id)
            await db.commit()
        other = await self.client.get(f"{settings.api_prefix}/finance/internal-review-requests",
                                      params={"kind": "other"})
        self.assertEqual(other.status_code, 200, other.text)
        self.assertFalse(set(historical_ids) & {row["id"] for row in other.json()["items"]})
        commission = await self.client.get(f"{settings.api_prefix}/finance/internal-review-requests",
                                           params={"kind": "commission"})
        self.assertEqual(commission.status_code, 200, commission.text)
        selected = [row for row in commission.json()["items"] if row["serial_no"] == "T930-HISTORY"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["status"], "待审批")
        self.assertEqual(len(selected[0]["data"]["application_items"]), 2)
        reviewed = await self.client.post(f"{settings.api_prefix}/finance/internal-applications/batch-review",
                                          params={"kind": "commission"}, json={
            "fee_ids": historical_ids[:1], "approved": True, "comment": "历史提成审批",
        })
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        async with self.sessions() as db:
            for fee_id in historical_ids:
                item = await db.get(BusinessRecord, fee_id)
                self.assertEqual(item.status, "已审批")
                events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == fee_id))).all()
                self.assertEqual([event.action for event in events], ["案件归档完成，提成进入待审批", "费用审批通过"])

    async def test_unsettled_commission_cannot_be_approved_by_direct_request(self):
        async with self.sessions() as db:
            item = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "T930-NP"))
            fee_id = item.id
            event_count = len((await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == fee_id,
            ))).all())
        denied = await self.client.post(f"{settings.api_prefix}/finance/internal-applications/batch-review",
                                        params={"kind": "commission"}, json={
            "fee_ids": [fee_id], "approved": True, "comment": "未结算不得审批",
        })
        self.assertEqual(denied.status_code, 409, denied.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, fee_id)).status, "待结算")
            self.assertEqual(len((await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == fee_id,
            ))).all()), event_count)

    async def test_other_internal_fee_review_is_whole_application(self):
        async with self.sessions() as db:
            ids = []
            for suffix in ("A", "B"):
                item = self._record(f"T930-OTHER-{suffix}", "内部交通费", "待审批", {
                    "fee_type": "内部费用", "expense_scope": "内部", "amount": 5,
                    "payment_application_no": "T930-OTHER-APP", "applicant": "finance-applicant",
                })
                db.add(item)
                await db.flush()
                ids.append(item.id)
            await db.commit()
        reviewed = await self.client.post(f"{settings.api_prefix}/finance/internal-applications/batch-review",
                                          params={"kind": "other"}, json={
            "fee_ids": ids[:1], "approved": False, "comment": "其他费整单拒绝",
        })
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(set(reviewed.json()["fee_ids"]), set(ids))
        async with self.sessions() as db:
            for fee_id in ids:
                self.assertEqual((await db.get(BusinessRecord, fee_id)).status, "已驳回")
                events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == fee_id))).all()
                self.assertEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main()

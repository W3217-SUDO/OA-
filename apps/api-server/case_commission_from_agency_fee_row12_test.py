import unittest
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, HrSubrecord, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
REPO_ROOT = Path(__file__).resolve().parents[2]
IDENTITY = {
    "username": "row12-admin",
    "role": "admin",
    "display_name": "第12行管理员",
    "department": "上海分所",
}


class CaseCommissionFromAgencyFeeRow12Test(unittest.IsolatedAsyncioTestCase):
    def test_pending_settlement_page_uses_commission_source_and_columns(self):
        route_config = (REPO_ROOT / "apps/admin-web/src/finance/config/routeConfigs.tsx").read_text(encoding="utf-8")
        queries = (REPO_ROOT / "apps/admin-web/src/finance/services/queriesActions.tsx").read_text(encoding="utf-8")
        page = (REPO_ROOT / "apps/admin-web/src/finance/FinanceCenterPage.tsx").read_text(encoding="utf-8")
        view = (REPO_ROOT / "apps/admin-web/src/finance/FinanceCenterView.tsx").read_text(encoding="utf-8")

        settle_config = route_config.split('"finance-internal-settle": {', 1)[1].split("},", 1)[0]
        for header in ("提成编号", "状态", "提成金额", "案件编号", "提成人", "来源代理费编号"):
            self.assertIn(f'"{header}"', settle_config)
        for unrelated_header in ("回款单位", "到账金额", "到账时间"):
            self.assertNotIn(f'"{unrelated_header}"', settle_config)
        self.assertIn('initialView === "finance-internal-settle"', queries)
        self.assertIn('api.get("/finance/settlements/pending")', queries)
        self.assertIn("提成编号: row.serial_no", page)
        self.assertIn("来源代理费编号: data.source_fee_no", page)
        self.assertNotIn("markCommissionPaid", view)

    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                department=IDENTITY["department"], role="admin", password_hash="x", is_active=True,
            ))
            employees = []
            for username, display_name in (
                ("row12-hearing", "开庭律师甲"),
                ("row12-assistant", "律师助理乙"),
                ("row12-source", "案源人丙"),
                ("row12-investigator", "调查员丁"),
            ):
                db.add(User(
                    username=username, display_name=display_name, department=IDENTITY["department"],
                    role="user", password_hash="x", is_active=True,
                ))
                employee = BusinessRecord(
                    module="hr", serial_no=f"CODEX-831-R12-HR-{len(employees) + 1}",
                    title=display_name, customer="", status="在职", owner=username,
                    department=IDENTITY["department"], data={"username": username, "is_active": True},
                )
                db.add(employee)
                employees.append(employee)
            await db.flush()
            db.add_all([
                HrSubrecord(
                    employee_id=employees[0].id, kind="commission",
                    data={"start_date": "2020-01-01", "end_date": "", "hearing_rate": 0.05, "hearing_fixed": 0},
                    created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
                ),
                HrSubrecord(
                    employee_id=employees[0].id, kind="commission",
                    data={"start_date": "2025-01-01", "end_date": "", "hearing_rate": 0.20, "hearing_fixed": 0},
                    created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
                ),
                HrSubrecord(
                    employee_id=employees[1].id, kind="commission",
                    data={"start_date": "2020-01-01", "end_date": "", "document_rate": 0, "document_fixed": 0},
                    created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
                ),
                HrSubrecord(
                    employee_id=employees[2].id, kind="commission",
                    data={"start_date": "2020-01-01", "end_date": "", "source_rate": 0, "source_fixed": 300},
                    created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
                ),
                HrSubrecord(
                    employee_id=employees[3].id, kind="commission",
                    data={"start_date": "2020-01-01", "end_date": "", "investigation_rate": 0.10, "investigation_fixed": 0},
                    created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
                ),
            ])
            case = BusinessRecord(
                module="case", serial_no="CODEX-831-R12-CASE", title="第12行提成测试案件",
                customer="第12行客户", status="一审立案受理", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={
                    "case_type": "民事争议", "case_creation_step": "completed",
                    "case_register_date": "2024-06-15",
                    "hearing_lawyer_usernames": ["row12-hearing"],
                    "hearing_lawyer_username": "row12-hearing",
                    "hearing_lawyer": "历史开庭律师",
                    "assistant_usernames": ["row12-assistant"],
                    "assistant": "律师助理乙", "assistants": ["律师助理乙", "历史助理"],
                    "source_person_usernames": ["row12-source"],
                    "source_person_username": "row12-source",
                    "source_person": "历史案源人",
                    "investigator_usernames": ["row12-investigator"],
                    "investigator": "调查员丁", "investigators": ["调查员丁", "历史调查员"],
                },
            )
            db.add(case)
            await db.flush()
            fee = BusinessRecord(
                module="finance", serial_no="CODEX-831-R12-FEE", title="代理费",
                customer=case.customer, status="草稿", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={"fee_type": "代理费", "expense_scope": "律所", "expense_subtype": "代理费", "amount": 8400, "case_id": case.id, "case_no": case.serial_no},
            )
            other_fee = BusinessRecord(
                module="finance", serial_no="CODEX-831-R12-OFFICIAL", title="官费",
                customer=case.customer, status="草稿", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={"fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "官费", "amount": 500, "case_id": case.id, "case_no": case.serial_no},
            )
            db.add_all([fee, other_fee])
            await db.commit()
            self.case_id, self.fee_id, self.other_fee_id = case.id, fee.id, other_fee.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row12.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    async def _create_one_commission(self) -> dict:
        preview = (await self.client.get(
            f"{API}/cases/{self.case_id}/commission-preview",
            params={"source_fee_id": self.fee_id},
        )).json()
        selected = preview["items"][0]
        response = await self.client.post(f"{API}/cases/{self.case_id}/commissions", json={
            "source_fee_id": self.fee_id,
            "items": [{
                "preview_key": selected["preview_key"],
                "actual_amount": selected["actual_amount"],
                "remark": "生命周期测试",
            }],
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["items"][0]

    async def test_preview_uses_selected_fee_case_people_and_commission_settings(self):
        response = await self.client.get(
            f"{API}/cases/{self.case_id}/commission-preview",
            params={"source_fee_id": self.fee_id},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["source_fee"]["amount"], 8400)
        rows = {item["commission_type"]: item for item in data["items"]}
        self.assertEqual(rows["开庭提成"]["employee_display_name"], "开庭律师甲")
        self.assertEqual(rows["开庭提成"]["base_amount"], 8400)
        self.assertEqual(rows["开庭提成"]["reference_commission"], 420)
        self.assertEqual(rows["案源固定提成"]["reference_commission"], 300)
        self.assertEqual(rows["调查提成"]["reference_commission"], 840)
        self.assertTrue(any("律师助理乙" in message and "文书" in message for message in data["missing_messages"]))
        self.assertEqual(data["case_date"], "2024-06-15")
        self.assertFalse(any("历史" in message for message in data["missing_messages"]))

    async def test_preview_uses_latest_customer_brand_manager_and_live_finance_summary(self):
        async with self.sessions() as db:
            for username, display_name in (("row12-quality-old", "旧品管"), ("row12-quality-new", "新品管")):
                db.add(User(
                    username=username, display_name=display_name, department=IDENTITY["department"],
                    role="user", password_hash="x", is_active=True,
                ))
                employee = BusinessRecord(
                    module="hr", serial_no=f"CODEX-831-R12-{username}", title=display_name,
                    customer="", status="在职", owner=username, department=IDENTITY["department"],
                    data={"username": username, "is_active": True},
                )
                db.add(employee)
                await db.flush()
                db.add(HrSubrecord(
                    employee_id=employee.id, kind="commission",
                    data={"start_date": "2020-01-01", "end_date": "", "quality_rate": 0.04, "quality_fixed": 0},
                    created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
                ))
            customer = BusinessRecord(
                module="customer", serial_no="CODEX-831-R12-CUSTOMER", title="第12行客户",
                customer="第12行客户", status="跟进中", owner="row12-quality-new",
                department=IDENTITY["department"],
                data={
                    "customer_managers": ["row12-quality-new", "row12-quality-old"],
                    "assignment_history": [
                        {"to_owner": "row12-quality-old", "created_at": "2024-01-01T00:00:00"},
                        {"to_owner": "row12-quality-new", "created_at": "2026-09-14T00:00:00"},
                    ],
                },
            )
            db.add(customer)
            await db.flush()
            case = await db.get(BusinessRecord, self.case_id)
            case.data = {**(case.data or {}), "customer_id": customer.id, "coordinator_username": "row12-quality-old"}
            other_fee = await db.get(BusinessRecord, self.other_fee_id)
            other_fee.data = {**(other_fee.data or {}), "refund_requested_amount": 500, "refunded_amount": 100}
            db.add(BusinessRecord(
                module="invoice", serial_no="CODEX-831-R12-INVOICE", title="第12行发票",
                customer=case.customer, status="已开票", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={
                    "case_id": case.id, "case_no": case.serial_no, "case_fee_ids": [self.fee_id],
                    "case_fee_allocations": [{"fee_id": self.fee_id, "amount": 8500, "over_amount": 100}],
                    "invoice_over_amount": 100,
                },
            ))
            await db.commit()

        response = await self.client.get(
            f"{API}/cases/{self.case_id}/commission-preview",
            params={"source_fee_id": self.fee_id},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        quality_rows = [item for item in data["items"] if item["commission_role"] == "品管"]
        self.assertEqual([item["employee_username"] for item in quality_rows], ["row12-quality-new"])
        self.assertEqual(quality_rows[0]["commission_type"], "品牌管理费")
        self.assertEqual(data["source_fee"]["refund_amount"], 400)
        self.assertEqual(data["source_fee"]["invoice_over_amount"], 100)
        self.assertEqual(data["source_fee"]["cost_over_amount"], 14.28)
        self.assertEqual(data["source_fee"]["amount"], 8385.72)
        self.assertEqual(quality_rows[0]["reference_commission"], 335.43)
        self.assertEqual(data["quality_manager_source"], "客户基本信息：CODEX-831-R12-CUSTOMER")

    async def test_batch_create_is_atomic_and_persists_source_relation(self):
        preview = (await self.client.get(
            f"{API}/cases/{self.case_id}/commission-preview",
            params={"source_fee_id": self.fee_id},
        )).json()
        selected = preview["items"][:2]
        response = await self.client.post(f"{API}/cases/{self.case_id}/commissions", json={
            "source_fee_id": self.fee_id,
            "items": [
                {"preview_key": selected[0]["preview_key"], "base_amount": 8000, "actual_amount": 400, "remark": "调整后金额"},
                {"preview_key": selected[1]["preview_key"], "actual_amount": selected[1]["actual_amount"], "remark": ""},
            ],
        })
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(result["total"], 2)
        self.assertTrue(result["application_no"].startswith("P"))
        self.assertEqual(len(result["payment_items"]), 2)
        self.assertTrue(all(item["application_no"] == result["application_no"] for item in result["payment_items"]))
        async with self.sessions() as db:
            rows = list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "finance",
                BusinessRecord.data["source_fee_id"].as_integer() == self.fee_id,
            ))).all())
            self.assertEqual(len(rows), 2)
            rows_by_type = {(row.data or {}).get("commission_type"): row for row in rows}
            self.assertEqual((rows_by_type[selected[0]["commission_type"]].data or {}).get("base_amount"), 8000)
            self.assertEqual((rows_by_type[selected[0]["commission_type"]].data or {}).get("reference_commission"), 400)
            self.assertEqual((rows_by_type[selected[1]["commission_type"]].data or {}).get("base_amount"), 8400)
            self.assertTrue(all(row.status == "待结算" for row in rows))
            self.assertTrue(all((row.data or {}).get("payment_status") == "待结算" for row in rows))
            self.assertTrue(all((row.data or {}).get("payment_application_no") == result["application_no"] for row in rows))
            self.assertTrue(all((row.data or {}).get("payment_requested_amount") == (row.data or {}).get("amount") for row in rows))
            self.assertTrue(all(not (row.data or {}).get("payment_applied_at") for row in rows))
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id.in_([row.id for row in rows])))).all())
            self.assertEqual(len(events), 2)
            self.assertTrue(all(event.action == "创建案件提成" and event.to_status == "待结算" for event in events))
            before = await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "finance"))
        failed = await self.client.post(f"{API}/cases/{self.case_id}/commissions", json={
            "source_fee_id": self.fee_id,
            "items": [
                {"preview_key": selected[0]["preview_key"], "actual_amount": 420, "remark": ""},
                {"preview_key": "expired:person:rate", "actual_amount": 1, "remark": ""},
            ],
        })
        self.assertEqual(failed.status_code, 422, failed.text)
        async with self.sessions() as db:
            after = await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "finance"))
        self.assertEqual(after, before)

    async def test_commission_lifecycle_requires_paid_settlement_and_archive(self):
        created = await self._create_one_commission()
        commission_id = created["id"]

        async with self.sessions() as db:
            commission = await db.get(BusinessRecord, commission_id)
            commission.status = "待审批"
            commission.data = {**(commission.data or {}), "payment_status": "待审批"}
            await db.commit()

        projected = await self.client.get(f"{API}/finance/fees/query", params={"page_size": 200})
        self.assertEqual(projected.status_code, 200, projected.text)
        projected_row = next(item for item in projected.json()["items"] if item["id"] == commission_id)
        self.assertEqual(projected_row["status"], "待结算")
        self.assertEqual(projected_row["data"]["payment_status"], "待结算")

        pending = await self.client.get(f"{API}/finance/settlements/pending")
        self.assertEqual(pending.status_code, 200, pending.text)
        pending_rows = [item for item in pending.json()["items"] if item["id"] == commission_id]
        self.assertEqual(len(pending_rows), 1)
        self.assertEqual(pending_rows[0]["status"], "待结算")
        self.assertEqual(pending_rows[0]["data"]["settlement_status"], "待结算")

        blocked = await self.client.post(
            f"{API}/finance/fees/{commission_id}/review",
            json={"approved": True, "comment": "错误提前审批"},
        )
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertIn("待结算", blocked.text)

        async with self.sessions() as db:
            settlement = BusinessRecord(
                module="finance_settlement", serial_no="CODEX-831-R12-SETTLEMENT",
                title="第12行一般结算", customer="第12行客户", status="待付款",
                owner=IDENTITY["username"], department=IDENTITY["department"],
                data={"allocation_details": [{"fee_id": self.fee_id, "case_id": self.case_id}]},
            )
            db.add(settlement)
            await db.commit()
            settlement_id = settlement.id

        paid = await self.client.post(
            f"{API}/finance/general-settlements/applications/payment",
            json={"application_ids": [settlement_id], "action": "paid", "comment": "一般结算完成"},
        )
        self.assertEqual(paid.status_code, 200, paid.text)
        async with self.sessions() as db:
            commission = await db.get(BusinessRecord, commission_id)
            self.assertEqual(commission.status, "待归档")
            self.assertEqual((commission.data or {}).get("payment_status"), "待归档")

        pending = await self.client.get(f"{API}/finance/settlements/pending")
        self.assertEqual(pending.status_code, 200, pending.text)
        self.assertNotIn(commission_id, [item["id"] for item in pending.json()["items"]])

        blocked = await self.client.post(
            f"{API}/finance/fees/{commission_id}/review",
            json={"approved": True, "comment": "归档前审批"},
        )
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertIn("待归档", blocked.text)

        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.status = "亏损审核"
            case.data = {**(case.data or {}), "archive_type": "deficit", "archive_submitter": ""}
            await db.commit()
        archived = await self.client.post(
            f"{API}/cases/{self.case_id}/archive/review",
            json={"approved": True, "comment": "同意归档"},
        )
        self.assertEqual(archived.status_code, 200, archived.text)
        async with self.sessions() as db:
            commission = await db.get(BusinessRecord, commission_id)
            self.assertEqual(commission.status, "待审批")
            self.assertEqual((commission.data or {}).get("payment_status"), "待审批")

            case = await db.get(BusinessRecord, self.case_id)
            case.status = "已归档"
            case.data = {
                **(case.data or {}),
                "status_before_archive": "执行",
                "unarchive_request": {"status": "待审批", "requested_by": "other-user"},
            }
            await db.commit()
        unarchived = await self.client.post(
            f"{API}/cases/{self.case_id}/unarchive/review",
            json={"approved": True, "comment": "同意解档"},
        )
        self.assertEqual(unarchived.status_code, 200, unarchived.text)
        async with self.sessions() as db:
            commission = await db.get(BusinessRecord, commission_id)
            self.assertEqual(commission.status, "待归档")

            case = await db.get(BusinessRecord, self.case_id)
            case.status = "亏损审核"
            case.data = {**(case.data or {}), "archive_type": "deficit", "archive_submitter": ""}
            await db.commit()
        archived_again = await self.client.post(
            f"{API}/cases/{self.case_id}/archive/review",
            json={"approved": True, "comment": "再次归档"},
        )
        self.assertEqual(archived_again.status_code, 200, archived_again.text)
        reviewed = await self.client.post(
            f"{API}/finance/fees/{commission_id}/review",
            json={"approved": True, "comment": "归档后审批"},
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["status"], "已审批")

        async with self.sessions() as db:
            settlement = await db.get(BusinessRecord, settlement_id)
            settlement.status = "已付款"
            case = await db.get(BusinessRecord, self.case_id)
            case.status = "已归档"
            case.data = {
                **(case.data or {}),
                "status_before_archive": "执行",
                "unarchive_request": {"status": "待审批", "requested_by": "other-user"},
            }
            await db.commit()
        preserved = await self.client.post(
            f"{API}/cases/{self.case_id}/unarchive/review",
            json={"approved": True, "comment": "审批后解档"},
        )
        self.assertEqual(preserved.status_code, 200, preserved.text)
        async with self.sessions() as db:
            commission = await db.get(BusinessRecord, commission_id)
            self.assertEqual(commission.status, "已审批")

    async def test_paid_settlement_rollback_returns_unreviewed_commission_to_pending_settlement(self):
        created = await self._create_one_commission()
        commission_id = created["id"]
        async with self.sessions() as db:
            settlement = BusinessRecord(
                module="finance_settlement", serial_no="CODEX-831-R12-ROLLBACK",
                title="第12行一般结算回退", customer="第12行客户", status="已付款",
                owner=IDENTITY["username"], department=IDENTITY["department"],
                data={"allocation_details": [{"fee_id": self.fee_id, "case_id": self.case_id}]},
            )
            db.add(settlement)
            await db.flush()
            commission = await db.get(BusinessRecord, commission_id)
            commission.status = "待归档"
            commission.data = {**(commission.data or {}), "payment_status": "待归档"}
            await db.commit()
            settlement_id = settlement.id

        rolled_back = await self.client.post(
            f"{API}/finance/general-settlements/applications/payment",
            json={"application_ids": [settlement_id], "action": "rollback", "comment": "付款回退"},
        )
        self.assertEqual(rolled_back.status_code, 200, rolled_back.text)
        async with self.sessions() as db:
            commission = await db.get(BusinessRecord, commission_id)
            self.assertEqual(commission.status, "待结算")
            self.assertEqual((commission.data or {}).get("payment_status"), "待结算")

    async def test_unlinked_participant_reports_each_missing_legacy_commission_setting(self):
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.data = {
                **(case.data or {}),
                "hearing_lawyer_usernames": [], "hearing_lawyer_username": "",
                "assistant_usernames": [], "assistant_username": "", "assistants": [],
                "source_person_usernames": [], "source_person_username": "",
                "hearing_lawyer": "外部合作律师",
                "assistant": "外部合作律师",
                "source_person": "外部合作律师",
            }
            await db.commit()

        response = await self.client.get(
            f"{API}/cases/{self.case_id}/commission-preview",
            params={"source_fee_id": self.fee_id},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertTrue(any("外部合作律师" in message and "开庭" in message for message in data["missing_messages"]))
        self.assertTrue(any("外部合作律师" in message and "文书" in message for message in data["missing_messages"]))
        self.assertTrue(any("外部合作律师" in message and "案源" in message for message in data["missing_messages"]))
        self.assertTrue(any(item["commission_type"] == "调查提成" for item in data["items"]))

    async def test_non_agency_fee_is_rejected(self):
        response = await self.client.get(
            f"{API}/cases/{self.case_id}/commission-preview",
            params={"source_fee_id": self.other_fee_id},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("必须选择一条代理费", response.text)

    async def test_migrated_lawyer_agency_fee_subtype_is_accepted(self):
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.title = "律师代理费"
            fee.data = {
                **(fee.data or {}),
                "fee_type": "其他费用",
                "expense_subtype": "律师代理费",
            }
            await db.commit()

        response = await self.client.get(
            f"{API}/cases/{self.case_id}/commission-preview",
            params={"source_fee_id": self.fee_id},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["source_fee"]["amount"], 8400)


if __name__ == "__main__":
    unittest.main()

import asyncio
import inspect
from pathlib import Path
import unittest

from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.crm.router import list_customers
from app.areas.finance.invoice_operations import create_invoice_application
from app.config import settings
from app.database import Base
from app.main import app
from app.models import BusinessRecord, SystemParameter, User


ROOT = Path(__file__).resolve().parents[4]


class Rework95BatchContractTest(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_employee_directory_permission_controls_full_scope_and_account_rows(self):
        source = self.read("apps/api-server/app/areas/hr/router.py")
        self.assertIn('can_view_company_directory = identity.get("role") == "admin" or "hr-all" in menu_keys', source)
        self.assertIn("if can_view_company_directory:", source)

    def test_empty_contract_delete_keeps_downstream_guards(self):
        source = self.read("apps/api-server/app/core/contracts.py")
        self.assertIn("allow_empty_contract: bool = False", source)
        for model in ("ReceivablePlan", "IncomingPayment", "ContractPaymentLine"):
            self.assertIn(model, source)
        self.assertIn("只能删除本人创建的空合同", source)

    def test_archived_contracts_are_blocked_from_downstream_creation(self):
        source = self.read("apps/api-server/app/core/contracts.py")
        for status in ("归档中", "归档审核中", "已归档"):
            self.assertIn(status, source)

    def test_contract_change_and_repeated_seal_application_are_supported(self):
        source = self.read("apps/api-server/app/areas/contract/router.py")
        self.assertIn('"seal_applications": [*previous_seal_items', source)
        self.assertIn("归档或已终止的合同不能发起变更", source)
        policy = self.read("apps/admin-web/src/contractWorkflowPolicy.mjs")
        self.assertIn('canChange: allowed("change", secondaryPolicy.canEdit)', policy)
        self.assertIn('pending_change', policy)
        center = self.read("apps/admin-web/src/contract/ContractCenterPage.tsx")
        modals = self.read("apps/admin-web/src/contract/ContractModals.tsx")
        app = self.read("apps/admin-web/src/App.tsx")
        self.assertIn("contract-change-${r.id}-", center)
        self.assertIn('mode={isContractChangeView ? "page" : "modal"}', center)
        self.assertIn('mode?: "modal" | "page"', modals)
        self.assertIn('active.startsWith("contract-change-")', app)

    def test_seal_candidate_and_submission_share_contract_approver_capability(self):
        source = self.read("apps/api-server/app/core/documents.py")
        self.assertIn('action_keys.add(SEAL_ACTION_CODES["approve"])', source)
        self.assertIn('granted["approve"] = True', source)
        self.assertIn('return action == "approve" and bool((user.profile or {}).get("contract_approval_enabled"))', source)

    def test_customer_people_resolve_inactive_users_and_hr_aliases(self):
        async def verify() -> None:
            engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
            sessions = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            try:
                async with engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
                async with sessions() as db:
                    db.add_all([
                        User(username="admin", display_name="测试管理员", role="admin", department="测试部", password_hash="x", is_active=True),
                        User(username="retired", display_name="离职客户经理", role="user", department="测试部", password_hash="x", is_active=False),
                        SystemParameter(category="customer_type", code="CUSTOMER", name="客户", sort_order=1, is_active=True),
                        BusinessRecord(module="hr", serial_no="HR-ALIAS-95", title="历史员工姓名", customer="", status="在职", owner="admin", department="测试部", data={"legacy_guid": "HR-GUID-95"}),
                        BusinessRecord(module="customer", serial_no="KH-PEOPLE-95", title="历史客户", customer="历史客户", status="我的客户", owner="admin", department="测试部", data={
                            "customer_type": "客户", "customer_managers": ["retired"], "customer_source": "HR-GUID-95",
                        }),
                    ])
                    await db.commit()
                    result = await list_customers(
                        scope="company", customer_name="", customer_type="客户", manager="", page=1, page_size=15,
                        identity={"username": "admin", "role": "admin"}, db=db,
                    )
                self.assertEqual(result["total"], 1)
                people = result["items"][0]["data"]
                self.assertEqual(people["customer_manager_display_names"], ["离职客户经理"])
                self.assertEqual(people["customer_source_display_name"], "历史员工姓名")
            finally:
                await engine.dispose()

        asyncio.run(verify())

    def test_clue_edit_and_detail_use_structured_indictees(self):
        modal = self.read("apps/admin-web/src/investigation/EditRecordModal.tsx")
        page = self.read("apps/admin-web/src/investigation/InvestigationCenterPage.tsx")
        self.assertIn('<Form.List name="indictees">', modal)
        self.assertIn('name={[name, "confirmation_method"]}', modal)
        self.assertIn('name={[name, "region"]}', modal)
        self.assertIn("indictees: Array.isArray(v.indictees) ? v.indictees : []", page)
        self.assertIn('join("；")', page)

    def test_invoice_uses_individual_fee_candidates_and_finance_routing(self):
        contract_router = self.read("apps/api-server/app/areas/contract/router.py")
        frontend = self.read("apps/admin-web/src/contract/services/financeActions.tsx")
        invoice_helper = self.read("apps/admin-web/src/financeInvoiceHelpers.mjs")
        self.assertIn('/contracts/{{contract_id}}/invoice-candidates', contract_router)
        self.assertIn('"fee_id": row["id"]', contract_router)
        self.assertIn("selectedInvoiceObjectKeys.map(Number).includes(item.fee_id)", frontend)
        self.assertIn("一次申请开票只能选择同一客户下的费用", invoice_helper)
        self.assertIn("case_no: oneCase ? caseNos[0]", invoice_helper)
        invoice_routes = [
            route for route in app.routes
            if isinstance(route, APIRoute)
            and route.path == f"{settings.api_prefix}/finance/invoices"
            and "POST" in route.methods
        ]
        self.assertEqual(len(invoice_routes), 1)
        self.assertIs(invoice_routes[0].endpoint, create_invoice_application)
        invoice_source = inspect.getsource(create_invoice_application)
        self.assertIn('data["accounting_center"] = "平台财务中心" if', invoice_source)
        self.assertIn("增值税专用发票必须填写注册地址", invoice_source)

    def test_payment_snapshot_routes_by_contract_body(self):
        source = self.read("apps/api-server/app/areas/contract/router.py")
        self.assertIn('accounting_center = "平台财务中心"', source)
        self.assertIn('"finance_scope": "platform"', source)
        snapshot_source = self.read("apps/api-server/app/core/contract_payment_lifecycle.py")
        self.assertIn('"lines": snapshot', snapshot_source)

    def test_legacy_parameter_migration_builds_real_roots_and_audits_orphans(self):
        source = self.read("scripts/migrate_legacy_system_parameters.py")
        self.assertIn("LEGACY-FEE-GROUP-", source)
        self.assertIn('result[-1]["is_active"] = legacy_id > 0 and result[-1]["is_active"]', source)
        self.assertIn("if parent_id > 0 else", source)
        self.assertIn("def audit(rows", source)
        self.assertNotIn("await db.delete(item)", source)


if __name__ == "__main__":
    unittest.main()

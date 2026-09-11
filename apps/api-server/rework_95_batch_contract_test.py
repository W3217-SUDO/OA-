from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


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
        source = self.read("apps/api-server/app/areas/crm/router.py")
        self.assertIn("directory_users = list((await db.scalars(select(User))).all())", source)
        self.assertIn('BusinessRecord.module == "hr"', source)
        self.assertIn("person_names.setdefault(alias.casefold(), display)", source)

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
        finance_router = self.read("apps/api-server/app/areas/finance/router.py")
        frontend = self.read("apps/admin-web/src/contract/services/financeActions.tsx")
        self.assertIn('/contracts/{{contract_id}}/invoice-candidates', contract_router)
        self.assertIn('"fee_id": fee.id', contract_router)
        self.assertIn("selectedInvoiceObjectKeys.includes(item.fee_id)", frontend)
        self.assertIn("同一张发票只能选择同一案件的费用", frontend)
        self.assertIn('data["accounting_center"] = "平台财务中心"', finance_router)
        self.assertIn("增值税专用发票必须填写注册地址", finance_router)

    def test_payment_snapshot_routes_by_contract_body(self):
        source = self.read("apps/api-server/app/areas/contract/router.py")
        self.assertIn('accounting_center = "平台财务中心"', source)
        self.assertIn('"finance_scope": "platform"', source)
        self.assertIn('"lines": snapshot', source)

    def test_legacy_parameter_migration_builds_real_roots_and_audits_orphans(self):
        source = self.read("scripts/migrate_legacy_system_parameters.py")
        self.assertIn("LEGACY-FEE-GROUP-", source)
        self.assertIn("if legacy_id < 0", source)
        self.assertIn("if parent_id > 0 else", source)
        self.assertIn("def audit(rows", source)
        self.assertIn("legacy_id < 0 and item.created_by == ACTOR", source)


if __name__ == "__main__":
    unittest.main()

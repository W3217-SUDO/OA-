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
        self.assertIn('canChange: allowed("change", secondaryPolicy.canEdit && !pendingChange)', policy)

    def test_customer_people_resolve_inactive_users_and_hr_aliases(self):
        source = self.read("apps/api-server/app/areas/crm/router.py")
        self.assertIn("directory_users = list((await db.scalars(select(User))).all())", source)
        self.assertIn('BusinessRecord.module == "hr"', source)
        self.assertIn("person_names.setdefault(alias.casefold(), display)", source)

    def test_clue_edit_and_detail_use_structured_indictees(self):
        modal = self.read("apps/admin-web/src/investigation/EditRecordModal.tsx")
        page = self.read("apps/admin-web/src/investigation/InvestigationCenterPage.tsx")
        self.assertIn('<Form.List name="indictees">', modal)
        self.assertIn("indictees: Array.isArray(v.indictees) ? v.indictees : []", page)
        self.assertIn('join("；")', page)


if __name__ == "__main__":
    unittest.main()

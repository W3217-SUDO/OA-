import inspect
import unittest

from app.main import CIVIL_CASE_TYPES, JOB_ROLE_ACTION_KEY_GRANTS, NORMAL_CASE_BASIC_TYPES, _case_action_granted, _case_detail_action_capabilities, update_normal_case_basic


class LegacyCivilAdminEditContractTest(unittest.TestCase):
    def test_legacy_civil_names_use_normal_basic_and_civil_endpoints(self):
        self.assertEqual(CIVIL_CASE_TYPES, {"民事案件", "民事争议", "民事"})
        self.assertTrue(CIVIL_CASE_TYPES.issubset(NORMAL_CASE_BASIC_TYPES))

    def test_visible_basic_edit_capability_uses_case_visibility(self):
        capability_source = inspect.getsource(_case_detail_action_capabilities)
        save_source = inspect.getsource(update_normal_case_basic)
        self.assertIn("can_edit_basic = active", capability_source)
        self.assertIn('await _require_case_action(identity, db, "case.detail.update")', save_source)
        self.assertNotIn('can_edit_basic = role == "manager" and await _case_action_granted', capability_source)

    def test_system_admin_is_an_explicit_case_action_superuser(self):
        action_source = inspect.getsource(_case_action_granted)
        self.assertIn('if action_code.startswith("case."):', action_source)
        self.assertIn('if "admin" in _identity_role_ids(identity):', action_source)
        self.assertIn('return "*" in action_keys or action_code in action_keys', action_source)

    def test_admin_can_grant_basic_edit_through_case_handling_role_action(self):
        self.assertIn("case.detail.update", JOB_ROLE_ACTION_KEY_GRANTS["案件承办"])


if __name__ == "__main__":
    unittest.main()

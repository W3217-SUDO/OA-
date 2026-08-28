import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).resolve().parent / "scripts" / "repair_migrated_case_people.py"
SPEC = importlib.util.spec_from_file_location("repair_migrated_case_people", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def employee(record_id, username, name, *, status="在职", active=True, migrated=True):
    return SimpleNamespace(
        id=record_id,
        module="hr",
        serial_no=str(record_id),
        title=name,
        owner=username,
        status=status,
        department="离职过渡",
        data={
            "username": username,
            "account_type": "员工账号",
            "is_active": active,
            **({"legacy_hr_identity": {"legacy_staff_id": record_id}} if migrated else {}),
        },
    )


def user(record_id, username, name, *, active=True):
    return SimpleNamespace(id=record_id, username=username, display_name=name, department="诉讼部", is_active=active)


def case(data, *, owner="admin"):
    return SimpleNamespace(serial_no="GDXS2300088", owner=owner, data=data)


class MigratedCasePeopleRepairTests(unittest.TestCase):
    def catalog(self, users=None, employees=None):
        return MODULE.build_identity_plan(users or [], employees or [])

    def test_missing_legacy_employee_gets_login_identity_plan(self):
        plan = self.catalog(employees=[employee(33754, "lixue", "李雪")])
        self.assertEqual([item["identity"].username for item in plan["creates"]], ["lixue"])
        self.assertTrue(plan["creates"][0]["identity"].is_active)

    def test_duplicate_employee_username_is_not_guessed(self):
        plan = self.catalog(employees=[employee(1, "same", "甲"), employee(2, "same", "乙")])
        self.assertEqual(plan["creates"], [])
        self.assertEqual(plan["issues"][0]["kind"], "duplicate_employee_username")

    def test_non_migrated_broken_employee_is_reported_without_account_creation(self):
        plan = self.catalog(employees=[employee(3, "manual", "手工档案", migrated=False)])
        self.assertEqual(plan["creates"], [])
        self.assertEqual(plan["issues"][0]["kind"], "missing_non_migrated_login")

    def test_existing_case_username_becomes_valid_when_employee_identity_exists(self):
        plan = self.catalog(employees=[employee(33754, "lixue", "李雪")])
        repaired = MODULE.plan_case_repair(
            case({"handling_lawyers": ["李雪"], "handling_lawyer_usernames": ["lixue"], "case_team_usernames": ["lixue"]}, owner="lixue"),
            plan["identities"], plan["display_groups"],
        )
        self.assertEqual(repaired["updates"], {})
        self.assertEqual(repaired["owner"], "")
        self.assertEqual(repaired["issues"], [])

    def test_chinese_only_assistant_backfills_username_and_case_team(self):
        plan = self.catalog(users=[user(1, "fwl", "范文玲")])
        repaired = MODULE.plan_case_repair(
            case({"assistant": "范文玲", "case_team_usernames": ["admin"]}),
            plan["identities"], plan["display_groups"],
        )
        self.assertEqual(repaired["updates"]["assistant_username"], "fwl")
        self.assertEqual(repaired["updates"]["case_team_usernames"], ["admin", "fwl"])

    def test_stale_account_uses_unique_current_display_name(self):
        plan = self.catalog(users=[user(1, "new-account", "李雪")])
        repaired = MODULE.plan_case_repair(
            case({"assistant": "李雪", "assistant_username": "old-account"}),
            plan["identities"], plan["display_groups"],
        )
        self.assertEqual(repaired["updates"]["assistant_username"], "new-account")

    def test_username_stored_in_display_field_is_resolved(self):
        plan = self.catalog(users=[user(1, "wengjie", "翁洁")])
        repaired = MODULE.plan_case_repair(
            case({"source_person": "wengjie"}), plan["identities"], plan["display_groups"],
        )
        self.assertEqual(repaired["updates"]["source_person_username"], "wengjie")
        self.assertEqual(repaired["updates"]["source_person"], "翁洁")

    def test_duplicate_display_name_stays_unresolved(self):
        plan = self.catalog(users=[user(1, "one", "王敏"), user(2, "two", "王敏")])
        repaired = MODULE.plan_case_repair(
            case({"assistant": "王敏"}), plan["identities"], plan["display_groups"],
        )
        self.assertNotIn("assistant_username", repaired["updates"])
        self.assertEqual(repaired["issues"][0]["status"], "ambiguous")

    def test_inactive_employee_identity_is_preserved_but_not_activated(self):
        plan = self.catalog(employees=[employee(9, "old-user", "历史员工", status="停用", active=False)])
        self.assertFalse(plan["creates"][0]["identity"].is_active)

    def test_resigned_but_not_disabled_employee_can_still_login(self):
        plan = self.catalog(employees=[employee(10, "resigned-user", "离职员工", status="离职", active=True)])
        self.assertTrue(plan["creates"][0]["identity"].is_active)

    def test_migrated_business_owner_backfills_case_source_person(self):
        plan = self.catalog(users=[user(1, "lixue", "李雪")])
        repaired = MODULE.plan_case_repair(
            case({"business_owner": "李雪", "business_owner_username": "lixue"}, owner="lixue"),
            plan["identities"],
            plan["display_groups"],
        )
        self.assertEqual(repaired["updates"]["source_person"], "李雪")
        self.assertEqual(repaired["updates"]["source_person_username"], "lixue")

    def test_legacy_participants_get_chinese_names_and_team_accounts(self):
        plan = self.catalog(users=[user(1, "lixue", "李雪"), user(2, "tgn", "陶国南")])
        repaired = MODULE.plan_case_repair(
            case({
                "case_team_usernames": ["lixue"],
                "legacy_participants": [{"staff_name": "lixue"}, {"staff_name": "tgn"}],
            }),
            plan["identities"],
            plan["display_groups"],
        )
        self.assertEqual(repaired["updates"]["legacy_participant_display_names"], ["李雪", "陶国南"])
        self.assertEqual(repaired["updates"]["case_team_usernames"], ["lixue", "tgn"])
        self.assertEqual(repaired["issues"], [])

    def test_unknown_legacy_participant_is_reported_without_guessing(self):
        plan = self.catalog(users=[user(1, "lixue", "李雪")])
        repaired = MODULE.plan_case_repair(
            case({"legacy_participants": [{"staff_name": "unknown-old-account"}]}),
            plan["identities"],
            plan["display_groups"],
        )
        self.assertNotIn("legacy_participant_display_names", repaired["updates"])
        self.assertEqual(repaired["issues"][0]["field"], "legacy_participants")
        self.assertEqual(repaired["issues"][0]["status"], "missing")

    def test_historical_employee_name_repairs_display_without_creating_login(self):
        employees = [employee(251, "chaixx", "柴笑笑", active=False, migrated=False)]
        names = MODULE.build_historical_name_map(employees, [])
        plan = self.catalog(employees=employees)
        repaired = MODULE.plan_case_repair(
            case({"legacy_participants": [{"staff_name": "chaixx"}]}),
            plan["identities"],
            plan["display_groups"],
            names,
        )
        self.assertEqual(repaired["updates"]["legacy_participant_display_names"], ["柴笑笑"])
        self.assertEqual(repaired["issues"][0]["status"], "historical_display_only")

    def test_historical_numbered_account_uses_unique_base_name_for_display_only(self):
        employees = [employee(152, "gucy", "顾春燕", active=False, migrated=False)]
        names = MODULE.build_historical_name_map(employees, [])
        plan = self.catalog(employees=employees)
        repaired = MODULE.plan_case_repair(
            case({"legacy_participants": [{"staff_name": "gucy1"}]}),
            plan["identities"],
            plan["display_groups"],
            names,
        )
        self.assertEqual(repaired["updates"]["legacy_participant_display_names"], ["顾春燕"])


if __name__ == "__main__":
    unittest.main()

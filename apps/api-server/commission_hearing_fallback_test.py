import copy
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.cases import (
    _case_commission_personnel_changed,
    _case_commission_preview_for_amount,
    _case_commission_role_person_tokens,
)
from app.core.constants import CASE_COMMISSION_ROLES


class CommissionHearingFallbackTest(unittest.IsolatedAsyncioTestCase):
    hearing = next(role for role in CASE_COMMISSION_ROLES if role["key"] == "hearing")

    def test_only_first_handling_account_is_used_without_mutation(self):
        data = {
            "handling_lawyer_usernames": ["first", "second"],
            "handling_lawyers": ["Stale name", "Second name"],
        }
        original = copy.deepcopy(data)
        self.assertEqual(_case_commission_role_person_tokens(data, self.hearing), ["first"])
        self.assertEqual(data, original)

    def test_explicit_hearing_aliases_override_handling_accounts(self):
        for field in self.hearing["fields"]:
            with self.subTest(field=field):
                value = ["explicit", "another"] if field.endswith(("usernames", "lawyers")) else "explicit"
                data = {field: value, "handling_lawyer_usernames": ["first", "second"]}
                expected = value if isinstance(value, list) else [value]
                self.assertEqual(_case_commission_role_person_tokens(data, self.hearing), expected)

    def test_explicit_account_wins_over_display_projection(self):
        data = {"hearing_lawyer_username": "explicit", "hearing_lawyers": ["Stale name"]}
        self.assertEqual(_case_commission_role_person_tokens(data, self.hearing), ["explicit"])

    def test_empty_hearing_and_legacy_handling_names(self):
        data = {"hearing_lawyer_usernames": [], "hearing_lawyer": "-", "handling_lawyers": ["First name", "Second name"]}
        self.assertEqual(_case_commission_role_person_tokens(data, self.hearing), ["First name"])
        self.assertEqual(_case_commission_role_person_tokens({}, self.hearing), [])
        self.assertEqual(_case_commission_role_person_tokens({"handling_lawyer_username": "first"}, self.hearing), ["first"])

    def test_other_roles_do_not_use_handling_fallback(self):
        for role in CASE_COMMISSION_ROLES:
            if role["key"] != "hearing":
                self.assertEqual(_case_commission_role_person_tokens({"handling_lawyer_usernames": ["first"]}, role), [])

    def test_change_detection_uses_same_effective_person(self):
        before = {"handling_lawyer_usernames": ["first", "second"]}
        self.assertTrue(_case_commission_personnel_changed(before, {"handling_lawyer_usernames": ["second", "first"]}))
        self.assertFalse(_case_commission_personnel_changed(before, {"handling_lawyer_usernames": ["first", "third"]}))
        self.assertFalse(_case_commission_personnel_changed(
            {**before, "hearing_lawyer": "explicit"},
            {"handling_lawyer_usernames": ["second"], "hearing_lawyer": "explicit"},
        ))

    async def test_missing_scheme_queries_only_bound_first_employee(self):
        employee = SimpleNamespace(id=47227, title="Bound lawyer", data={"username": "fwl"})
        case = SimpleNamespace(
            id=47167, serial_no="CODEX-HEARING-FALLBACK", title="Fixture",
            data={"handling_lawyer_usernames": ["fwl", "other"], "handling_lawyers": ["Stale name", "Other"]},
        )
        lookup = AsyncMock(return_value=None)
        with patch("app.core.formatters._dashboard_case_date", return_value=datetime(2026, 1, 1)), \
                patch("app.core.cases._round_case_commission_amount", side_effect=lambda value: round(value, 2)), \
                patch("app.core.cases._commission_scheme_record_for_case", lookup):
            result = await _case_commission_preview_for_amount(
                case, 100, None, employee_index={"fwl": employee},
                active_users_by_username={"fwl": SimpleNamespace(username="fwl", display_name="Bound lawyer")},
            )
        lookup.assert_awaited_once_with(47227, date(2026, 1, 1), None)
        self.assertEqual(result["items"], [])
        self.assertEqual([person["username"] for person in result["personnel"]], ["fwl"])
        self.assertEqual(result["missing_messages"], [
            "Bound lawyer\uff08\u5f00\u5ead\uff09\uff1a\u65e0\u8986\u76d6\u6848\u4ef6\u65e5\u671f 2026-01-01 \u7684\u6709\u6548\u63d0\u6210\u65b9\u6848",
        ])


if __name__ == "__main__":
    unittest.main()

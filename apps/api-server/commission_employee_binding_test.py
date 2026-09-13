import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.core.cases import _case_commission_person_tokens, _case_commission_preview_for_amount
from app.core.system import _commission_employee_index


class CommissionEmployeeBindingTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def employee(record_id, username, *, owner="admin", title="Employee"):
        return SimpleNamespace(
            id=record_id, owner=owner, title=title, status="active",
            data={"username": username},
        )

    @staticmethod
    def user(username, display_name="Employee"):
        return SimpleNamespace(username=username, display_name=display_name, is_active=True)

    async def index(self, employees, users):
        db = SimpleNamespace(scalars=AsyncMock(side_effect=[
            Mock(all=Mock(return_value=employees)),
            Mock(all=Mock(return_value=users)),
        ]))
        return await _commission_employee_index(db)

    async def preview(self, token, index, users, *, case_data=None, has_scheme=True):
        case = SimpleNamespace(
            id=100, serial_no="CODEX-BINDING", title="Binding fixture",
            data=case_data if case_data is not None else {"assistant_username": token},
        )
        # No engine/session or business data is created; all reads are mocks.
        scheme = SimpleNamespace(id=200, data={"document_rate": 0.05})
        lookup = AsyncMock(return_value=scheme if has_scheme else None)
        with patch("app.core.formatters._dashboard_case_date", return_value=datetime(2026, 1, 1)), \
                patch("app.core.cases._round_case_commission_amount", side_effect=lambda value: round(value, 2)), \
                patch("app.core.cases._commission_scheme_record_for_case", lookup):
            result = await _case_commission_preview_for_amount(
                case, 100, None, employee_index=index,
                active_users_by_username={user.username: user for user in users},
            )
        return result, lookup

    async def test_creator_owner_does_not_block_unique_current_account(self):
        employee = self.employee(1, "fwl", owner="admin")
        users = [self.user("admin", "Administrator"), self.user("fwl")]
        index = await self.index([employee], users)
        self.assertNotIn("admin", index)
        result, lookup = await self.preview("fwl", index, users)
        self.assertEqual(result["missing_messages"], [])
        self.assertEqual(result["items"][0]["employee_username"], "fwl")
        self.assertEqual(result["items"][0]["actual_amount"], 5)
        self.assertEqual(lookup.await_args.args[0], employee.id)

    async def test_duplicate_current_account_blocks_historical_owner(self):
        first = self.employee(1, "admin", owner="taowei", title="Legacy employee")
        second = self.employee(2, "admin", owner="admin", title="Administrator")
        users = [self.user("admin", "Administrator")]
        for employees in ([first, second], [second, first]):
            index = await self.index(employees, users)
            self.assertIs(index["taowei"], first)
            self.assertIsNone(index["admin"])
            for token in ("taowei", "admin", "Legacy employee"):
                result, lookup = await self.preview(token, index, users)
                self.assertEqual(result["items"], [])
                self.assertTrue(result["missing_messages"])
                lookup.assert_not_awaited()

    async def test_current_account_precedes_same_name_alias(self):
        account = self.employee(1, "fwl", title="Account employee")
        alias = self.employee(2, "other", title="fwl")
        users = [self.user("fwl", "Account employee"), self.user("other", "Other employee")]
        for employees in ([account, alias], [alias, account]):
            index = await self.index(employees, users)
            self.assertIs(index["fwl"], account)
            result, lookup = await self.preview("fwl", index, users)
            self.assertEqual(result["items"][0]["employee_username"], "fwl")
            self.assertEqual(lookup.await_args.args[0], account.id)

    async def test_alias_cannot_resolve_to_another_current_employee(self):
        alias = self.employee(1, "fwl", title="Legacy employee")
        account = self.employee(2, "fwl", title="Account employee")
        result, lookup = await self.preview(
            "Legacy employee", {"legacy employee": alias, "fwl": account}, [self.user("fwl")],
        )
        self.assertEqual(result["items"], [])
        self.assertTrue(result["missing_messages"])
        lookup.assert_not_awaited()

    async def test_duplicate_display_names_do_not_pick_first_employee(self):
        first = self.employee(1, "first", title="Shared name")
        second = self.employee(2, "second", title="Shared name")
        users = [self.user("first", "Shared name"), self.user("second", "Shared name")]
        index = await self.index([first, second], users)
        self.assertIsNone(index["shared name"])
        self.assertIs(index["first"], first)
        self.assertIs(index["second"], second)

    def test_stable_account_precedes_display_even_when_fields_are_reordered(self):
        fields = ("assistant", "assistant_usernames", "assistant_username")
        data = {"assistant": "TAOWEI", "assistant_username": "tw", "assistant_usernames": ["tw"]}
        self.assertEqual(_case_commission_person_tokens(data, fields), ["tw"])
        self.assertEqual(_case_commission_person_tokens({"assistant": "TAOWEI"}, fields), ["TAOWEI"])

    async def test_stable_account_ignores_ambiguous_legacy_display(self):
        actual = self.employee(1, "tw", owner="tw", title="TAOWEI")
        legacy = self.employee(2, "admin", owner="taowei", title="Legacy employee")
        administrator = self.employee(3, "admin", owner="admin", title="Administrator")
        users = [self.user("tw", "TAOWEI"), self.user("admin", "Administrator")]
        index = await self.index([legacy, administrator, actual], users)
        self.assertIsNone(index["taowei"])
        self.assertIs(index["tw"], actual)
        data = {"assistant_usernames": ["tw"], "assistant_username": "tw", "assistant": "TAOWEI"}
        for has_scheme in (True, False):
            result, lookup = await self.preview(
                "tw", index, users, case_data=data, has_scheme=has_scheme,
            )
            lookup.assert_awaited_once()
            self.assertEqual(lookup.await_args.args[0], actual.id)
            self.assertEqual([item["username"] for item in result["personnel"]], ["tw"])
            if has_scheme:
                self.assertEqual(result["missing_messages"], [])
                self.assertEqual([item["employee_username"] for item in result["items"]], ["tw"])
            else:
                self.assertEqual(result["items"], [])
                self.assertEqual(len(result["missing_messages"]), 1)

    async def test_missing_stable_account_does_not_fall_back_to_display_employee(self):
        display_employee = self.employee(1, "other", title="TAOWEI")
        users = [self.user("other", "TAOWEI")]
        index = await self.index([display_employee], users)
        result, lookup = await self.preview(
            "tw", index, users,
            case_data={"assistant_usernames": ["tw"], "assistant": "TAOWEI"},
        )
        self.assertEqual(result["items"], [])
        self.assertEqual(result["personnel"], [])
        self.assertTrue(result["missing_messages"])
        lookup.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

"""279951：回款(工行/中信/中行/招商) 四个页面直接“导入”“删除”未导入流水，和“银行原始流水”用同一张表、同一套接口。"""
import unittest
from unittest import mock

from fastapi import HTTPException

from app.areas.finance import bank_flows
from app.models import BankStatementLine
from app.security import _PAGE_MENU_PREFIXES, _route_prefix_match

USER = {"username": "cw", "role": "user", "_finance_scope": "firm"}


def _line(bank):
    return BankStatementLine(bank=bank, finance_scope="firm", payer_name="甲", amount=1, status="未导入", uploaded_by="cw")


def _candidates(path):
    for prefix, menus in sorted(_PAGE_MENU_PREFIXES, key=lambda item: len(item[0]), reverse=True):
        if _route_prefix_match(path, prefix):
            return menus
    return ()


class BankPageFlowMenuTest(unittest.IsolatedAsyncioTestCase):
    async def _check(self, menus, lines, scope="firm"):
        payload = mock.AsyncMock(return_value={"menu_keys": menus})
        with mock.patch("app.core.permissions._permission_payload_for_identity", payload):
            await bank_flows._require_flow_menu({**USER, "_finance_scope": scope}, None, lines)

    async def test_bank_page_menu_allows_its_own_bank(self):
        await self._check(["finance-receipts-icbc"], [_line("icbc")])
        await self._check(["platform-finance-overview-cmb"], [_line("cmb")], scope="platform")
        await self._check(["finance-receipts-bank-flow"], [_line("boc"), _line("citic")])

    async def test_other_bank_or_other_center_page_is_refused(self):
        for menus, lines, scope in (
            (["finance-receipts-icbc"], [_line("boc")], "firm"),
            (["finance-receipts-icbc"], [_line("icbc"), _line("cmb")], "firm"),
            (["finance-receipts-icbc"], [_line("icbc")], "platform"),
        ):
            with self.assertRaises(HTTPException) as caught:
                await self._check(menus, lines, scope)
            self.assertEqual(caught.exception.status_code, 403)

    def test_line_endpoints_open_to_bank_pages_but_legacy_mirror_is_not(self):
        for path in ("/finance/bank-flows/lines", "/finance/bank-flows/generate", "/finance/bank-flows/delete"):
            menus = _candidates(path)
            self.assertIn("finance-receipts-citic", menus)
            self.assertIn("platform-finance-overview-icbc", menus)
            self.assertIn("finance-receipts-bank-flow", menus)
        self.assertNotIn("finance-receipts-citic", _candidates("/finance/bank-flows"))


if __name__ == "__main__":
    unittest.main()

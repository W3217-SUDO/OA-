"""501585（shenhe 11-05）：回款管理里不需要的银行页面不在左侧菜单和角色权限树显示，后端授权仍认。"""
import re
import unittest
from pathlib import Path

from app.core.constants import NAV_HIDDEN_RECEIPT_MENU_KEYS, ROLE_TREE_HIDDEN_MENU_KEYS, SYSTEM_MENU_ROUTE_KEYS

HIDDEN = {"finance-receipts-citic", "finance-receipts-bank-flow", "platform-finance-overview-citic",
          "platform-finance-overview-cmb", "platform-finance-overview-gdicbc", "platform-finance-overview-bank-flow"}
KEPT = {"finance-receipts-icbc", "finance-receipts-boc", "finance-receipts-cmb", "finance-receipts-gdicbc",
        "platform-finance-overview-icbc", "platform-finance-overview-boc"}


class ReceiptMenusHidden501585Test(unittest.TestCase):
    def test_hidden_in_role_tree_but_other_bank_pages_stay(self):
        self.assertEqual(set(NAV_HIDDEN_RECEIPT_MENU_KEYS), HIDDEN)
        self.assertTrue(HIDDEN <= ROLE_TREE_HIDDEN_MENU_KEYS)
        self.assertFalse(KEPT & ROLE_TREE_HIDDEN_MENU_KEYS)
        self.assertTrue(HIDDEN <= SYSTEM_MENU_ROUTE_KEYS, "菜单和路由保留，旧链接仍能打开")

    def test_frontend_nav_filters_same_keys(self):
        app = (Path(__file__).resolve().parents[2] / "admin-web/src/App.tsx").read_text(encoding="utf-8")
        block = re.search(r"NAV_HIDDEN_RECEIPT_MENU_KEYS = new Set\(\[(.*?)\]\)", app, re.S).group(1)
        self.assertEqual(set(re.findall(r'"([a-z-]+)"', block)), HIDDEN)
        self.assertIn("!NAV_HIDDEN_RECEIPT_MENU_KEYS.has(item.key)", app)


if __name__ == "__main__":
    unittest.main()

"""Contract creation is authorized by the visible contract-new menu."""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.main import _require_contract_action


class ContractCreateVisiblePermissionTest(unittest.IsolatedAsyncioTestCase):
    async def test_visible_contract_menu_allows_creation_without_action_key(self):
        permission = {
            "menu_keys": ["contract-new"],
            "action_keys": [],
            "field_keys": [],
            "data_scope": "本人及共享数据",
        }
        identity = {"username": "creator", "role": "user", "role_ids": ["user"]}
        with patch("app.main._permission_payload_for_identity", new=AsyncMock(return_value=permission)):
            await _require_contract_action(identity, None, "contract.application.create", "新建")

    async def test_hidden_create_menu_remains_denied(self):
        permission = {
            "menu_keys": ["user-center"],
            "action_keys": [],
            "field_keys": [],
            "data_scope": "本人及共享数据",
        }
        identity = {"username": "viewer", "role": "user", "role_ids": ["user"]}
        with patch("app.main._permission_payload_for_identity", new=AsyncMock(return_value=permission)):
            with self.assertRaises(HTTPException) as error:
                await _require_contract_action(identity, None, "contract.application.create", "新建")
        self.assertEqual(error.exception.status_code, 403)

    async def test_visible_contract_menu_allows_other_actions_without_action_keys(self):
        permission = {
            "menu_keys": ["contract-new", "contract-mine"],
            "action_keys": [],
            "field_keys": [],
            "data_scope": "本人及共享数据",
        }
        identity = {"username": "creator", "role": "user", "role_ids": ["user"]}
        with patch("app.main._permission_payload_for_identity", new=AsyncMock(return_value=permission)):
            await _require_contract_action(identity, None, "contract.application.update", "维护")
            await _require_contract_action(identity, None, "contract.application.submit", "提交审批")
            await _require_contract_action(identity, None, "contract.payment.create", "发起付款申请")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import ast
import unittest
from pathlib import Path


SOURCE = Path(__file__).with_name("app").joinpath("main.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


class OrdinaryUserSealMenuContractTest(unittest.TestCase):
    def test_default_user_can_open_only_their_own_seal_workspace(self) -> None:
        self.assertIn('"seal-my"', SOURCE)
        default_roles = next(
            node for node in TREE.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "DEFAULT_ROLE_PERMISSIONS" for target in node.targets)
        )
        text = ast.unparse(default_roles)
        user_config = text.split("'user':", 1)[1]
        self.assertIn("'seal-my'", user_config)
        self.assertNotIn("'seal-audit'", user_config)
        self.assertNotIn("'seal-admin'", user_config)

    def test_existing_user_role_is_migrated_to_seal_my_leaves(self) -> None:
        self.assertIn("ordinary_user_seal_my_menu_v1", SOURCE)
        self.assertIn('_stored_menu_permission_keys(["seal-my"])', SOURCE)
        self.assertIn("UPDATE role_permissions SET menu_keys", SOURCE)


if __name__ == "__main__":
    unittest.main()

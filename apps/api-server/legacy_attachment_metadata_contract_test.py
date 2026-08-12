from __future__ import annotations

import ast
import unittest
from pathlib import Path


SOURCE = Path(__file__).with_name("app").joinpath("main.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


class LegacyAttachmentMetadataContractTest(unittest.TestCase):
    def test_attachment_response_keeps_identity_and_adds_display_name(self) -> None:
        function = next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == "_attachment_dict")
        text = ast.unparse(function)
        self.assertIn("uploader_display_name", text)
        self.assertIn("item.uploader", text)
        self.assertIn("uploader_names", text)

    def test_attachment_list_bulk_resolves_system_user_names(self) -> None:
        function = next(node for node in TREE.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "list_attachments")
        text = ast.unparse(function)
        self.assertIn("_user_display_map(uploader_usernames, db)", text)
        self.assertIn("_person_display_name(user.display_name, user.username)", text)
        self.assertIn("_attachment_dict(item, records.get(item.record_id), uploader_names)", text)


if __name__ == "__main__":
    unittest.main()

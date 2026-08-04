"""Red contract tests for atomic contract attachment batch deletion.

This file intentionally does not start an HTTP server or mutate the database.
It locks the legacy FCM contract-file delete contract and the minimum local
backend shape Terra should schedule in app/main.py.
"""

from pathlib import Path
import re
import unittest


HERE = Path(__file__).resolve().parent
LOCAL_MAIN = HERE / "app" / "main.py"
OLD_ROOT = HERE.parent.parent.parent / "旧系统归档源码" / "SH.CRM.WEB"
OLD_FILE_CONTROLLER = OLD_ROOT / "Areas" / "FCM" / "Controllers" / "ContractFileController.cs"
OLD_CONTRACT_JS = OLD_ROOT / "Scripts" / "FCM" / "Contract" / "FCM.Contract.js"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def local_route_source(source: str) -> str:
    pattern = re.compile(
        r'@app\.post\(f"\{settings\.api_prefix\}/contracts/\{\{contract_id\}\}/attachments/delete"[^\n]*\)\s*\n'
        r'async def (?P<name>[a-zA-Z0-9_]+)\([^\n]+\):',
    )
    match = pattern.search(source)
    if not match:
        return ""
    start = match.start()
    next_route = re.search(r"\n@app\.", source[match.end():])
    end = len(source) if next_route is None else match.end() + next_route.start()
    return source[start:end]


class ContractAttachmentBatchDeleteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local = text(LOCAL_MAIN)
        cls.legacy_controller = text(OLD_FILE_CONTROLLER)
        cls.legacy_js = text(OLD_CONTRACT_JS)
        cls.route = local_route_source(cls.local)

    def test_legacy_contract_file_delete_accepts_many_file_ids_and_envelope(self):
        self.assertIn("Delete(List<long> fileIds)", self.legacy_controller)
        self.assertIn("ContractFileService.Instance.Delete(fileIds)", self.legacy_controller)
        self.assertIn('response.Message = "删除成功！"', self.legacy_controller)
        self.assertIn("response.IsSuccess = true", self.legacy_controller)
        self.assertIn('response.Message = "删除失败！"', self.legacy_controller)
        self.assertIn("response.IsSuccess = false", self.legacy_controller)
        self.assertIn("/FCM/ContractFile/Delete", self.legacy_js)
        self.assertIn("fileIds", self.legacy_js)

    def test_local_contract_batch_delete_endpoint_exists_and_accepts_legacy_file_ids(self):
        self.assertTrue(self.route, "missing POST /contracts/{contract_id}/attachments/delete")
        self.assertRegex(self.route, r"file_ids|fileIds")
        self.assertIn("dict.fromkeys", self.route)
        self.assertIn("FileAttachment.id.in_", self.route)

    def test_local_prevalidates_every_selected_file_before_any_mutation(self):
        self.assertTrue(self.route, "missing contract attachment batch delete route")
        required_guards = [
            "len(attachments) != len",
            "record_id == contract_id",
            'item.category != "合同附件"',
            "_require_contract_attachment_write_access",
        ]
        for token in required_guards:
            self.assertIn(token, self.route)
        first_delete = self.route.find("db.delete")
        self.assertGreater(first_delete, 0, "route must eventually delete prepared attachments")
        for token in required_guards:
            self.assertLess(self.route.find(token), first_delete, f"{token} must run before db.delete")

    def test_local_is_atomic_for_db_rows_and_physical_files(self):
        self.assertTrue(self.route, "missing contract attachment batch delete route")
        for token in (
            "prepared",
            "staged",
            "path.replace",
            "await db.rollback()",
            "await db.commit()",
            "WorkflowEvent",
            "unlink",
        ):
            self.assertIn(token, self.route)

    def test_local_returns_http_200_legacy_envelope_for_failures_and_success(self):
        self.assertTrue(self.route, "missing contract attachment batch delete route")
        self.assertNotIn("status_code=status.HTTP_204_NO_CONTENT", self.route)
        self.assertIn('"IsSuccess": False', self.route)
        self.assertIn('"IsSuccess": True', self.route)
        self.assertIn('"Message"', self.route)
        self.assertNotIn("raise HTTPException(status_code=404", self.route)
        self.assertNotIn("raise HTTPException(status_code=403", self.route)


if __name__ == "__main__":
    unittest.main()

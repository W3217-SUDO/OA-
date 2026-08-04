"""Red contract gates for the next seal backend batch.

These tests intentionally perform no HTTP call, database write, or file IO
outside reading source files. They lock the missing backend contracts before
the shared app/main.py window is granted.
"""

from pathlib import Path
import re
import unittest


HERE = Path(__file__).resolve().parent
LOCAL_MAIN = HERE / "app" / "main.py"
OLD_ROOT = HERE.parent.parent.parent / "旧系统归档源码" / "SH.CRM.WEB"
OLD_CONTROLLER = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentController.cs"
OLD_FILE_CONTROLLER = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentFileController.cs"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def function_span(source: str, function_name: str) -> str:
    start = source.index(f"async def {function_name}")
    next_route = source.find("@app.", start + 10)
    return source[start:] if next_route < 0 else source[start:next_route]


def assert_contains(case: unittest.TestCase, source: str, token: str, context: str) -> None:
    case.assertTrue(token in source, f"{context} missing token: {token!r}")


def assert_matches(case: unittest.TestCase, source: str, pattern: str, context: str) -> None:
    case.assertIsNotNone(re.search(pattern, source), f"{context} missing pattern: {pattern}")


class SealBackendAttachmentCopyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local = read(LOCAL_MAIN)
        cls.old_controller = read(OLD_CONTROLLER)
        cls.old_file_controller = read(OLD_FILE_CONTROLLER)

    def test_legacy_contract_and_case_create_copy_source_files(self):
        self.assertIn("CreateByContract(string id,string contractNo, string contractFileIds)", self.old_controller)
        self.assertIn("ContractFileService.Instance.GetContractFile(fileId)", self.old_controller)
        self.assertIn("ContractFileService.Instance.GetContractFileListByContractNo(contractNo)", self.old_controller)
        self.assertIn("CreateByCase(string id, string caseNo, string caseFileIds)", self.old_controller)
        self.assertIn("CaseFileService.Instance.GetCaseFile(long.Parse(fileId))", self.old_controller)
        self.assertIn("OfficialDocumentFileService.Instance.CreateUpdate(officialDocumentFile, bytes)", self.old_controller)

    def test_local_create_input_accepts_source_attachment_ids(self):
        dto = self.local[self.local.index("class SealApplicationInput"):self.local.index("class SealPackageDownloadInput")]
        assert_matches(self, dto, r"(contract_file_ids|case_file_ids|source_attachment_ids)\s*:", "SealApplicationInput")

    def test_local_create_application_copies_contract_and_case_files_atomically(self):
        source = function_span(self.local, "create_seal_application")
        for token in (
            "_copy_seal_source_attachments",
            "FileAttachment",
            "source_attachment_ids",
            "await db.rollback()",
            "target.unlink",
            "WorkflowEvent",
        ):
            assert_contains(self, source, token, "create_seal_application")

    def test_local_source_copy_helper_verifies_permissions_and_compensates_files(self):
        assert_contains(self, self.local, "async def _copy_seal_source_attachments", "app/main.py")
        start = self.local.index("async def _copy_seal_source_attachments")
        end = self.local.find("\n\n@app.", start)
        helper = self.local[start:] if end < 0 else self.local[start:end]
        for token in (
            "_ensure_record_module",
            "_ensure_attachment_record_visible",
            "category = \"用印文件\"",
            "target.write_bytes",
            "await db.rollback()",
            "unlink(missing_ok=True)",
        ):
            assert_contains(self, helper, token, "_copy_seal_source_attachments")

    def test_legacy_file_upload_is_multi_file_and_local_has_atomic_multi_upload(self):
        self.assertIn("for (int i = 0; i < Request.Files.Count; i++)", self.old_file_controller)
        self.assertIn("OfficialDocumentFileUpload(OfficialDocumentModel model)", self.old_file_controller)
        assert_matches(self, self.local, r"async def upload_seal_(application_)?files", "app/main.py")
        upload_source = function_span(self.local, "upload_seal_application_files")
        for token in (
            "files: list[UploadFile]",
            "prepared",
            "await db.rollback()",
            "unlink(missing_ok=True)",
            "_sync_seal_document_names",
        ):
            assert_contains(self, upload_source, token, "upload_seal_application_files")

    def test_legacy_file_list_paginates_and_local_has_dedicated_server_paging(self):
        self.assertIn("OfficialDocumentFiles(string officialDocumentGuid, int? pageNo, int? pageSize)", self.old_file_controller)
        self.assertIn("result.PageSize = pageSize > 0 ? pageSize.Value : 15", self.old_file_controller)
        self.assertIn(".Skip(result.PageSize * (result.PageNo - 1))", self.old_file_controller)
        self.assertIn(".Take(result.PageSize)", self.old_file_controller)
        assert_matches(self, self.local, r"async def list_seal_(application_)?files", "app/main.py")
        files_source = function_span(self.local, "list_seal_application_files")
        for token in (
            "page: int = Query(1",
            "page_size: int = Query(15",
            "select(func.count()).select_from(FileAttachment)",
            ".offset((page - 1) * page_size).limit(page_size)",
            '"pages"',
        ):
            assert_contains(self, files_source, token, "list_seal_application_files")


if __name__ == "__main__":
    unittest.main()

"""Executable source contract design for seal backend batch parity.

No HTTP session, fixture, database write, or file upload is performed.  The
three expected-failure tests are deliberate parity gates for the main-thread
owner: they become green only after the serialized main.py work is complete.
"""

from pathlib import Path
import re
import unittest


HERE = Path(__file__).resolve().parent
LOCAL_MAIN = HERE / "app" / "main.py"
OLD_ROOT = HERE.parent.parent.parent / "旧系统归档源码" / "SH.CRM.WEB"
OLD_CONTROLLER = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentController.cs"
OLD_FILE = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentFileController.cs"
OLD_JS = OLD_ROOT / "Scripts" / "AWS" / "OfficialDocument" / "AWS.OfficialDocument.js"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


class SealBackendBatchContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local = text(LOCAL_MAIN)
        cls.old_controller = text(OLD_CONTROLLER)
        cls.old_file = text(OLD_FILE)
        cls.old_js = text(OLD_JS)

    def test_legacy_file_batch_delete_and_pagination_contract(self):
        self.assertIn("Delete(List<long> fileIds)", self.old_file)
        self.assertIn("result.PageSize = pageSize > 0 ? pageSize.Value : 15", self.old_file)
        self.assertIn("result.TotalItemCount = officialDocumentFiles.Count", self.old_file)
        self.assertIn(".Skip(result.PageSize * (result.PageNo - 1))", self.old_file)
        self.assertIn(".Take(result.PageSize)", self.old_file)
        self.assertIn("OrderBy(x => x.FileId)", self.old_file)

    def test_legacy_multi_number_stamp_upload_partial_failure_contract(self):
        stamp = self.old_controller[self.old_controller.index("StampFileUpload"):]
        self.assertIn("officialDocumentNos.Split(',').ToList().ForEach", stamp)
        self.assertIn("OfficialDocumentFileService.Instance.CreateUpdate", stamp)
        self.assertIn("OfficialDocumentService.Instance.Print", stamp)
        self.assertIn("response.Message = \"用印失败.\"", stamp)

    def test_legacy_js_selection_and_empty_selection_messages(self):
        self.assertIn("$.checkbox.vals(\"chkOfficialDocumentId\")", self.old_js)
        self.assertIn("请选择用印文件.", self.old_js)
        self.assertIn("请选择需要撤回的用印申请.", self.old_js)
        self.assertIn("/AWS/OfficialDocumentFile/Delete", self.old_js)

    def test_local_single_delete_is_transactional_and_audited(self):
        delete_start = self.local.index("async def delete_attachment")
        delete_end = self.local.index("@app.post", delete_start)
        delete_source = self.local[delete_start:delete_end]
        self.assertIn("record.module == \"seal\"", delete_source)
        self.assertIn("status_code=409", delete_source)
        self.assertIn("db.delete(item)", delete_source)
        self.assertIn("WorkflowEvent(record_id=record.id", delete_source)
        self.assertIn("await db.commit()", delete_source)
        self.assertIn("path.unlink()", delete_source)

    def test_local_stamp_updates_status_asset_and_audit_atomically(self):
        stamp_start = self.local.index("async def stamp_seal_application")
        stamp_end = self.local.index("@app.post", stamp_start + 10)
        stamp_source = self.local[stamp_start:stamp_end]
        for token in ("status_code=403", "status_code=409", "item.status =", "asset.usage_count +=", "WorkflowEvent(record_id=item.id", "await db.commit()"):
            self.assertIn(token, stamp_source)

    def test_local_package_download_is_read_only_and_has_404_path(self):
        start = self.local.index("async def package_download_seal_files")
        end = self.local.index("@app.post", start + 10)
        source = self.local[start:end]
        self.assertIn("application_ids", source)
        self.assertIn("status_code=404", source)
        self.assertIn("StreamingResponse", source)
        self.assertNotIn("db.delete", source)

    def test_local_batch_delete_has_permission_status_transaction_and_file_compensation(self):
        start = self.local.index("async def batch_delete_seal_attachments")
        end = self.local.index("@app.post", start + 10)
        source = self.local[start:end]
        for token in ("status_code=404", "status_code=409", "status_code=422", "staged", "path.replace", "await db.rollback()", "await db.commit()", "WorkflowEvent", "unlink"):
            self.assertIn(token, source)

    def test_local_batch_stamp_and_withdraw_prevalidate_then_commit_once(self):
        stamp_start = self.local.index("async def batch_stamp_seal_applications")
        stamp_end = self.local.index("@app.post", stamp_start + 10)
        withdraw_start = self.local.index("async def batch_withdraw_seal_applications")
        withdraw_end = self.local.index("@app.post", withdraw_start + 10)
        stamp = self.local[stamp_start:stamp_end]
        withdraw = self.local[withdraw_start:withdraw_end]
        for token in ("status_code=403", "status_code=404", "status_code=409", "SealAssetAudit", "WorkflowEvent", "await db.rollback()", "await db.commit()"):
            self.assertIn(token, stamp)
        for token in ("status_code=403", "status_code=404", "status_code=409", "WorkflowEvent", "await db.rollback()", "await db.commit()"):
            self.assertIn(token, withdraw)

    def test_gate_default_seal_page_size_is_fifteen(self):
        """Main-thread gate: old list/file defaults are 15."""
        declaration = re.search(r"async def list_seal_applications\([^\n]+", self.local)
        self.assertIsNotNone(declaration)
        self.assertIn("page_size: int = Query(15", declaration.group(0))

    def test_gate_seal_batch_attachment_delete_endpoint_exists(self):
        """Main-thread gate: legacy Delete accepts multiple file IDs."""
        self.assertRegex(self.local, r"seals/applications/[^\n]+files/delete")

    def test_gate_multi_number_stamp_endpoint_exists(self):
        """Main-thread gate: legacy Print/StampFileUpload accepts many numbers."""
        self.assertRegex(self.local, r"seals/applications/(batch|package)-stamp|stamp.*application_ids")


if __name__ == "__main__":
    unittest.main()

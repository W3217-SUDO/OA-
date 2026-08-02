"""Static full-stack contract checks for the seal/official-document alignment.

This test intentionally performs no login, HTTP call, database write, or fixture
creation.  It protects the source-level mapping while the shared main.py remains
owned by another task.
"""

from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parent
APP = REPO / "app"
LOCAL_MAIN = APP / "main.py"
LOCAL_MODELS = APP / "models.py"
OLD_ROOT = REPO.parent.parent.parent / "旧系统归档源码" / "SH.CRM.WEB"
OLD_FILE_CONTROLLER = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentFileController.cs"
OLD_CONTROLLER = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentController.cs"
OLD_AUDIT_CONTROLLER = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentAuditController.cs"
OLD_FILE_SCRIPT = OLD_ROOT / "Scripts" / "AWS" / "OfficialDocument" / "AWS.OfficialDocument.js"
OLD_OFFICIAL_MODEL = OLD_ROOT / "Areas" / "AWS" / "ViewModels" / "OfficialDocument" / "OfficialDocumentModel.cs"
OLD_FILE_MODEL = OLD_ROOT / "Areas" / "AWS" / "ViewModels" / "OfficialDocumentFile" / "FileListModel.cs"
OLD_AUDIT_MODEL = OLD_ROOT / "Areas" / "AWS" / "ViewModels" / "OfficialDocumentAudit" / "AuditModel.cs"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


class SealBackendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_main = read(LOCAL_MAIN)
        cls.local_models = read(LOCAL_MODELS)
        cls.old_file = read(OLD_FILE_CONTROLLER)
        cls.old_controller = read(OLD_CONTROLLER)
        cls.old_audit = read(OLD_AUDIT_CONTROLLER)
        cls.old_script = read(OLD_FILE_SCRIPT)
        cls.old_official_model = read(OLD_OFFICIAL_MODEL)
        cls.old_file_model = read(OLD_FILE_MODEL)
        cls.old_audit_model = read(OLD_AUDIT_MODEL)

    def test_old_controller_service_and_dto_contract_is_present(self):
        self.assertIn("OfficialDocumentFileService.Instance", self.old_file)
        self.assertIn("OfficialDocumentService.Instance", self.old_controller)
        self.assertIn("OfficialDocumentAuditService.Instance", self.old_audit)
        self.assertIn("BizOfficialDocument", self.old_official_model)
        self.assertIn("BizOfficialDocumentFile", self.old_file_model)
        self.assertIn("BizOfficialDocumentAudit", self.old_audit_model)

    def test_old_file_permissions_paging_upload_download_delete(self):
        self.assertIn("[CheckUserLogin]", self.old_file)
        self.assertIn("OfficialDocumentFiles(string officialDocumentGuid, int? pageNo, int? pageSize)", self.old_file)
        self.assertIn("result.PageSize = pageSize > 0 ? pageSize.Value : 15", self.old_file)
        self.assertIn("Request.Files", self.old_file)
        self.assertIn("OfficialDocumentFileDownload(long officialDocumentFileId)", self.old_file)
        self.assertIn("Delete(List<long> fileIds)", self.old_file)

    def test_old_workflow_audit_and_failure_contract(self):
        for symbol in ("Print(List<string>", "Download(List<string>", "StampFileUpload(string", "AuditList(string"):
            self.assertIn(symbol, self.old_controller + self.old_audit)
        for symbol in ("PendingList", "ApprovedList", "RejectedList", "Approved", "Rejected"):
            self.assertIn(symbol, self.old_audit)
        self.assertIn("用印失败", self.old_controller)
        self.assertIn("请选择用印文件", self.old_script)

    def test_local_seal_dtos_and_routes_cover_the_flow(self):
        for symbol in (
            "class SealApplicationInput",
            "class SealPackageDownloadInput",
            "class SealApprovalInput",
            "class SealStampInput",
            "async def list_seal_applications",
            "async def create_seal_application",
            "async def submit_seal_application",
            "async def withdraw_seal_application",
            "async def approve_seal_application",
            "async def stamp_seal_application",
            "async def archive_seal_application",
            "async def package_download_seal_files",
        ):
            self.assertIn(symbol, self.local_main)

    def test_local_attachment_preview_download_delete_permissions(self):
        for symbol in (
            "async def upload_attachment",
            "async def download_attachment",
            "async def preview_attachment",
            "async def delete_attachment",
            "record.module == \"seal\"",
            "status_code=409",
            "status_code=404",
        ):
            self.assertIn(symbol, self.local_main)
        self.assertIn("_require_record_owner_or_manager(record, identity, db)", self.local_main)
        self.assertIn("WorkflowEvent(record_id=record.id", self.local_main)

    def test_local_database_model_and_audit_projection(self):
        for symbol in (
            "class BusinessRecord",
            "class WorkflowEvent",
            "class FileAttachment",
            "class SealAsset",
            "class SealAssetAudit",
            "__tablename__ = \"business_records\"",
            "__tablename__ = \"workflow_events\"",
            "__tablename__ = \"file_attachments\"",
            "__tablename__ = \"seal_assets\"",
            "__tablename__ = \"seal_asset_audits\"",
        ):
            self.assertIn(symbol, self.local_models)
        self.assertIn("db.add(WorkflowEvent", self.local_main)
        self.assertIn("await db.commit()", self.local_main)

    def test_local_status_and_error_matrix_is_explicit(self):
        for status in ("草稿", "待审批", "待用印", "已拒绝", "已撤回", "已用印", "已归档"):
            self.assertIn(status, self.local_main)
        for code in ("status_code=403", "status_code=404", "status_code=409"):
            self.assertIn(code, self.local_main)

    def test_local_menu_permission_and_scope_guards(self):
        self.assertIn('("seal", "", "用印中心"', self.local_main)
        self.assertIn('"seal": ("seal",)', self.local_main)
        self.assertIn('if view == "all" and identity.get("role") not in {"admin", "manager"}', self.local_main)
        self.assertIn("Depends(current_identity)", self.local_main)

    def test_external_old_service_source_is_a_known_audit_debt(self):
        # The archived web repository references Dchien.Legal.Service/BizModel
        # assemblies but does not carry their source files. Keep this explicit so
        # a passing static check cannot be mistaken for service-level equivalence.
        service_sources = list(OLD_ROOT.rglob("*OfficialDocumentService*.cs"))
        self.assertEqual(service_sources, [], "old service source unexpectedly appeared; expand the audit")


if __name__ == "__main__":
    unittest.main()

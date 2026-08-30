from pathlib import Path
import unittest


SOURCE = (Path(__file__).parent / "app" / "main.py").read_text(encoding="utf-8")
ROUTES = SOURCE.replace("{{", "{").replace("}}", "}")


class CaseAiSpaceContractTest(unittest.TestCase):
    def test_ai_space_is_a_reserved_virtual_folder(self):
        self.assertIn('AI_SPACE_CATEGORY = "AI空间"', SOURCE)
        self.assertIn('CASE_DOCUMENT_FOLDER_HEADERS = {"AI空间"', SOURCE)
        self.assertIn("FileAttachment.category != AI_SPACE_CATEGORY", SOURCE)

    def test_draft_lifecycle_endpoints_are_present(self):
        for route in (
            '/cases/{case_id}/ai-space',
            '/cases/{case_id}/ai-space/files',
            '/cases/{case_id}/ai-space/files/{attachment_id}/content',
            '/cases/{case_id}/ai-space/files/{attachment_id}/promote',
        ):
            self.assertIn(route, ROUTES)

    def test_ai_drafts_require_case_permissions_and_audit_promotion(self):
        self.assertIn("await _require_case_attachment_upload_access(record, identity, db)", SOURCE)
        self.assertIn("await _require_case_detail_write_access(record, identity, db)", SOURCE)
        self.assertIn('action="AI 草稿转入正式系统"', SOURCE)
        self.assertIn("_validate_case_formal_document_category", SOURCE)

    def test_ai_space_creates_and_edits_word_documents(self):
        self.assertIn('AI_SPACE_EDITABLE_SUFFIXES = {".docx", ".md", ".txt"}', SOURCE)
        self.assertIn('return _docx_bytes(Path(name).stem, content), WORD_DOCUMENT_CONTENT_TYPE', SOURCE)
        self.assertIn('document = Document(path)', SOURCE)
        self.assertIn('name = f"{safe_title}.docx"', SOURCE)
        self.assertIn('content = _docx_bytes(item.title, item.content)', SOURCE)

    def test_regular_upload_can_target_ai_space(self):
        self.assertIn("*CASE_FORMAL_DOCUMENT_FOLDERS", SOURCE)
        self.assertIn("target in CASE_FORMAL_DOCUMENT_FOLDERS", SOURCE)
        self.assertIn('@app.get(f"{settings.api_prefix}/cases/{{case_id}}/document-folders")', SOURCE)
        self.assertIn("*_case_custom_document_folders(record)", SOURCE)
        self.assertIn('"label": "客户文档", "value": "客户文档"', SOURCE)
        self.assertIn('"label": "合同文档", "value": "合同文档"', SOURCE)
        self.assertIn('"label": "调查文档", "value": "调查文档全部"', SOURCE)
        self.assertIn('"label": "案件文档", "value": "案件文档全部"', SOURCE)
        self.assertIn("item.record_id = destination_record.id", SOURCE)


if __name__ == "__main__":
    unittest.main()

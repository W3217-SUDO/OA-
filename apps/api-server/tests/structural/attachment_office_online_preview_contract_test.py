import unittest
from pathlib import Path


SYSTEM_AREA = Path(__file__).resolve().parents[2] / "app" / "areas" / "system"
ROUTER = SYSTEM_AREA / "router.py"
ATTACHMENTS = SYSTEM_AREA / "attachments.py"


class AttachmentOfficeOnlinePreviewContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ATTACHMENTS.read_text(encoding="utf-8")
        cls.router_source = ROUTER.read_text(encoding="utf-8")

    def test_authenticated_endpoint_issues_short_lived_office_token(self):
        self.assertIn("async def create_office_preview_link(", self.source)
        self.assertIn('"purpose": "office-online-preview"', self.source)
        self.assertIn("timedelta(minutes=10)", self.source)
        self.assertIn("await case_attachment_parent(case_id, item.record_id, identity, db)", self.source)
        self.assertIn("await ensure_investigation_material_access(item.record_id, identity, db)", self.source)
        self.assertIn("await _ensure_attachment_record_visible(item.record_id, identity, db, allow_clue_audit_read=True)", self.source)
        self.assertIn("settings.office_preview_public_base_url.strip().rstrip", self.source)
        self.assertIn('public_file_name = f"attachment-{item.id}{suffix}"', self.source)
        self.assertIn("office-preview/{token}/{public_file_name}", self.source)
        self.assertIn('"source_url": f"{public_base}{source_path}" if public_base else source_path', self.source)

    def test_public_endpoint_validates_token_and_streams_original_file_inline(self):
        self.assertIn("async def stream_office_preview_attachment(", self.source)
        self.assertIn("token: str, file_name: str", self.source)
        self.assertIn('jwt.decode(token, settings.secret_key, algorithms=["HS256"])', self.source)
        self.assertIn('payload.get("purpose") != "office-online-preview"', self.source)
        self.assertIn('file_name != f"attachment-{item.id}{suffix}"', self.source)
        self.assertIn('content_disposition_type="inline"', self.source)
        self.assertIn('"Cache-Control": "private, max-age=600"', self.source)

    def test_main_composes_every_system_route_after_new_endpoints(self):
        from app.main import app
        from app.areas.system.attachments import create_office_preview_link, stream_office_preview_attachment

        self.assertIn("from app.areas.system.attachments import (", self.router_source)
        self.assertIn("router.include_router(attachments_router)", self.router_source)
        routes = {(route.path, method): route.endpoint for route in app.routes for method in getattr(route, "methods", ())}
        self.assertIs(routes[("/api/v1/attachments/{attachment_id}/office-preview", "GET")], create_office_preview_link)
        self.assertIs(routes[("/api/v1/public/attachments/office-preview/{token}/{file_name}", "GET")], stream_office_preview_attachment)


if __name__ == "__main__":
    unittest.main()

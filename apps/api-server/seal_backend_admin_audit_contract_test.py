"""Static source contracts for seal rollback, admin-use, asset and audit parity.

This is deliberately a no-fixture/no-HTTP contract test.  Expected failures are
parity gates for the serialized ``main.py`` owner; they document concrete
backend work without changing the shared business implementation here.
"""

from pathlib import Path
import re
import unittest


HERE = Path(__file__).resolve().parent
LOCAL_MAIN = HERE / "app" / "main.py"
OLD_ROOT = HERE.parent.parent.parent / "旧系统归档源码" / "SH.CRM.WEB"
OLD_DOC = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentController.cs"
OLD_AUDIT = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentAuditController.cs"
OLD_AUDIT_VIEW = OLD_ROOT / "Areas" / "AWS" / "Views" / "OfficialDocumentAudit" / "PartialView" / "AuditList.cshtml"
OLD_CREATE_VIEW = OLD_ROOT / "Areas" / "AWS" / "Views" / "OfficialDocument" / "PartialView" / "Create.cshtml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


class SealBackendAdminAuditContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local = read(LOCAL_MAIN)
        cls.old_doc = read(OLD_DOC)
        cls.old_audit = read(OLD_AUDIT)
        cls.old_audit_view = read(OLD_AUDIT_VIEW)
        cls.old_create = read(OLD_CREATE_VIEW)

    def _span(self, function_name: str, next_marker: str = "@app.") -> str:
        start = self.local.index(f"async def {function_name}")
        end = self.local.find(next_marker, start + 10)
        return self.local[start:] if end < 0 else self.local[start:end]

    def test_legacy_rollback_is_authenticated_batch_and_has_contract_message(self):
        self.assertIn("[CheckUserLogin]", self.old_doc)
        self.assertIn("Rollback(List<string> officialDocumentNos)", self.old_doc)
        self.assertIn("OfficialDocumentService.Instance.Rollback(officialDocumentNos)", self.old_doc)
        self.assertIn("用印撤回成功", self.old_doc)

    def test_legacy_audit_controller_has_three_queues_and_history_action(self):
        for name in ("PendingList", "ApprovedList", "RejectedList", "AuditList", "Approved", "Rejected"):
            self.assertIn(name, self.old_audit)
        self.assertIn("[CheckUserLogin]", self.old_audit)
        self.assertIn("BizModel.AWS.OfficialDocument.BizOfficialDocumentAudit", self.old_audit)
        self.assertIn("AuditStatus.A", self.old_audit)
        self.assertIn("AuditStatus.R", self.old_audit)

    def test_legacy_audit_list_response_fields_and_round_are_explicit(self):
        for field in ("AuditorName", "AuditStatusName", "AuditDate", "AuditContent", "AuditRoundId"):
            self.assertIn(field, self.old_audit_view)

    def test_legacy_admin_use_and_seal_type_payload_contract(self):
        self.assertRegex(self.old_create, r'name="OfficialDocument_Basic_OfficialDocumentType"[^>]+value="30"')
        self.assertIn("行政用印", self.old_create)
        self.assertIn('name="OfficialDocument_Basic_IsElectronicSeal"', self.old_create)
        values = set(re.findall(r'name="OfficialDocument_Basic_SealType"[^>]+value="(\d+)"', self.old_create))
        self.assertTrue({"1", "2", "4", "8", "16", "32", "64"}.issubset(values))

    def test_local_withdraw_has_owner_admin_state_gate_and_workflow_event(self):
        source = self._span("withdraw_seal_application")
        for token in ("identity.get(\"role\") != \"admin\"", "item.owner", "status not in", "已撤回", "WorkflowEvent", "await db.commit()"):
            self.assertIn(token, source)

    def test_local_approve_has_role_state_data_and_workflow_audit(self):
        source = self._span("approve_seal_application")
        for token in ("_get_seal_application_for_action", '"approve" if body.approved else "reject"', "status", "approved", "approver", "approved_at", "approval_comment", "WorkflowEvent", "await db.commit()"):
            self.assertIn(token, source)

    def test_local_asset_mutation_permissions_validation_and_delete_audit(self):
        for function_name, tokens in {
            "create_seal_asset": ('_require_seal_base_action(identity, db, "manage_assets")', "REQUIRED_SEAL_TYPES", "status_code=409", "await db.commit()"),
            "update_seal_asset": ('_require_seal_base_action(identity, db, "manage_assets")', "status", "seal_type", "await db.commit()"),
            "delete_seal_asset": ('_require_seal_base_action(identity, db, "manage_assets")', "status_code=404", "status_code=409", "SealAssetAudit", "await db.commit()"),
        }.items():
            source = self._span(function_name)
            for token in tokens:
                self.assertIn(token, source)

    def test_local_stamp_updates_asset_usage_and_workflow_event(self):
        source = self._span("stamp_seal_application")
        for token in ('_require_seal_base_action(identity, db, "stamp")', "待用印", "actual_copies", "asset.status", "usage_count", "last_used_at", "WorkflowEvent", "await db.commit()"):
            self.assertIn(token, source)

    def test_gate_batch_rollback_endpoint_accepts_multiple_record_ids(self):
        """Old Rollback accepts List<string>; local withdraw is single-record only."""
        self.assertRegex(self.local, r"seals/applications/(batch|bulk).*(withdraw|rollback)|withdraw.*application_ids")

    def test_gate_use_type_is_enum_validated_server_side(self):
        """Old type 30 is a closed admin-use choice; free text must not reach DB."""
        source = self._span("_validated_seal_relations", "@app.get")
        self.assertIn("if use_type not in SEAL_USE_TYPES", source)
        self.assertIn("SEAL_USE_TYPES", self.local)

    def test_gate_seal_type_bitmask_or_multi_asset_relation_is_preserved(self):
        """Old DTO carries seven bit values; local input stores one asset id/type."""
        dto = self.local[self.local.index("class SealApplicationInput"):self.local.index("class SealPackageDownloadInput")]
        self.assertRegex(dto, r"seal_types?\s*:")

    def test_gate_rejection_comment_is_required_by_backend(self):
        """The UI requires a rejection reason; API must enforce the same 422 contract."""
        source = self._span("approve_seal_application", "@app.post")
        self.assertRegex(source, r"not\s+body\.approved.*comment|approved.*comment.*strip")

    @unittest.expectedFailure
    def test_gate_audit_response_has_status_date_and_persisted_round_fields(self):
        """Legacy AuditList exposes status/date/content/round, not generic transitions only."""
        source = self._span("record_history", "@app.patch")
        self.assertIn("audit_status", source)
        self.assertIn("audit_round", source)

    @unittest.expectedFailure
    def test_gate_history_endpoint_can_return_audit_only_rows(self):
        """UI filtering action text cannot replace a server-side audit scope."""
        source = self._span("record_history", "@app.patch")
        self.assertRegex(source, r"audit_only|audit_status|action_filter")

    def test_gate_asset_update_and_stamp_write_asset_audit_rows(self):
        """Create/update/stamp lifecycle changes need the same asset audit trail as delete."""
        update = self._span("update_seal_asset")
        stamp = self._span("stamp_seal_application")
        self.assertIn("SealAssetAudit", update)
        self.assertIn("SealAssetAudit", stamp)

    def test_gate_admin_queue_permission_matches_stamp_roles(self):
        """Managers allowed to stamp must also be able to read the administrative queue."""
        source = self._span("list_seal_applications", "@app.post")
        self.assertNotRegex(source, r'view == "all" and identity\.get\("role"\) != "admin"')

    @unittest.expectedFailure
    def test_gate_state_actions_use_row_lock_or_idempotency_guard(self):
        """Approval/withdraw/stamp must make concurrent double actions deterministic."""
        combined = "\n".join(self._span(name, "@app.post") for name in (
            "withdraw_seal_application", "approve_seal_application", "stamp_seal_application"))
        self.assertRegex(combined, r"with_for_update|idempotency")


if __name__ == "__main__":
    unittest.main()

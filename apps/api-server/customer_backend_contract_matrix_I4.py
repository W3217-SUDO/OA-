"""Read-only full-stack customer contract audit.

This audit intentionally does not import the running application or create
database rows.  It compares the legacy controller/view-model contracts with
the local FastAPI/SQLAlchemy source and keeps unresolved backend gaps explicit
until the shared ``main.py`` ownership is released.
"""

from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[2]
OLD = REPO.parent / "旧系统归档源码" / "SH.CRM.WEB"
MAIN = REPO / "apps" / "api-server" / "app" / "main.py"
MODELS = REPO / "apps" / "api-server" / "app" / "models.py"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


OLD_CONTROLLER = source(OLD / "Areas" / "CRM" / "Controllers" / "CustomerController.cs")
OLD_ASSIGNMENT = source(OLD / "Areas" / "CRM" / "Controllers" / "CustomerAssignmentController.cs")
OLD_SHARE = source(OLD / "Areas" / "CRM" / "Controllers" / "CustomerShareController.cs")
OLD_CONTACTS = source(OLD / "Areas" / "CRM" / "Controllers" / "CustomerContactsController .cs")
OLD_FILES = source(OLD / "Areas" / "CRM" / "Controllers" / "CustomerFileController.cs")
LOCAL_MAIN = source(MAIN)
LOCAL_MODELS = source(MODELS)


# These are deliberately reported, not hidden by a passing frontend suite.
# They require a serial backend decision because the shared main.py is owned by
# another task in the current worktree.
KNOWN_BACKEND_GAPS = (
    "legacy List monetary summary projection (14 fields) vs local summary (2 fields)",
    "legacy CustomerList/AllCustomerList search endpoints have no exact local route",
    "legacy CustomerSharedObjects read endpoint has no dedicated local route",
    "legacy contact SetDefatultContacts/SetActivedContacts endpoints have no exact local route",
    "legacy customerGuid-based CustomerFiles/CustomerFileDownloadByGuid contract is represented only by generic record_id attachments",
    "legacy CustomerEvents/CustomerEventCreate contract has no customer-specific local route",
    "legacy PostResponse 200/IsSuccess failure envelope differs from local HTTP error status/detail contract",
    "customer PATCH /records/{record_id} returns unfiltered _record_dict instead of the field-filtered identity projection",
)


class CustomerBackendContractMatrixI4(unittest.TestCase):
    def test_legacy_controller_service_and_dto_contract_is_present(self):
        for action in (
            "CustomerDelete(long customerId)",
            "CustomerRestore(long customerId)",
            "CustomerOpen(long customerId)",
            "CustomerClose(long customerId)",
            "CustomerCreateUpdate(CreateUpdateModel model)",
            "CustomerList(string keyWord)",
            "AllCustomerList(string keyWord)",
        ):
            self.assertIn(action, OLD_CONTROLLER)
        self.assertIn("CustomerService.Instance.DeleteCustomer(customerId)", OLD_CONTROLLER)
        self.assertIn("CustomerService.Instance.RestoreCustomer(customerId)", OLD_CONTROLLER)
        self.assertIn("CustomerService.Instance.OpenCustomer(customerId)", OLD_CONTROLLER)
        self.assertIn("CustomerService.Instance.CloseCustomer(customerId)", OLD_CONTROLLER)
        self.assertIn("CustomerOwnerChange(customerIds, assigningCustomerOwner)", OLD_ASSIGNMENT)
        self.assertIn("CustomerSharing(customerId, sharedObjects)", OLD_SHARE)
        self.assertIn("CustomerSharedObjects(long customerId)", OLD_SHARE)
        self.assertIn("response.IsSuccess", OLD_CONTROLLER)
        self.assertIn("response.Message", OLD_CONTROLLER)
        self.assertIn("response.Data", OLD_SHARE)

    def test_local_customer_route_dto_matrix_is_explicit(self):
        route_functions = (
            "list_customers", "create_customer", "claim_customer", "release_customer",
            "share_customer", "recycle_customer", "restore_customer", "update_customer_managers",
            "add_customer_contact", "update_customer_contact", "delete_customer_contact",
            "upload_customer_contact_photo", "download_customer_contact_photo",
            "list_attachments", "upload_attachment", "download_attachment", "delete_attachment",
        )
        for function_name in route_functions:
            self.assertRegex(LOCAL_MAIN, rf"async def {function_name}\b")
        for route_fragment in (
            "/customers", "/customers/{{customer_id}}/claim", "/customers/{{customer_id}}/release",
            "/customers/{{customer_id}}/share", "/customers/{{customer_id}}/recycle",
            "/customers/{{customer_id}}/restore", "/customers/{{customer_id}}/managers",
            "/customers/{{customer_id}}/contacts", "/attachments", "/attachments/{{attachment_id}}/download",
        ):
            self.assertIn(route_fragment, LOCAL_MAIN)
        for dto, fields in {
            "CustomerActionInput": ("comment",),
            "CustomerShareInput": ("recipients", "comment"),
            "CustomerManagersInput": ("managers", "comment"),
            "CustomerContactInput": ("name", "phone", "is_primary", "is_valid"),
        }.items():
            block = LOCAL_MAIN[LOCAL_MAIN.index(f"class {dto}"):]
            block = block[: block.find("\n\nclass ") if "\n\nclass " in block else len(block)]
            for field in fields:
                self.assertRegex(block, rf"\b{field}\b")

    def test_local_models_and_mutations_have_state_audit_and_transaction_hooks(self):
        for field in ("module", "serial_no", "title", "customer", "status", "owner", "department", "data"):
            self.assertRegex(LOCAL_MODELS, rf"\b{field}: Mapped")
        for field in ("record_id", "action", "from_status", "to_status", "operator", "comment"):
            self.assertRegex(LOCAL_MODELS, rf"\b{field}: Mapped")
        for field in ("record_id", "original_name", "stored_name", "content_type", "size", "path", "uploader"):
            self.assertRegex(LOCAL_MODELS, rf"\b{field}: Mapped")
        for function_name in ("claim_customer", "release_customer", "share_customer", "recycle_customer", "restore_customer"):
            block = LOCAL_MAIN[LOCAL_MAIN.index(f"async def {function_name}"):]
            block = block[: block.find("\n\n@app.") if "\n\n@app." in block else len(block)]
            self.assertIn("_customer_event", block)
            self.assertIn("await db.commit()", block)
            self.assertIn("await db.refresh", block)
        self.assertIn("@app.get(f\"{settings.api_prefix}/audit/events\")", LOCAL_MAIN)

    def test_permission_and_failure_boundaries_are_visible(self):
        for legacy in (OLD_CONTROLLER, OLD_ASSIGNMENT, OLD_SHARE, OLD_CONTACTS, OLD_FILES):
            self.assertIn("CheckUserLogin", legacy)
        for helper in ("_customer_or_404", "_locked_customer_or_404", "_require_record_owner_or_manager", "current_identity"):
            self.assertIn(helper, LOCAL_MAIN)
        self.assertIn("HTTPException(status_code=403", LOCAL_MAIN)
        self.assertIn("HTTPException(status_code=404", LOCAL_MAIN)
        self.assertIn("HTTPException(status_code=409", LOCAL_MAIN)
        self.assertIn("HTTPException(status_code=422", LOCAL_MAIN)

    def test_unresolved_backend_gaps_remain_explicit(self):
        self.assertGreaterEqual(len(KNOWN_BACKEND_GAPS), 5)
        self.assertTrue(all(isinstance(item, str) and item for item in KNOWN_BACKEND_GAPS))

    def test_known_gap_markers_are_present_in_current_backend(self):
        self.assertNotIn("CustomerSharedObjects", LOCAL_MAIN)
        self.assertNotIn("CustomerEvents", LOCAL_MAIN)
        update_start = LOCAL_MAIN.index("async def update_record")
        update_block = LOCAL_MAIN[update_start:update_start + 9000]
        self.assertIn("return _record_dict(record)", update_block)
        self.assertIn('"agency_fee_due"', LOCAL_MAIN)
        self.assertIn('"official_fee_unreceived"', LOCAL_MAIN)
        self.assertNotIn('"total_paid_case_office_fee_amount"', LOCAL_MAIN)


if __name__ == "__main__":
    unittest.main()

"""Static backend audit for the first three Case parity batches.

This is intentionally a source contract rather than a live API test: it does
not log in, create records, mutate the database, or require a running server.
It keeps frontend parity tests from being mistaken for proof that the local
FastAPI, DTO, persistence, permission, and audit paths exist.
"""
import ast
import pathlib
import unittest

from app.models import BusinessRecord, SystemParameter, WorkflowEvent
from app.models_shared import BatchClueCaseInput, CaseArbitrationBasicInput, CaseCreateInput, CaseNormalBasicInput


APP_ROOT = pathlib.Path(__file__).resolve().parents[2] / "app"
API_FILES = (
    APP_ROOT / "api_schemas" / "cases.py",
    APP_ROOT / "api_schemas" / "investigation.py",
    APP_ROOT / "core" / "cases.py",
    APP_ROOT / "core" / "constants.py",
    APP_ROOT / "areas" / "legal" / "router.py",
    APP_ROOT / "areas" / "investigation" / "router.py",
)
API_SOURCE = "\n".join(path.read_text(encoding="utf-8") for path in API_FILES)
MODEL_SOURCE = (APP_ROOT / "models.py").read_text(encoding="utf-8")


class CasePreviousBatchesBackendAuditTest(unittest.TestCase):
    def test_create_and_type_specific_edit_are_backend_mapped(self):
        for dto, fields in (
            (CaseCreateInput, {"contract_record_id", "title", "case_type", "handling_lawyers"}),
            (CaseNormalBasicInput, {"customer_record_id", "case_phase", "cause_or_charge", "handling_lawyers"}),
            (CaseArbitrationBasicInput, {"customer_record_id", "case_phase", "cause_or_charge", "handling_lawyers"}),
        ):
            self.assertTrue(fields.issubset(dto.model_fields), dto.__name__)
        for token in (
            "class CaseCreateInput(BaseModel):",
            "@router.post(f\"{settings.api_prefix}/cases\"",
            "async def create_case(",
            "contract_record_id",
            "CASE_CREATE_PERMISSION_BY_TYPE",
            "contract = await _ensure_record_visible(body.contract_record_id, identity, db)",
            "case_creation_step",
            "class CaseNormalBasicInput(BaseModel):",
            "@router.put(f\"{settings.api_prefix}/cases/{{case_id}}/normal-basic\")",
            "class CaseArbitrationBasicInput(BaseModel):",
            "@router.put(f\"{settings.api_prefix}/cases/{{case_id}}/arbitration-basic\")",
            "_resolve_active_case_people",
            "_require_case_creation_completed",
        ):
            self.assertIn(token, API_SOURCE)

    def test_clue_conversion_duplicate_and_merge_have_persistent_paths(self):
        self.assertTrue({"clue_ids", "case_type", "cause_or_charge", "handling_lawyer"}.issubset(BatchClueCaseInput.model_fields))
        for token in (
            "class BatchClueCaseInput(BaseModel):",
            "@router.post(f\"{settings.api_prefix}/investigations/clues/batch-cases\"",
            "async def batch_create_cases_from_clues(",
            "converted_case_id",
            "converted_case_no",
            "async def duplicate_case(",
            "async def merge_case(",
            "class CaseMergeInput(BaseModel):",
            "original_case_no",
            "WorkflowEvent(",
        ):
            self.assertIn(token, API_SOURCE)

    def test_execution_progress_and_phase_write_paths_are_backend_mapped(self):
        for token in (
            "class CaseExecutionStatusInput(BaseModel):",
            "@router.post(f\"{settings.api_prefix}/cases/execution-status\")",
            "class CaseProgressInput(BaseModel):",
            "@router.post(f\"{settings.api_prefix}/cases/{{case_id}}/progress\")",
            "class CasePhaseChangeInput(BaseModel):",
            "@router.get(f\"{settings.api_prefix}/cases/phases\")",
            "@router.post(f\"{settings.api_prefix}/cases/phase-change\")",
            "_require_case_progress_write_access",
            "CASE_PHASE_STATUS_BY_CODE",
            "await db.commit()",
        ):
            self.assertIn(token, API_SOURCE)

    def test_case_models_expose_state_payload_and_audit_storage(self):
        for model, fields in (
            (SystemParameter, {"category", "code", "name", "is_active"}),
            (BusinessRecord, {"module", "serial_no", "status", "data"}),
            (WorkflowEvent, {"record_id", "from_status", "to_status", "operator"}),
        ):
            self.assertTrue(fields.issubset(model.__table__.columns.keys()), model.__name__)

    def test_backend_sources_parse_as_python(self):
        for path in API_FILES:
            ast.parse(path.read_text(encoding="utf-8"))
        ast.parse(MODEL_SOURCE)


if __name__ == "__main__":
    unittest.main()

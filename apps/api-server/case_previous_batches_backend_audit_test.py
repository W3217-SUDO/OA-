"""Static backend audit for the first three Case parity batches.

This is intentionally a source contract rather than a live API test: it does
not log in, create records, mutate the database, or require a running server.
It keeps frontend parity tests from being mistaken for proof that the local
FastAPI, DTO, persistence, permission, and audit paths exist.
"""
import ast
import pathlib
import unittest


API_SOURCE = (pathlib.Path(__file__).with_name("app") / "main.py").read_text(encoding="utf-8")
MODEL_SOURCE = (pathlib.Path(__file__).with_name("app") / "models.py").read_text(encoding="utf-8")


class CasePreviousBatchesBackendAuditTest(unittest.TestCase):
    def test_create_and_type_specific_edit_are_backend_mapped(self):
        for token in (
            "class CaseCreateInput(BaseModel):",
            "@app.post(f\"{settings.api_prefix}/cases\"",
            "async def create_case(",
            "contract_record_id",
            "CASE_CREATE_PERMISSION_BY_TYPE",
            "_ensure_record_visible(body.contract_record_id, identity, db)",
            "case_creation_step",
            "class CaseNormalBasicInput(BaseModel):",
            "@app.put(f\"{settings.api_prefix}/cases/{{case_id}}/normal-basic\")",
            "class CaseArbitrationBasicInput(BaseModel):",
            "@app.put(f\"{settings.api_prefix}/cases/{{case_id}}/arbitration-basic\")",
            "_resolve_active_case_people",
            "_require_case_creation_completed",
        ):
            self.assertIn(token, API_SOURCE)

    def test_clue_conversion_duplicate_and_merge_have_persistent_paths(self):
        for token in (
            "class BatchClueCaseInput(BaseModel):",
            "@app.post(f\"{settings.api_prefix}/investigations/clues/batch-cases\"",
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
            "@app.post(f\"{settings.api_prefix}/cases/execution-status\")",
            "class CaseProgressInput(BaseModel):",
            "@app.post(f\"{settings.api_prefix}/cases/{{case_id}}/progress\")",
            "class CasePhaseChangeInput(BaseModel):",
            "@app.get(f\"{settings.api_prefix}/cases/phases\")",
            "@app.post(f\"{settings.api_prefix}/cases/phase-change\")",
            "_require_case_progress_write_access",
            "CASE_PHASE_STATUS_BY_CODE",
            "await db.commit()",
        ):
            self.assertIn(token, API_SOURCE)

    def test_case_models_expose_state_payload_and_audit_storage(self):
        for token in (
            "class SystemParameter(Base):",
            "category: Mapped[str]",
            "code: Mapped[str]",
            "name: Mapped[str]",
            "is_active: Mapped[bool]",
            "class BusinessRecord(Base):",
            "module: Mapped[str]",
            "serial_no: Mapped[str]",
            "status: Mapped[str]",
            "data: Mapped[dict]",
            "class WorkflowEvent(Base):",
            "record_id: Mapped[int]",
            "from_status: Mapped[str]",
            "to_status: Mapped[str]",
            "operator: Mapped[str]",
        ):
            self.assertIn(token, MODEL_SOURCE)

    def test_backend_sources_parse_as_python(self):
        ast.parse(API_SOURCE)
        ast.parse(MODEL_SOURCE)


if __name__ == "__main__":
    unittest.main()

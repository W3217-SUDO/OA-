import unittest
import inspect
from pathlib import Path
from sqlalchemy import BigInteger, Numeric
from app import main as app_main
from app.core.investigation import _register_clue_collection
from app.models import LegacyCase, LegacyContract, LegacyCustomer, LegacyInvestigation


class LegacyProjectionSyncContractTest(unittest.TestCase):
    def setUp(self):
        self.main = "\n".join(Path(name).read_text(encoding="utf-8") for name in (
            "app/core/legacy_sync.py", "app/core/constants.py",
        ))

    def test_legacy_identifier_and_money_types_preserve_sql_server_ranges(self):
        for model, field in (
            (LegacyCustomer, "CustomerId"),
            (LegacyContract, "ContractId"),
            (LegacyInvestigation, "InvestigationId"),
        ):
            column = model.__table__.c[field]
            self.assertIsInstance(column.type, BigInteger)
            self.assertTrue(column.primary_key)
        for model, field in (
            (LegacyContract, "ContractMoney"),
            (LegacyContract, "TaxRate"),
            (LegacyCustomer, "PrePaidAmount"),
        ):
            column = model.__table__.c[field]
            self.assertIsInstance(column.type, Numeric)
            self.assertEqual((column.type.precision, column.type.scale), (18, 2))
            self.assertTrue(column.nullable)
        self.assertEqual(LegacyCase.__table__.name, "Legal_Case")

    def test_legacy_timestamp_projection_removes_timezone(self):
        self.assertIn("return value.replace(tzinfo=None) if value.tzinfo else value", self.main)
        self.assertIn("return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed", self.main)

    def test_sqlite_uses_stable_negative_projection_ids_for_bigint_keys(self):
        self.assertIn('async def _legacy_projection_pk(', self.main)
        self.assertIn('return {column: -record.id} if connection.dialect.name == "sqlite" else {}', self.main)
        self.assertIn('**await _legacy_projection_pk(record, "ClueId", db)', self.main)
        self.assertIn('**await _legacy_projection_pk(record, "CaseId", db)', self.main)

    def test_status_mappings_cover_contract_and_investigation_lifecycles(self):
        for marker in (
            "LEGACY_CONTRACT_STATUS_BY_NEW = {",
            '"审批中": 10',
            'CONTRACT_APPROVED_STATUS: 20',
            "LEGACY_INVESTIGATION_STATUS = {",
            "LEGACY_INVESTIGATION_TASK_STATUS = {",
            "LEGACY_INVESTIGATION_CLUE_STATUS = {",
        ):
            self.assertIn(marker, self.main)

    def test_all_creation_and_generic_mutation_paths_sync_projection(self):
        for function_name in (
            "create_customer", "create_contract_draft", "register_clue_collection",
            "create_investigation_task", "create_case", "create_record",
            "update_record", "transition_record",
        ):
            source = inspect.getsource(getattr(app_main, function_name))
            if function_name == "register_clue_collection":
                self.assertIn("await _register_clue_collection(", source)
                self.assertIn("await _sync_legacy_projection(", inspect.getsource(_register_clue_collection))
            else:
                self.assertIn("await _sync_legacy_projection(", source)
        collection_source = inspect.getsource(_register_clue_collection)
        self.assertIn("await _sync_legacy_investigation_clue_evidence(", collection_source)

    def test_imported_legacy_soft_links_survive_projection_refresh(self):
        self.assertIn("def _legacy_snapshot_value(data: dict, *keys: str)", self.main)
        for legacy_key in ("CustomerNo", "ContractNo", "InvestigationNo", "InvestigationTaskNo"):
            self.assertIn(f'_legacy_snapshot_value(data, "{legacy_key}"', self.main)
        self.assertIn('data.get("investigation_task_no")', self.main)
        self.assertIn('if source_task and source_task.module == "task":', self.main)
        self.assertNotIn(
            'legacy.InvestigationTaskNo = _legacy_case_text(data.get("source_task_no"), 20)',
            self.main,
        )


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


class LegacyProjectionSyncContractTest(unittest.TestCase):
    def setUp(self):
        self.main = Path("app/main.py").read_text(encoding="utf-8")
        self.models = Path("app/models.py").read_text(encoding="utf-8")

    def test_legacy_identifier_and_money_types_preserve_sql_server_ranges(self):
        for declaration in (
            "CustomerId: Mapped[int] = mapped_column(BigInteger, primary_key=True)",
            "ContractId: Mapped[int] = mapped_column(BigInteger, primary_key=True)",
            "InvestigationId: Mapped[int] = mapped_column(BigInteger, primary_key=True)",
            "ContractMoney: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)",
            "TaxRate: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)",
            "PrePaidAmount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)",
            'Column("CaseId", BigInteger, primary_key=True)',
        ):
            self.assertIn(declaration, self.models)

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
            '"已通过": 20',
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
            start = self.main.index(f"async def {function_name}(")
            end = self.main.find("\n@app.", start + 1)
            self.assertIn("await _sync_legacy_projection(", self.main[start:end])
        collection_start = self.main.index("async def register_clue_collection")
        collection_end = self.main.find("\n@app.", collection_start + 1)
        self.assertIn("await _sync_legacy_investigation_clue_evidence(", self.main[collection_start:collection_end])


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("app") / "main.py"
FRONTEND = Path(__file__).parents[1] / "admin-web" / "src" / "ContractCenterPage.tsx"


class SealContractSourceFilesRow3Test(unittest.TestCase):
    def test_contract_seal_request_accepts_and_copies_real_source_files(self):
        source = SOURCE.read_text(encoding="utf-8")
        dto = source[source.index("class ContractSealApplicationInput"):source.index("class ContractInvestigationInput")]
        self.assertIn("source_attachment_ids: list[int]", dto)
        start = source.index("async def create_contract_seal_application")
        end = source.index("async def create_contract_investigation", start)
        branch = source[start:end]
        for token in ("_copy_seal_source_attachments", "source_attachment_ids", "await db.rollback()", "target.unlink"):
            self.assertIn(token, branch)

    def test_contract_ui_passes_selected_contract_files_into_application(self):
        source = FRONTEND.read_text(encoding="utf-8")
        start = source.index("const createSealApplication")
        end = source.index("const", start + len("const createSealApplication"))
        self.assertIn("source_attachment_ids", source[start:])
        self.assertIn("attachments.map", source[start:])


if __name__ == "__main__":
    unittest.main()

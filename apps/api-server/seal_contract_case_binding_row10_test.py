"""Static source check: contract seal application must bind linked case via ContractObject.

Row 10 / sheet 9.2: contract seal applications created from the contract side
must carry the case_no of the contract's linked case.  The link between
contracts and cases is authoritative in ContractObject (the many-to-many
table), not in case.data contract references.
"""

from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parent
MAIN = REPO / "app" / "main.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SealContractCaseBindingRow10Test(unittest.TestCase):
    def _function_body(self, name: str) -> str:
        source = read(MAIN)
        start = source.index(f"async def {name}(")
        # find the next top-level async def after this one
        rest = source[start + 1:]
        next_def = rest.index("\nasync def ")
        return source[start:start + 1 + next_def]

    def test_single_linked_case_prefers_contract_object_table(self):
        """_single_linked_case_for_contract must look up via ContractObject first.

        The authoritative contract-case relationship lives in the ContractObject
        join table.  Relying on case.data["contract_no"] / contract_record_id is
        unreliable because those JSON fields are not guaranteed to be present
        or current.
        """
        body = self._function_body("_single_linked_case_for_contract")
        self.assertIn(
            "ContractObject.contract_record_id",
            body,
            "ContractObject join table must be the primary lookup path",
        )
        self.assertIn(
            "ContractObject.case_record_id",
            body,
            "ContractObject.case_record_id must be used to join with case records",
        )

    def test_single_linked_case_falls_back_to_data_references(self):
        """Keep the legacy data-based fallback for contracts that have no
        ContractObject rows but still have a case pointing at them via JSON.
        """
        body = self._function_body("_single_linked_case_for_contract")
        self.assertIn(
            'data["contract_record_id"]',
            body,
            "Legacy contract_record_id JSON fallback must remain",
        )
        self.assertIn(
            'data["contract_no"]',
            body,
            "Legacy contract_no JSON fallback must remain",
        )

    def test_contract_seal_application_still_binds_case(self):
        """create_contract_seal_application must still set case_no from the
        linked case after the refactor.
        """
        body = self._function_body("create_contract_seal_application")
        self.assertIn(
            "_single_linked_case_for_contract(contract, identity, db)",
            body,
        )
        self.assertIn('"case_no": linked_case.serial_no if linked_case else ""', body)
        self.assertIn(
            '"case_record_id": linked_case.id if linked_case else None',
            body,
        )

    def test_validated_seal_relations_still_uses_single_linked_case(self):
        """_validated_seal_relations (used by generic seal creation) must still
        resolve contract -> case via the shared helper.
        """
        body = self._function_body("_validated_seal_relations")
        self.assertIn("_single_linked_case_for_contract(contract, identity, db)", body)


if __name__ == "__main__":
    unittest.main()

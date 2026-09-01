from __future__ import annotations

import unittest

from app.main import _contract_customer_manager_values
from app.models import BusinessRecord


def record(module: str, owner: str, managers: list[str]) -> BusinessRecord:
    return BusinessRecord(
        module=module,
        serial_no=f"CODEX-901-ROW25-{module}",
        title=f"row25-{module}",
        customer="row25-customer",
        status="审批中" if module == "contract" else "跟进中",
        owner=owner,
        department="测试部",
        description="row 25 projection regression",
        data={"customer_managers": managers},
    )


class ContractCustomerManagerProjectionRow25Test(unittest.TestCase):
    def test_linked_customer_roster_replaces_contract_creation_snapshot(self) -> None:
        contract = record("contract", "source-owner", ["taowei", "fanwenlin", "stale-person"])
        customer = record("customer", "taowei", ["taowei", "fanwenlin"])

        self.assertEqual(
            _contract_customer_manager_values(contract, customer),
            ["taowei", "fanwenlin"],
        )
        self.assertEqual(
            contract.data["customer_managers"],
            ["taowei", "fanwenlin", "stale-person"],
            "presentation projection must not rewrite the contract history snapshot",
        )

    def test_unresolved_customer_keeps_deduplicated_contract_snapshot(self) -> None:
        contract = record("contract", "source-owner", ["taowei", "taowei", "fanwenlin"])

        self.assertEqual(
            _contract_customer_manager_values(contract, None),
            ["taowei", "fanwenlin"],
        )

    def test_customer_owner_is_the_legacy_fallback_when_roster_is_empty(self) -> None:
        contract = record("contract", "source-owner", ["stale-person"])
        customer = record("customer", "taowei", [])

        self.assertEqual(_contract_customer_manager_values(contract, customer), ["taowei"])


if __name__ == "__main__":
    unittest.main()

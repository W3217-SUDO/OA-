from __future__ import annotations

import unittest

from app.main import _contract_investigation_source_data
from app.models import BusinessRecord


class ContractInvestigationSourceRow26Test(unittest.TestCase):
    def test_contract_and_customer_identity_are_persisted_together(self) -> None:
        contract = BusinessRecord(
            id=261,
            module="contract",
            serial_no="SHHT2673411",
            title="测试客户8.3合同11",
            customer="过期客户名称",
            status="审批中",
            owner="publisher",
            department="测试部",
            description="",
            data={"customer_id": 26, "customer_no": "OLD-NO"},
        )
        customer = BusinessRecord(
            id=26,
            module="customer",
            serial_no="SHKH2600002",
            title="测试客户8.3",
            customer="",
            status="跟进中",
            owner="manager",
            department="测试部",
            description="",
            data={"customer_managers": ["manager"]},
        )

        self.assertEqual(
            _contract_investigation_source_data(contract, customer),
            {
                "contract_id": 261,
                "contract_record_id": 261,
                "contract_no": "SHHT2673411",
                "contract_name": "测试客户8.3合同11",
                "customer_id": 26,
                "customer_record_id": 26,
                "customer_no": "SHKH2600002",
                "customer_name": "测试客户8.3",
            },
        )


if __name__ == "__main__":
    unittest.main()

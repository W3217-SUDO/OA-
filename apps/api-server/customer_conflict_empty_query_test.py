"""Regression: an empty customer-conflict query loads the default latest case."""

import asyncio
from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.main import customer_conflicts  # noqa: E402


class _ScalarRows(list):
    def all(self):
        return list(self)


class _ConflictQueryDb:
    """Read-only query double; each scalar call follows the endpoint query order."""

    def __init__(self, cases, customers, users):
        self._rows = [_ScalarRows(cases), _ScalarRows(customers), _ScalarRows(users)]

    async def scalars(self, _statement):
        return self._rows.pop(0)


def _record(**values):
    return SimpleNamespace(
        id=values.pop("id"),
        module=values.pop("module"),
        serial_no=values.pop("serial_no", ""),
        title=values.pop("title", ""),
        customer=values.pop("customer", ""),
        status=values.pop("status", "正常"),
        owner=values.pop("owner", ""),
        data=values.pop("data", {}),
        updated_at=values.pop("updated_at", datetime(2026, 1, 1)),
        created_at=values.pop("created_at", datetime(2026, 1, 1)),
        **values,
    )


class CustomerConflictEmptyQueryTest(unittest.TestCase):
    def test_empty_query_returns_a_default_case(self):
        async def run():
            async with SessionLocal() as session:
                return await customer_conflicts(
                    name="",
                    identity={"role": "admin"},
                    db=session,
                )

        result = asyncio.run(run())

        self.assertTrue(result["found"])
        self.assertTrue(result["latest_case_no"])

    def test_empty_query_resolves_managers_from_default_case_customer(self):
        """A blank-title customer must never supply a default case's managers."""
        default_customer = "默认案件客户"
        db = _ConflictQueryDb(
            cases=[_record(
                id=1,
                module="case",
                serial_no="CASE-DEFAULT",
                customer=default_customer,
                data={"filing_date": "2026-01-02"},
            )],
            customers=[
                _record(
                    id=99,
                    module="customer",
                    owner="blank-manager",
                    data={"customer_managers": ["blank-manager"]},
                ),
                _record(
                    id=1,
                    module="customer",
                    title=default_customer,
                    customer=default_customer,
                    owner="default-manager",
                    data={"customer_managers": ["default-manager"]},
                ),
            ],
            users=[
                SimpleNamespace(username="blank-manager", display_name="空名管理人"),
                SimpleNamespace(username="default-manager", display_name="默认客户管理人"),
            ],
        )

        result = asyncio.run(customer_conflicts(name="", identity={"role": "admin"}, db=db))

        self.assertEqual(result["our_customer"], default_customer)
        self.assertEqual(result["customer_managers"], ["默认客户管理人"])

    def test_empty_query_uses_default_case_customer_without_a_blank_customer(self):
        """The default manager lookup also remains stable when no blank customer exists."""
        default_customer = "无空名客户默认案件"
        db = _ConflictQueryDb(
            cases=[_record(
                id=1,
                module="case",
                serial_no="CASE-NO-BLANK",
                customer=default_customer,
                data={"filing_date": "2026-01-03"},
            )],
            customers=[_record(
                id=1,
                module="customer",
                title=default_customer,
                customer=default_customer,
                owner="default-manager",
                data={"customer_managers": ["default-manager"]},
            )],
            users=[SimpleNamespace(username="default-manager", display_name="默认客户管理人")],
        )

        result = asyncio.run(customer_conflicts(name="", identity={"role": "admin"}, db=db))

        self.assertEqual(result["our_customer"], default_customer)
        self.assertEqual(result["customer_managers"], ["默认客户管理人"])


if __name__ == "__main__":
    unittest.main()

"""Regression contracts for customer-conflict query validation and matching."""

import asyncio
from datetime import datetime
from pathlib import Path
import sys
import unittest

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.main import customer_conflicts  # noqa: E402
from app.models import BusinessRecord, User  # noqa: E402


class _ScalarRows(list):
    def all(self):
        return list(self)


class _ConflictQueryDb:
    """只按真实 ORM 实体和模块条件返回记录。"""

    def __init__(self, cases, customers, users):
        self.cases = cases
        self.customers = customers
        self.users = users

    async def scalars(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is User:
            return _ScalarRows(self.users)
        if entity is BusinessRecord:
            values = set(statement.compile().params.values())
            if "case" in values:
                return _ScalarRows(self.cases)
            if "customer" in values:
                return _ScalarRows(self.customers)
        raise AssertionError(f"未预期的查询：{statement}")


def _record(**values):
    return BusinessRecord(
        id=values.pop("id"),
        module=values.pop("module"),
        serial_no=values.pop("serial_no", ""),
        title=values.pop("title", ""),
        customer=values.pop("customer", ""),
        status=values.pop("status", "normal"),
        owner=values.pop("owner", ""),
        data=values.pop("data", {}),
        updated_at=values.pop("updated_at", datetime(2026, 1, 1)),
        created_at=values.pop("created_at", datetime(2026, 1, 1)),
        **values,
    )


class CustomerConflictEmptyQueryTest(unittest.TestCase):
    def assert_empty_query_rejected(self, db):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(customer_conflicts(name="", identity={"role": "admin"}, db=db))
        self.assertEqual(raised.exception.status_code, 422)

    def test_empty_query_is_rejected_before_database_lookup(self):
        self.assert_empty_query_rejected(_ConflictQueryDb(cases=[], customers=[], users=[]))

    def test_empty_query_does_not_resolve_blank_customer_managers(self):
        self.assert_empty_query_rejected(_ConflictQueryDb(
            cases=[_record(id=1, module="case", serial_no="CASE-BLANK", customer="Exact Customer")],
            customers=[_record(id=99, module="customer", owner="blank-manager", data={"customer_managers": ["blank-manager"]})],
            users=[User(username="blank-manager", display_name="Blank Manager", is_active=True)],
        ))

    def test_empty_query_is_rejected_even_when_a_default_case_exists(self):
        self.assert_empty_query_rejected(_ConflictQueryDb(
            cases=[_record(id=1, module="case", serial_no="CASE-DEFAULT", customer="Exact Customer")],
            customers=[_record(id=1, module="customer", title="Exact Customer", customer="Exact Customer", owner="exact-manager", data={"customer_managers": ["exact-manager"]})],
            users=[User(username="exact-manager", display_name="Exact Manager", is_active=True)],
        ))

    def test_exact_query_resolves_matching_case_customer_managers(self):
        customer_name = "Exact Customer"
        db = _ConflictQueryDb(
            cases=[_record(id=1, module="case", serial_no="CASE-EXACT", customer=customer_name, data={"filing_date": "2026-01-03"})],
            customers=[
                _record(id=99, module="customer", owner="other-manager", data={"customer_managers": ["other-manager"]}),
                _record(id=1, module="customer", title=customer_name, customer=customer_name, owner="exact-manager", data={"customer_managers": ["exact-manager"]}),
            ],
            users=[
                User(username="other-manager", display_name="Other Manager", is_active=True),
                User(username="exact-manager", display_name="Exact Manager", is_active=True),
            ],
        )

        result = asyncio.run(customer_conflicts(name=customer_name, identity={"role": "admin"}, db=db))

        self.assertTrue(result["found"])
        self.assertEqual(result["latest_case_no"], "CASE-EXACT")
        self.assertEqual(result["our_customer"], customer_name)
        self.assertEqual(result["customer_managers"], ["Exact Manager"])


if __name__ == "__main__":
    unittest.main()

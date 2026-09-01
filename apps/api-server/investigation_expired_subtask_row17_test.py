"""9.1 row 17: expired investigation authorizations cannot create subtasks."""
from __future__ import annotations

from datetime import date
import unittest

from app.main import _investigation_authorization_expired
from app.models import BusinessRecord


def investigation(data: dict) -> BusinessRecord:
    return BusinessRecord(module="investigation", serial_no="R17-INV", title="调查事项", customer="客户", status="待分配", owner="supervisor", department="调查部", data=data)


class InvestigationExpiredSubtaskRow17Test(unittest.TestCase):
    def test_authorization_that_ended_before_today_is_expired(self):
        self.assertTrue(_investigation_authorization_expired(investigation({"authorized_to": "2024-11-23T00:00:00+08:00"}), today=date(2026, 9, 1)))

    def test_today_and_future_authorizations_are_not_expired(self):
        for value in ("2026-09-01", "2026-09-02T00:00:00+08:00"):
            with self.subTest(value=value):
                self.assertFalse(_investigation_authorization_expired(investigation({"authorized_to": value}), today=date(2026, 9, 1)))

    def test_legacy_end_date_is_used_when_authorized_to_is_missing(self):
        self.assertTrue(_investigation_authorization_expired(investigation({"end_date": "2024-11-23"}), today=date(2026, 9, 1)))

    def test_missing_or_invalid_end_date_does_not_invent_expiry(self):
        for data in ({}, {"authorized_to": "not-a-date"}):
            with self.subTest(data=data):
                self.assertFalse(_investigation_authorization_expired(investigation(data), today=date(2026, 9, 1)))


if __name__ == "__main__":
    unittest.main()

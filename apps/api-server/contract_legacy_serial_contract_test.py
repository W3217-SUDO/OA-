import asyncio
from datetime import datetime
import re
from pathlib import Path
import unittest

from app.main import _next_contract_serial_no


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _FakeSession:
    def __init__(self, values):
        self._values = values

    async def scalars(self, _statement):
        return _ScalarResult(self._values)


class ContractLegacySerialContractTest(unittest.TestCase):
    def test_next_contract_serial_uses_legacy_shht_year_sequence(self):
        prefix = f"SHHT{datetime.now():%y}"
        db = _FakeSession([f"{prefix}00001", f"{prefix}00009", "HT20260802123456"])

        serial = asyncio.run(_next_contract_serial_no(db))

        self.assertEqual(serial, f"{prefix}00010")
        self.assertRegex(serial, rf"^SHHT{datetime.now():%y}\d{{5}}$")
        self.assertLessEqual(len(serial), 11)

    def test_contract_create_ignores_non_legacy_client_serial(self):
        source = Path("app/main.py").read_text(encoding="utf-8")

        self.assertIn('async with _contract_serial_lock:', source)
        self.assertIn('serial_no = await _next_contract_serial_no(db)', source)
        self.assertNotIn('requested_serial_no = body.serial_no.strip()', source)
        self.assertIn('合同名称已存在，不能新建同名合同', source)

    def test_contract_submit_persists_sync_seal_choice(self):
        source = Path("app/main.py").read_text(encoding="utf-8")

        self.assertIn('sync_seal: bool = False', source)
        self.assertIn('"sync_seal": body.sync_seal', source)

    def test_contract_investigation_uses_the_configured_supervisor_only(self):
        source = Path("app/main.py").read_text(encoding="utf-8")

        self.assertIn('"investigation_assignment"', source)
        self.assertIn('async def _configured_investigation_supervisor', source)
        self.assertIn('supervisor = await _configured_investigation_supervisor(db)', source)
        self.assertIn('requested_owner != supervisor.username', source)
        self.assertIn('调查任务必须分配给系统配置的调查主管', source)


if __name__ == "__main__":
    unittest.main()

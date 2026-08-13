import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
IMPORTER = ROOT / "scripts" / "import_sh_latest50_samples.py"


class LegacyFullInvestigationImportContractTest(unittest.TestCase):
    def test_legacy_datetime_values_are_naive_wall_time(self):
        from app.models import LegacyCustomer
        from scripts.import_sh_latest50_samples import legacy_values

        values = legacy_values(
            LegacyCustomer,
            {"CreateTime": "2019-01-02T16:41:09.317000+08:00"},
        )
        self.assertIsNone(values["CreateTime"].tzinfo)
        self.assertEqual(values["CreateTime"].hour, 16)

    def test_existing_soft_key_rows_keep_their_primary_key(self):
        source = IMPORTER.read_text(encoding="utf-8")
        self.assertIn("primary_keys = [column.name for column in model.__table__.primary_key.columns]", source)
        self.assertIn("if name in primary_keys:\n                    continue", source)
        self.assertIn("if primary_value is not None and await db.get(model, primary_value) is not None:", source)

    def test_exporter_omits_sensitive_staff_fields(self):
        source = (ROOT / "scripts" / "export_legacy_investigation_tree.ps1").read_text(encoding="utf-8")
        self.assertNotIn("SELECT s.*", source)
        for field in ("Password", "OrgPassword", "IdentityNo", "Email", "MobilePhone"):
            self.assertNotIn(f"s.{field}", source)
        for field in ("StaffNo", "StaffName", "StaffChName", "DepartmentId", "IsActived"):
            self.assertIn(f"s.{field}", source)

    def test_full_tree_import_is_complete_and_idempotent(self):
        bundle = os.environ.get("LEGACY_SAMPLE_BUNDLE")
        investigation_bundle = os.environ.get("LEGACY_FULL_INVESTIGATION_BUNDLE")
        if not bundle or not investigation_bundle:
            self.skipTest("full 8091 migration bundle paths were not supplied")

        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "legacy-full-investigation.db"
            env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{database}"}
            subprocess.run(
                [sys.executable, "-c", """
import asyncio
from app.database import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password
async def main():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        db.add(User(username='admin', display_name='管理员', role='admin', role_ids=['admin'], department='测试', password_hash=hash_password('CODEX-test-password'), is_active=True))
        await db.commit()
asyncio.run(main())
"""],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            command = [
                sys.executable,
                str(IMPORTER),
                bundle,
                "--investigation-bundle",
                investigation_bundle,
            ]
            first = json.loads(subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True, text=True).stdout)
            second = json.loads(subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True, text=True).stdout)

            self.assertEqual(first["expected"]["investigations"], 126)
            self.assertEqual(first["expected"]["tasks"], 963)
            self.assertEqual(first["records"]["investigations"], 126)
            self.assertEqual(first["records"]["tasks"], 963)
            self.assertEqual(second["records"]["investigations"], 0)
            self.assertEqual(second["records"]["tasks"], 0)
            self.assertEqual(second["legacy"]["investigations"]["created"], 0)
            self.assertEqual(second["legacy"]["tasks"]["created"], 0)


if __name__ == "__main__":
    unittest.main()

"""Regression checks for importing historical case relation projections."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUNDLE = Path(__file__).resolve().parents[4] / "legacy-gdcrm-101-local-20260812" / "backup"
IMPORTER = ROOT / "scripts" / "import_sh_latest50_samples.py"


class Latest50CaseRelationsImportContractTest(unittest.TestCase):
    def test_import_is_idempotent_and_preserves_relation_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "latest50.db"
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
            first = subprocess.run(
                [sys.executable, str(IMPORTER), str(BUNDLE)],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            second = subprocess.run(
                [sys.executable, str(IMPORTER), str(BUNDLE)],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            first_result = json.loads(first.stdout)
            second_result = json.loads(second.stdout)
            self.assertEqual(first_result["legacy"]["case_files"]["created"], 86)
            self.assertEqual(first_result["legacy"]["case_participants"]["created"], 141)
            self.assertEqual(first_result["legacy"]["case_logs"]["created"], 261)
            for key in ("case_files", "case_participants", "case_logs"):
                self.assertEqual(second_result["legacy"][key]["created"], 0)

            # The importer subprocess has its own engine; inspect through a
            # short subprocess so this test uses the same DATABASE_URL.
            probe = subprocess.run(
                [sys.executable, "-c", """
import asyncio
import json
from sqlalchemy import func, select
from app.database import SessionLocal
from app.models import LegacyCaseFile, LegacyCaseParticipant, LegacyCaseLog
async def main():
    async with SessionLocal() as db:
        print(json.dumps({
            'case_files': await db.scalar(select(func.count()).select_from(LegacyCaseFile)),
            'case_participants': await db.scalar(select(func.count()).select_from(LegacyCaseParticipant)),
            'case_logs': await db.scalar(select(func.count()).select_from(LegacyCaseLog)),
        }))
asyncio.run(main())
"""],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(json.loads(probe.stdout), {"case_files": 86, "case_participants": 141, "case_logs": 261})


if __name__ == "__main__":
    unittest.main()



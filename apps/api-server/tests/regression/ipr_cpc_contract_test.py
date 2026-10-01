import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "cpc-admin", "role": "admin", "display_name": "CPC Admin", "department": "IPR"}


class IprCpcContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.upload_root = Path(tempfile.mkdtemp(prefix="codex-cpc-"))
        from app import main as main_module
        self.main_module = main_module
        self.original_upload_root = main_module.UPLOAD_ROOT
        main_module.UPLOAD_ROOT = self.upload_root
        async with self.sessions() as db:
            db.add_all([
                User(username="cpc-admin", display_name="CPC Admin", department="IPR", role="admin", password_hash="x", is_active=True),
                User(username="cpc-owner", display_name="CPC Owner", department="IPR", role="user", password_hash="x", is_active=True),
                User(username="cpc-other", display_name="CPC Other", department="Other", role="user", password_hash="x", is_active=True),
            ])
            patent = BusinessRecord(module="ipr_case", serial_no="CODEX-CPC-P-001", title="便携式检测装置", customer="CODEX客户", status="在办", owner="cpc-owner", department="IPR", data={"case_kind": "专利", "applicant": "CODEX申请人", "application_no": "20260001", "application_type": "发明", "inventor": "测试发明人"})
            trademark = BusinessRecord(module="ipr_case", serial_no="CODEX-CPC-T-001", title="商标案件", customer="CODEX客户", status="在办", owner="cpc-owner", department="IPR", data={"case_kind": "商标", "applicant": "CODEX申请人"})
            incomplete = BusinessRecord(module="ipr_case", serial_no="CODEX-CPC-P-002", title="缺申请人专利", customer="CODEX客户", status="在办", owner="cpc-owner", department="IPR", data={"case_kind": "专利"})
            db.add_all([patent, trademark, incomplete])
            await db.flush()
            self.patent_id, self.trademark_id, self.incomplete_id = patent.id, trademark.id, incomplete.id
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://cpc.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.main_module.UPLOAD_ROOT = self.original_upload_root
        shutil.rmtree(self.upload_root)
        self.assertFalse(self.upload_root.exists(), "CPC test upload directory must be removed")
        await self.engine.dispose()

    async def test_generate_history_download_and_immutable_snapshot(self):
        generated = await self.client.post(f"{API}/ipr/cases/{self.patent_id}/cpc-applications")
        self.assertEqual(generated.status_code, 201, generated.text)
        item = generated.json()
        self.assertTrue(item["original_name"].endswith(".zip"))
        self.assertEqual(item["format"], "CPC基础申报信息快照（非官方CPC申报格式）")

        downloaded = await self.client.get(item["download_url"])
        self.assertEqual(downloaded.status_code, 200, downloaded.text)
        self.assertEqual(downloaded.headers["content-type"].split(";")[0], "application/zip")
        with zipfile.ZipFile(io.BytesIO(downloaded.content)) as package:
            self.assertEqual(set(package.namelist()), {"CPC基础申报信息.txt", "CPC基础申报信息.json"})
            self.assertIn("便携式检测装置", package.read("CPC基础申报信息.txt").decode("utf-8"))
            payload = json.loads(package.read("CPC基础申报信息.json"))
            self.assertEqual(payload["application"]["applicant"], "CODEX申请人")
            self.assertNotIn("data", payload)

        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.patent_id)
            record.data = {**record.data, "applicant": "后续修改的申请人"}
            await db.commit()
        later = await self.client.post(f"{API}/ipr/cases/{self.patent_id}/cpc-applications")
        self.assertEqual(later.status_code, 201, later.text)
        history = await self.client.get(f"{API}/ipr/cases/{self.patent_id}/cpc-applications")
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()["total"], 2)
        self.assertEqual(history.json()["items"][0]["id"], later.json()["id"])
        old_bytes = (await self.client.get(item["download_url"])).content
        with zipfile.ZipFile(io.BytesIO(old_bytes)) as package:
            self.assertIn("CODEX申请人", package.read("CPC基础申报信息.txt").decode("utf-8"))

        unlock = await self.client.post(f"{API}/ipr/cases/{self.patent_id}/files/{item['id']}/unlock")
        self.assertEqual(unlock.status_code, 409, unlock.text)
        deletion = await self.client.delete(f"{API}/ipr/cases/{self.patent_id}/files/{item['id']}")
        self.assertEqual(deletion.status_code, 409, deletion.text)
        async with self.sessions() as db:
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.patent_id))).all())
            self.assertTrue(any(event.action == "生成CPC基础申报信息快照" for event in events))

    async def test_validates_patent_required_fields_and_cross_case_history_ids(self):
        self.assertEqual((await self.client.post(f"{API}/ipr/cases/{self.trademark_id}/cpc-applications")).status_code, 422)
        self.assertEqual((await self.client.post(f"{API}/ipr/cases/{self.incomplete_id}/cpc-applications")).status_code, 422)
        generated = await self.client.post(f"{API}/ipr/cases/{self.patent_id}/cpc-applications")
        self.assertEqual(generated.status_code, 201, generated.text)
        cross_case = await self.client.get(f"{API}/ipr/cases/{self.incomplete_id}/cpc-applications/{generated.json()['id']}/download")
        self.assertEqual(cross_case.status_code, 404, cross_case.text)
        async with self.sessions() as db:
            self.assertEqual(int(await db.scalar(select(func.count()).select_from(FileAttachment).where(FileAttachment.record_id == self.incomplete_id)) or 0), 0)

    async def test_current_record_permissions_apply_to_generate_history_and_download(self):
        generated = await self.client.post(f"{API}/ipr/cases/{self.patent_id}/cpc-applications")
        self.assertEqual(generated.status_code, 201, generated.text)
        app.dependency_overrides[current_identity] = lambda: {"username": "cpc-other", "role": "user", "display_name": "CPC Other", "department": "Other"}
        self.assertIn((await self.client.post(f"{API}/ipr/cases/{self.patent_id}/cpc-applications")).status_code, {403, 404})
        self.assertIn((await self.client.get(f"{API}/ipr/cases/{self.patent_id}/cpc-applications")).status_code, {403, 404})
        self.assertIn((await self.client.get(generated.json()["download_url"])).status_code, {403, 404})

    async def test_read_history_remains_available_after_case_closes_but_generation_does_not(self):
        generated = await self.client.post(f"{API}/ipr/cases/{self.patent_id}/cpc-applications")
        self.assertEqual(generated.status_code, 201, generated.text)
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.patent_id)
            record.status = "已结案"
            await db.commit()
        self.assertEqual((await self.client.get(f"{API}/ipr/cases/{self.patent_id}/cpc-applications")).status_code, 200)
        self.assertEqual((await self.client.get(generated.json()["download_url"])).status_code, 200)
        self.assertEqual((await self.client.post(f"{API}/ipr/cases/{self.patent_id}/cpc-applications")).status_code, 409)


if __name__ == "__main__":
    unittest.main()

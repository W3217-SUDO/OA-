"""9.29 调查详情、附件只读边界和日期持久化的独立 API 验证。"""
import json
import os
from datetime import date, timedelta
from pathlib import Path
import unittest

EVIDENCE = Path(os.environ["OA_BATCH_EVIDENCE"]).resolve()
(EVIDENCE / "tasks").mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(EVIDENCE / 'tasks-test.db').as_posix()}"
os.environ["UPLOAD_ROOT"] = str(EVIDENCE / "tasks-uploads")
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["DINGTALK_NOTIFICATIONS_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "isolated-local-regression-key-not-for-deployment"

import httpx
from docx import Document
from sqlalchemy import select, func
from app.main import app
from app.database import Base, SessionLocal, engine
from app.models import BusinessRecord, FileAttachment, RolePermission, SystemConfig, User
from app.security import create_token
from app.core.tasks import _validate_task_deadline
from fastapi import HTTPException


class Investigation929ApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.prefix = "CODEX-929-R14"
        self.uploads = EVIDENCE / "tasks-uploads"
        self.uploads.mkdir(parents=True, exist_ok=True)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with SessionLocal() as db:
            existing = await db.scalar(select(func.count()).select_from(BusinessRecord))
            self.assertEqual(existing, 0, "隔离数据库必须为空，不能覆盖既有数据")
            for role in ["publisher", "supervisor", "assignee", "sibling", "outsider", "admin", "shared", "department_reader", "company_reader", "manager"]:
                scope = {"department_reader": "本部门数据", "company_reader": "全所数据"}.get(role)
                db.add(User(username=f"{self.prefix}-{role}", display_name=f"{role}测试人员", role=role if role in {"admin", "manager"} else "user", role_ids=[], password_hash="isolated-test", department="supervisor" if role in {"department_reader", "manager"} else role, profile={"permission_overrides": {"data_scope": scope}} if scope else {}, is_active=True))
            db.add(RolePermission(role="user", display_name="调查人员", menu_keys=["investigation-task-sub-mine", "investigation-task-published", "investigation-task-mine"], field_keys=[], data_scope="本人及共享数据"))
            db.add(RolePermission(role="manager", display_name="部门负责人", menu_keys=["investigation-task-sub-mine", "investigation-task-published", "investigation-task-mine"], field_keys=[], data_scope="本部门数据"))
            db.add(SystemConfig(key="investigation_assignment", label="调查主管", value={"supervisor_username": f"{self.prefix}-supervisor"}))
            contract = self.record("contract", "contract", "publisher", status="审批通过", data={})
            db.add(contract); await db.flush()
            common = {"publisher": f"{self.prefix}-publisher", "source_owner": f"{self.prefix}-publisher", "contract_id": contract.id, "contract_record_id": contract.id, "contract_no": contract.serial_no, "right_type": "商标", "authorized_from": str(date.today()), "authorized_to": str(date.today() + timedelta(days=200)), "region": "上海"}
            parent = self.record("investigation", "parent", "supervisor", data=common)
            other = self.record("investigation", "other", "outsider", data={})
            db.add_all([parent, other]); await db.flush()
            self.parent_id, self.other_id = parent.id, other.id
            child = self.record("task", "child", "assignee", data={**common, "investigation_record_id": parent.id, "initiator": f"{self.prefix}-supervisor", "shared_to": [f"{self.prefix}-shared"], "start_date": str(date.today()+timedelta(days=3)), "end_date": str(date.today()+timedelta(days=50)), "deadline": str(date.today()+timedelta(days=90)), "attachment_ids": []})
            sibling = self.record("task", "sibling", "sibling", data={"investigation_record_id": parent.id, "initiator": f"{self.prefix}-supervisor"})
            db.add_all([child, sibling]); await db.flush()
            self.child_id, self.sibling_id = child.id, sibling.id
            for index in range(18):
                db.add(self.record("clue", f"clue-{index}", "assignee", data={"source_task_id": child.id, "investigation_record_id": parent.id, "collected_at": str(date.today())}))
            db.add(self.record("clue", "sibling-clue", "sibling", data={"source_task_id": sibling.id, "investigation_record_id": parent.id}))
            self.file_ids = []
            for index, record_id in enumerate([parent.id, other.id, sibling.id]):
                path = self.uploads / f"{self.prefix}-{index}.docx"
                document = Document(); document.add_paragraph(f"{self.prefix} 调查授权资料 {index}"); document.save(path)
                attachment = FileAttachment(record_id=record_id, category="调查授权书", original_name=f"调查资料{index}.docx", stored_name=path.name, path=str(path), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", size=path.stat().st_size, uploader=f"{self.prefix}-publisher")
                db.add(attachment); await db.flush(); self.file_ids.append(attachment.id)
            await db.commit()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated-task.test")
        self.results = []

    def record(self, module, suffix, owner, status="进行中", data=None):
        return BusinessRecord(module=module, serial_no=f"{self.prefix}-{suffix}", title=f"{self.prefix} {suffix}", customer=f"{self.prefix}客户", owner=f"{self.prefix}-{owner}", department=owner, status=status, description="完整调查说明", data=data or {})

    async def request(self, role, method, path, expected=200, **kwargs):
        headers = {"Authorization": f"Bearer {create_token(f'{self.prefix}-{role}', role if role in {'admin', 'manager'} else 'user')}", "X-Page-Key": "investigation-task-sub-mine"}
        response = await self.client.request(method, "/api/v1"+path, headers=headers, **kwargs)
        self.assertIn(response.status_code, expected if isinstance(expected, tuple) else (expected,), response.text[:1000])
        self.results.append({"role": role, "method": method, "path": path, "status": response.status_code})
        return response

    async def test_real_api_permissions_pagination_and_persistence(self):
        for role in ["publisher", "supervisor", "admin"]:
            result = (await self.request(role, "GET", f"/investigations/{self.parent_id}/task-detail")).json()
            self.assertEqual(result["total"], 2)
            self.assertEqual({row["id"] for row in result["items"]}, {self.child_id, self.sibling_id})
            self.assertEqual(result["materials"][0]["id"], self.file_ids[0])
            self.assertEqual(result["materials"][0]["category"], "调查授权书")
        for role in ["assignee", "publisher", "supervisor"]:
            result = (await self.request(role, "GET", f"/investigations/{self.child_id}/task-detail?page_size=15")).json()
            self.assertEqual((len(result["items"]), result["total"]), (15, 18))
            self.assertEqual(result["parent"]["id"], self.parent_id)
            self.assertNotEqual(result["record"]["data"]["end_date"], result["parent"]["data"]["authorized_to"])
            self.assertEqual(result["materials"][0]["id"], self.file_ids[0])
        parent_page = (await self.request("publisher", "GET", f"/investigations/{self.parent_id}/task-detail?page_size=1")).json()
        self.assertEqual((len(parent_page["items"]), parent_page["total"]), (1, 2))
        second = (await self.request("assignee", "GET", f"/investigations/{self.child_id}/task-detail?page=2&page_size=15")).json()
        self.assertEqual(len(second["items"]), 3)
        for role, record_id in [("assignee", self.other_id), ("assignee", self.sibling_id), ("outsider", self.child_id), ("outsider", self.parent_id)]:
            await self.request(role, "GET", f"/investigations/{record_id}/task-detail", (403, 404))
        for role in ["assignee", "publisher", "supervisor"]:
            file = self.file_ids[0]
            preview = (await self.request(role, "GET", f"/attachments/{file}/preview")).json()
            self.assertEqual(preview["kind"], "docx")
            download = await self.request(role, "GET", f"/attachments/{file}/download")
            self.assertTrue(download.content.startswith(b"PK"))
        for file in self.file_ids[1:]:
            await self.request("assignee", "GET", f"/attachments/{file}/download", (403, 404))
        await self.request("outsider", "GET", f"/attachments/{self.file_ids[0]}/preview", (403, 404))
        await self.request("assignee", "DELETE", f"/attachments/{self.file_ids[0]}", (403, 404))
        await self.request("assignee", "POST", "/attachments", (403, 404), data={"record_id": self.parent_id, "category": "调查授权书"}, files={"file": ("blocked.txt", b"blocked", "text/plain")})
        await self.request("assignee", "PATCH", f"/investigations/records/{self.parent_id}", (403, 404), json={"description": "不能通过只读详情写入"})
        await self.request("assignee", "PATCH", f"/records/{self.parent_id}", (403, 404), json={"description": "不能通过通用入口写入"})
        # 子任务共享不隐式授予父调查资料；父记录独立共享后才可读取。
        await self.request("shared", "GET", f"/investigations/{self.child_id}/task-detail", (403, 404))
        await self.request("shared", "GET", f"/attachments/{self.file_ids[0]}/download", (403, 404))
        async with SessionLocal() as db:
            parent = await db.get(BusinessRecord, self.parent_id)
            parent.data = {**parent.data, "shared_to": [f"{self.prefix}-shared"]}
            await db.commit()
        shared_detail = (await self.request("shared", "GET", f"/investigations/{self.child_id}/task-detail")).json()
        self.assertEqual(shared_detail["materials"][0]["id"], self.file_ids[0])
        for role in ["shared", "department_reader", "company_reader"]:
            parent_detail = (await self.request(role, "GET", f"/investigations/{self.parent_id}/task-detail")).json()
            self.assertEqual(parent_detail["materials"][0]["id"], self.file_ids[0])
            self.assertTrue((await self.request(role, "GET", f"/attachments/{self.file_ids[0]}/download")).content.startswith(b"PK"))
            self.assertEqual((await self.request(role, "GET", f"/attachments/{self.file_ids[0]}/preview")).json()["kind"], "docx")
            await self.request(role, "POST", "/attachments", 403, data={"record_id": self.parent_id, "category": "调查授权书"}, files={"file": ("blocked.txt", b"blocked", "text/plain")})
            await self.request(role, "DELETE", f"/attachments/{self.file_ids[0]}", 403)
            await self.request(role, "PATCH", f"/investigations/records/{self.parent_id}", 403, json={"description": "只读共享不能写入"})
            await self.request(role, "PATCH", f"/records/{self.parent_id}", 403, json={"description": "只读范围不能写入"})
        async with SessionLocal() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(FileAttachment)), 3)
            self.assertTrue(Path((await db.get(FileAttachment, self.file_ids[0])).path).is_file())
        for role in ["publisher", "supervisor", "admin", "manager"]:
            uploaded = (await self.request(role, "POST", "/attachments", 201, data={"record_id": self.parent_id, "category": "调查授权书"}, files={"file": ("CODEX-929-R14-authorized.txt", b"authorized", "text/plain")})).json()
            await self.request(role, "DELETE", f"/attachments/{uploaded['id']}", 204)
        await self.request("assignee", "GET", "/investigations/999999/task-detail", 404)
        deadline, end = date.today()+timedelta(days=900), date.today()+timedelta(days=60)
        payload = {"title": "CODEX-929-R16 长期调查", "owner": f"{self.prefix}-assignee", "deadline": str(deadline), "start_date": str(date.today()+timedelta(days=2)), "end_date": str(end), "province": "上海市", "city": "上海市"}
        created = (await self.request("supervisor", "POST", f"/investigations/{self.parent_id}/tasks", 201, json=payload)).json()
        async with SessionLocal() as db:
            stored = await db.get(BusinessRecord, created["id"])
            self.assertEqual(stored.data["deadline"], str(deadline))
            self.assertEqual(stored.data["end_date"], str(end))
            self.assertEqual(stored.status, "待接收")
            self.assertEqual((await db.get(BusinessRecord, self.parent_id)).description, "完整调查说明")
        await self.request("supervisor", "POST", f"/investigations/{self.parent_id}/tasks", 422, json={**payload, "deadline": str(date.today()-timedelta(days=1))})
        await self.request("supervisor", "POST", f"/investigations/{self.parent_id}/tasks", 422, json={**payload, "start_date": str(end+timedelta(days=1))})
        with self.assertRaises(HTTPException):
            _validate_task_deadline(deadline)
        (EVIDENCE / "tasks" / "api-results.json").write_text(json.dumps(self.results, ensure_ascii=False, indent=2), encoding="utf-8")

    async def asyncTearDown(self):
        await self.client.aclose()
        async with SessionLocal() as db:
            paths = (await db.scalars(select(FileAttachment.path))).all()
        for value in paths:
            path = Path(value).resolve()
            self.assertTrue(path.is_relative_to(self.uploads.resolve()))
            path.unlink(missing_ok=True)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        for file in self.uploads.glob(f"{self.prefix}-*.docx"):
            file.unlink()
        async with SessionLocal() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(FileAttachment)), 0)
        await engine.dispose()


if __name__ == "__main__":
    unittest.main(verbosity=2)

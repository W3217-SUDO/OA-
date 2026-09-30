"""9.30 合同调查、主管待分配队列及多区域子任务的隔离 API 验证。"""

import asyncio
import json
import os
from datetime import date, timedelta
from pathlib import Path
import unittest

EVIDENCE = Path(os.environ["OA_BATCH_EVIDENCE"]).resolve() / "row5-7-api"
EVIDENCE.mkdir(parents=True, exist_ok=True)
DATABASE = EVIDENCE / "isolated.db"
if DATABASE.exists():
    raise RuntimeError("隔离测试数据库必须不存在")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DATABASE.as_posix()}"
os.environ["UPLOAD_ROOT"] = str(EVIDENCE / "uploads")
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["DINGTALK_NOTIFICATIONS_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "isolated-930-investigation-test-key"

import httpx
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import BusinessRecord, LegacyInvestigationTask, RolePermission, SystemConfig, User
from app.security import create_token


class Investigation930ContractTaskApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.prefix = "CODEX-930-INVESTIGATION"
        self.results = []
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with SessionLocal() as db:
            users = [
                ("publisher", "user"),
                ("supervisor", "user"),
                ("assignee", "user"),
                ("second", "user"),
                ("outsider", "user"),
                ("admin", "admin"),
            ]
            db.add_all([
                User(
                    username=f"{self.prefix}-{name}", display_name=name,
                    department="调查部", password_hash="isolated-test", role=role,
                    role_ids=[], is_active=True,
                ) for name, role in users
            ])
            db.add(RolePermission(
                role="user", display_name="调查人员", data_scope="本人及共享数据",
                menu_keys=["investigation-task-unassigned", "investigation-task-sub-mine", "investigation-task-published"],
                field_keys=[],
            ))
            db.add(SystemConfig(
                key="investigation_assignment", label="调查主管",
                value={"supervisor_username": f"{self.prefix}-supervisor"},
            ))
            contract = BusinessRecord(
                module="contract", serial_no=f"{self.prefix}-HT", title="调查合同",
                customer=f"{self.prefix}客户", status="审批通过",
                owner=f"{self.prefix}-publisher", department="调查部", data={},
            )
            db.add(contract)
            await db.flush()
            self.contract_id = contract.id
            historical = BusinessRecord(
                module="investigation", serial_no=f"{self.prefix}-HIST", title="既有已分配调查",
                customer=contract.customer, status="进行中", owner=f"{self.prefix}-assignee",
                department="调查部", data={
                    "contract_id": contract.id, "contract_no": contract.serial_no,
                    "publisher": f"{self.prefix}-publisher",
                    "assigner": f"{self.prefix}-supervisor",
                    "authorization_scope": "全国",
                    "authorized_to": str(date.today() + timedelta(days=30)),
                },
            )
            db.add(historical)
            await db.flush()
            self.historical_id = historical.id
            await db.commit()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://isolated-930.test",
        )

    async def request(self, name, method, path, expected=200, **kwargs):
        role = "admin" if name == "admin" else "user"
        headers = {
            "Authorization": f"Bearer {create_token(f'{self.prefix}-{name}', role)}",
            "X-Page-Key": "investigation-task-unassigned",
        }
        response = await self.client.request(method, f"/api/v1{path}", headers=headers, **kwargs)
        self.assertEqual(response.status_code, expected, response.text[:800])
        self.results.append({"actor": name, "method": method, "path": path, "status": expected})
        return response.json()

    async def test_contract_repeat_assignment_and_multi_region(self):
        today = date.today()
        create_body = {
            "title": "同名调查任务", "owner": f"{self.prefix}-supervisor",
            "authorized_from": str(today), "authorized_to": str(today + timedelta(days=30)),
            "region": "全国", "authorization_scope": "全国", "right_type": "商标",
        }
        first = await self.request("publisher", "POST", f"/contracts/{self.contract_id}/investigation", 201, json=create_body)
        second = await self.request("publisher", "POST", f"/contracts/{self.contract_id}/investigation", 201, json=create_body)
        self.assertNotEqual(first["serial_no"], second["serial_no"])
        self.assertRegex(first["serial_no"], r"^DC\d{8}S\d{9}$")
        self.assertEqual(len(first["serial_no"]), 20)
        self.assertEqual(int(first["serial_no"][-9:]), first["id"])
        self.assertEqual(int(second["serial_no"][-9:]), second["id"])
        self.assertLess(first["serial_no"], second["serial_no"])
        self.assertEqual(first["data"]["auditor"], f"{self.prefix}-supervisor")

        before = await self.request("supervisor", "GET", "/records?module=investigation&scope=mine&investigation_view=unassigned")
        self.assertEqual({item["id"] for item in before["items"]}, {first["id"], second["id"], self.historical_id})
        await self.request("supervisor", "POST", f"/investigations/{first['id']}/assign", json={"investigator": f"{self.prefix}-assignee"})
        after = await self.request("supervisor", "GET", "/records?module=investigation&scope=mine&investigation_view=unassigned")
        self.assertEqual({item["id"] for item in after["items"]}, {first["id"], second["id"], self.historical_id})
        outsider = await self.request("outsider", "GET", "/records?module=investigation&scope=mine&investigation_view=unassigned")
        self.assertEqual(outsider["total"], 0)
        await self.request("outsider", "POST", f"/investigations/{first['id']}/assign", 403, json={
            "investigator": f"{self.prefix}-outsider",
        })

        task_body = {
            "title": "多地调查", "owner": f"{self.prefix}-assignee",
            "deadline": str(today + timedelta(days=10)),
            "investigation_regions": [["上海市", "市辖区"], ["江苏省", "南京市"]],
        }
        task = await self.request("supervisor", "POST", f"/investigations/{first['id']}/tasks", 201, json=task_body)
        self.assertEqual(task["data"]["investigation_regions"], task_body["investigation_regions"])
        self.assertEqual(task["data"]["region"], "上海市 市辖区、江苏省 南京市")
        children = await self.request("supervisor", "GET", f"/investigations/{first['id']}/tasks")
        self.assertEqual({item["id"] for item in children["items"]}, {task["id"]})
        await self.request("outsider", "GET", f"/investigations/{first['id']}/tasks", 404)
        async with SessionLocal() as db:
            persisted = await db.get(BusinessRecord, task["id"])
            self.assertEqual(persisted.data["investigation_regions"], task_body["investigation_regions"])
            legacy = await db.scalar(select(LegacyInvestigationTask).where(
                LegacyInvestigationTask.TaskNo == task["serial_no"],
            ))
            self.assertEqual(legacy.Province, "上海市,江苏省")
            self.assertEqual(legacy.City, "市辖区,南京市")
            linked = await db.get(BusinessRecord, self.contract_id)
            self.assertEqual(set(linked.data["investigation_ids"]), {first["id"], second["id"]})
        await self.request("supervisor", "POST", f"/investigations/{first['id']}/tasks", 422, json={
            **task_body, "investigation_regions": [["上海市", "南京市"]],
        })
        await self.request("supervisor", "POST", f"/investigations/{first['id']}/tasks", 422, json={
            **task_body, "investigation_regions": [["上海市", "市辖区"], ["上海市", "市辖区"]],
        })
        await self.request("supervisor", "POST", f"/investigations/{first['id']}/tasks", 422, json={
            **task_body, "investigation_regions": [["江苏省"], ["江苏省", "南京市"]],
        })
        await self.request("outsider", "POST", f"/investigations/{first['id']}/tasks", 403, json=task_body)
        await self.request("supervisor", "POST", f"/investigations/{self.historical_id}/tasks", 201, json=task_body)

        async with SessionLocal() as db:
            regional = await db.get(BusinessRecord, second["id"])
            regional.data = {
                **regional.data, "authorization_scope_type": "R",
                "authorization_scope": "江苏省南京市",
                "authorization_regions": [["江苏省", "南京市"]],
            }
            await db.commit()
        await self.request("supervisor", "POST", f"/investigations/{second['id']}/tasks", 422, json=task_body)
        await self.request("supervisor", "POST", f"/investigations/{second['id']}/tasks", 422, json={
            **task_body, "investigation_regions": [["江苏省"]],
        })
        regional_task = await self.request("supervisor", "POST", f"/investigations/{second['id']}/tasks", 201, json={
            **task_body, "investigation_regions": [["江苏省", "南京市"]],
        })
        self.assertEqual(regional_task["data"]["investigation_regions"], [["江苏省", "南京市"]])

        async with SessionLocal() as db:
            old = await db.get(BusinessRecord, first["id"])
            old.data = {**old.data, "authorized_to": str(today - timedelta(days=1))}
            await db.commit()
        await self.request("supervisor", "POST", f"/investigations/{first['id']}/tasks", 409, json=task_body)
        headers = {
            "Authorization": f"Bearer {create_token(f'{self.prefix}-publisher', 'user')}",
            "X-Page-Key": "investigation-task-unassigned",
        }
        responses = await asyncio.gather(*(
            self.client.post(
                f"/api/v1/contracts/{self.contract_id}/investigation",
                headers=headers, json=create_body,
            ) for _ in range(4)
        ), return_exceptions=True)
        self.assertTrue(all(isinstance(response, httpx.Response) for response in responses), responses)
        self.assertEqual([response.status_code for response in responses], [201] * 4)
        self.results.extend({
            "actor": "publisher", "method": "POST", "path": f"/contracts/{self.contract_id}/investigation",
            "status": response.status_code, "concurrent": True,
        } for response in responses)
        concurrent = sorted((response.json() for response in responses), key=lambda item: item["id"])
        serials = [item["serial_no"] for item in concurrent]
        self.assertEqual(len(set(serials)), 4)
        self.assertEqual(serials, sorted(serials))
        self.assertEqual([int(serial[-9:]) for serial in serials], [item["id"] for item in concurrent])
        async with SessionLocal() as db:
            linked = await db.get(BusinessRecord, self.contract_id)
            self.assertEqual(set(linked.data["investigation_ids"]), {
                first["id"], second["id"], *(item["id"] for item in concurrent),
            })
            self.assertEqual(linked.data["last_investigation_no"], concurrent[-1]["serial_no"])
        EVIDENCE.joinpath("api-results.json").write_text(json.dumps(self.results, ensure_ascii=False, indent=2), encoding="utf-8")

    async def asyncTearDown(self):
        await self.client.aclose()
        await engine.dispose()
        DATABASE.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

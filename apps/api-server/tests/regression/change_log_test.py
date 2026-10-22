"""变更留痕：新增、修改（含 JSON 键差异）、update 语句、删除、恢复都记前后值、操作人、来源；可还原并检测冲突。"""
import unittest

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import change_log, soft_delete
from app.database import Base
from app.models import BusinessRecord, DataChangeLog, Department, Notification, SecurityPolicy, WorkflowEvent


class ChangeLogTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        soft_delete.set_actor("tester")
        self.source = change_log.set_source("mcp")

    async def asyncTearDown(self):
        change_log.source_var.reset(self.source)
        await self.engine.dispose()

    async def _logs(self, db, **filters):
        statement = select(DataChangeLog).order_by(DataChangeLog.id)
        for key, value in filters.items():
            statement = statement.where(getattr(DataChangeLog, key) == value)
        return (await db.scalars(statement)).all()

    async def test_insert_update_delete_restore_are_logged_with_actor_and_source(self):
        async with self.sessions() as db:
            department = Department(code="LOG-1", name="留痕部门")
            db.add(department)
            await db.commit()
            department.name = "留痕部门-改"
            await db.commit()
            await db.delete(department)
            await db.commit()
            await db.run_sync(lambda sync: soft_delete.restore_rows(sync, "departments", [department.id]))
            await db.commit()
            logs = await self._logs(db, table_name="departments", row_id=str(department.id))
        self.assertEqual([log.action for log in logs], ["insert", "update", "delete", "restore"])
        self.assertEqual(logs[1].changes, {"name": ["留痕部门", "留痕部门-改"]})
        self.assertTrue(all(log.actor == "tester" and log.source == "mcp" for log in logs))
        self.assertEqual(logs[0].summary, "留痕部门")

    async def test_json_columns_record_only_changed_keys_and_revert_restores_them(self):
        async with self.sessions() as db:
            record = BusinessRecord(module="case", serial_no="J-LOG", title="案件", data={"a": 1, "b": 2, "big": "x" * 1000})
            db.add(record)
            await db.commit()
            record_id = record.id
            record.data = {**record.data, "a": 9, "c": 3}
            record.data.pop("b")
            await db.commit()
            log = (await self._logs(db, table_name="business_records", action="update"))[0]
            self.assertEqual(log.changes, {"data": {"__json__": {"a": [1, 9], "b": [2, change_log.ABSENT], "c": [change_log.ABSENT, 3]}}})
            log_id = log.id
            await change_log.revert(db, log_id, "admin")
            db.expire_all()
            fresh = await db.get(BusinessRecord, record_id)
            self.assertEqual(fresh.data, {"a": 1, "b": 2, "big": "x" * 1000})
            reverted = await db.get(DataChangeLog, log_id)
            self.assertEqual(reverted.reverted_by, "admin")
            follow = (await self._logs(db, revert_of=log_id))
            self.assertEqual(len(follow), 1)  # 还原本身也留痕
            self.assertEqual(follow[0].source, "web")

    async def test_update_statement_is_logged_and_revert_detects_later_changes(self):
        async with self.sessions() as db:
            db.add(Department(code="ST-1", name="一"))
            await db.commit()
            await db.execute(update(Department).where(Department.code == "ST-1").values(name="二"))
            await db.commit()
            log = (await self._logs(db, table_name="departments", action="update"))[0]
            log_id = log.id
            self.assertEqual(log.changes, {"name": ["一", "二"]})
            await db.execute(update(Department).where(Department.code == "ST-1").values(name="三"))
            await db.commit()
            with self.assertRaises(HTTPException) as caught:
                await change_log.revert(db, log_id, "admin")
            self.assertEqual(caught.exception.status_code, 409)
            await db.rollback()
            await change_log.revert(db, log_id, "admin", force=True)
            db.expire_all()
            self.assertEqual((await db.scalars(select(Department.name))).all(), ["一"])

    async def test_revert_of_insert_deletes_and_revert_of_delete_restores(self):
        async with self.sessions() as db:
            db.add(Department(code="R-1", name="新增"))
            await db.commit()
            insert_log = (await self._logs(db, table_name="departments", action="insert"))[0]
            await change_log.revert(db, insert_log.id, "admin")
            self.assertEqual((await db.scalars(select(Department))).all(), [])
            delete_log = (await self._logs(db, table_name="departments", action="delete"))[0]
            await change_log.revert(db, delete_log.id, "admin")
            self.assertEqual([d.code for d in (await db.scalars(select(Department))).all()], ["R-1"])
            with self.assertRaises(HTTPException):
                await change_log.revert(db, delete_log.id, "admin")  # 不能重复还原

    async def test_bulk_delete_statement_and_append_only_logs(self):
        async with self.sessions() as db:
            db.add_all([Department(code="B-1", name="甲"), Department(code="B-2", name="乙")])
            record = BusinessRecord(module="case", serial_no="W-1", title="t")
            db.add(record)
            await db.flush()
            db.add(WorkflowEvent(record_id=record.id, action="x", operator="u"))
            await db.commit()
            await db.execute(delete(Department).where(Department.code.like("B-%")))
            await db.commit()
            self.assertEqual(len(await self._logs(db, table_name="departments", action="delete")), 2)
            self.assertEqual(await self._logs(db, table_name="workflow_events"), [])  # 追加型日志表不重复留痕

    async def test_technical_tables_are_logged_too_and_hard_deletes_keep_a_full_row(self):
        async with self.sessions() as db:
            policy = SecurityPolicy()
            db.add(policy)
            await db.commit()
            policy_id, old_length = policy.id, policy.min_password_length
            policy.min_password_length = old_length + 4
            await db.commit()
            await db.delete(policy)
            await db.commit()
            logs = await self._logs(db, table_name="security_policies", row_id=str(policy_id))
            self.assertEqual([log.action for log in logs], ["insert", "update", "delete"])
            self.assertEqual(logs[1].changes["min_password_length"], [old_length, old_length + 4])
            self.assertEqual(logs[2].changes["__row__"]["min_password_length"], old_length + 4)  # 真删除前整行存档
            await change_log.revert(db, logs[2].id, "admin")  # 按存档插回
            db.expire_all()
            back = await db.get(SecurityPolicy, policy_id)
            self.assertEqual(back.min_password_length, old_length + 4)

    async def test_core_delete_and_insert_statements_on_technical_tables(self):
        from sqlalchemy import insert as sql_insert
        async with self.sessions() as db:
            await db.execute(sql_insert(Notification), [{"source_key": f"n{i}", "source_type": "task", "sender": "s", "recipient": "u", "notification_type": "系统通知", "title": "t", "content": "c"} for i in range(3)])
            await db.commit()
            await db.execute(delete(Notification).where(Notification.source_key == "n1"))
            await db.commit()
            logs = await self._logs(db, table_name="notifications")
            self.assertEqual([log.action for log in logs], ["insert", "delete"])
            self.assertIn("__bulk__", logs[0].changes)
            self.assertEqual(logs[1].changes["__row__"]["source_key"], "n1")

    async def test_skip_change_log_for_maintenance(self):
        async with self.sessions() as db:
            db.info["skip_change_log"] = True
            db.add(Department(code="S-1", name="维护"))
            await db.commit()
            self.assertEqual(await self._logs(db), [])


if __name__ == "__main__":
    unittest.main()

"""逻辑删除：删除只做标记，查询自动过滤，编号可重用，级联同步，可恢复，技术表仍可物理删除。"""
import unittest

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import soft_delete
from app.database import Base
from app.models import (BusinessRecord, Department, FileAttachment, Notification, SecurityPolicy, Warehouse,
                        WarehouseStorageLocation)


class SoftDeleteTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        soft_delete.set_actor("tester")

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _raw(self, db, model, **filters):
        """绕过自动过滤，直接看库里有没有这一行。"""
        statement = select(model).execution_options(include_deleted=True)
        for key, value in filters.items():
            statement = statement.where(getattr(model, key) == value)
        return (await db.scalars(statement)).all()

    def test_columns_and_exclusions(self):
        tables = soft_delete.soft_tables()
        self.assertIn("departments", tables)
        self.assertIn("deleted_at", Department.__table__.c)
        for name in ("notifications", "security_policies", "mcp_access_tokens", "party_library"):
            self.assertNotIn(name, tables)
        self.assertNotIn("deleted_at", Notification.__table__.c)
        self.assertFalse([name for name in tables if name.startswith("legacy_")])

    async def test_session_delete_marks_row_and_hides_it(self):
        async with self.sessions() as db:
            department = Department(code="D1", name="一部")
            db.add(department)
            await db.commit()
            await db.delete(department)
            await db.commit()
            self.assertEqual((await db.scalars(select(Department))).all(), [])
            self.assertEqual(await db.scalar(select(func.count()).select_from(Department)), 0)
            self.assertIsNone(await db.get(Department, department.id))
            rows = await self._raw(db, Department, code="D1")
            self.assertEqual(len(rows), 1)
            self.assertIsNotNone(rows[0].deleted_at)
            self.assertEqual(rows[0].deleted_by, "tester")

    async def test_delete_statement_is_rewritten_and_reports_rowcount(self):
        async with self.sessions() as db:
            db.add_all([Department(code="A", name="甲"), Department(code="B", name="乙")])
            await db.commit()
            result = await db.execute(delete(Department).where(Department.code == "A"))
            await db.commit()
            self.assertEqual(result.rowcount, 1)
            self.assertEqual([d.code for d in (await db.scalars(select(Department))).all()], ["B"])
            self.assertEqual(len(await self._raw(db, Department)), 2)
            again = await db.execute(delete(Department).where(Department.code == "A"))
            self.assertEqual(again.rowcount, 0)  # 已删除的不会再被命中

    async def test_deleted_object_leaves_identity_map_after_statement_delete(self):
        async with self.sessions() as db:
            db.add(Department(code="M", name="内存对象"))
            await db.commit()
            department = (await db.scalars(select(Department))).one()
            await db.execute(delete(Department).where(Department.id == department.id))
            self.assertIsNone(await db.get(Department, department.id))  # 不能再从身份映射里拿到已删除对象

    async def test_unique_code_can_be_reused_after_delete_but_not_while_live(self):
        async with self.sessions() as db:
            first = Department(code="DUP", name="重名部门")
            db.add(first)
            await db.commit()
            db.add(Department(code="DUP", name="另一个"))
            with self.assertRaises(IntegrityError):
                await db.commit()
            await db.rollback()
            await db.delete(first)
            await db.commit()
            db.add(Department(code="DUP", name="重名部门"))
            await db.commit()
            self.assertEqual(len(await self._raw(db, Department, code="DUP")), 2)
            self.assertEqual(len((await db.scalars(select(Department))).all()), 1)

    async def test_cascade_children_are_marked_and_restored_together(self):
        async with self.sessions() as db:
            record = BusinessRecord(module="case", serial_no="C-1", title="案件")
            db.add(record)
            await db.flush()
            attachment = FileAttachment(record_id=record.id, original_name="a.txt", stored_name="s1", path="/p", uploader="u")
            db.add(attachment)
            await db.commit()
            record_id, attachment_id = record.id, attachment.id
            await db.delete(record)
            await db.commit()
            self.assertEqual((await db.scalars(select(FileAttachment))).all(), [])
            self.assertEqual(len(await self._raw(db, FileAttachment, id=attachment_id)), 1)
            await db.run_sync(lambda sync: soft_delete.restore_rows(sync, "business_records", [record_id]))
            await db.commit()
            self.assertEqual(len((await db.scalars(select(BusinessRecord))).all()), 1)
            self.assertEqual(len((await db.scalars(select(FileAttachment))).all()), 1)

    async def test_restrict_reference_still_blocks_deletion(self):
        async with self.sessions() as db:
            warehouse = Warehouse(warehouse_no="W1", name="仓库")
            db.add(warehouse)
            await db.flush()
            db.add(WarehouseStorageLocation(warehouse_id=warehouse.id, storage_location_no="L1", name="库位"))
            await db.commit()
            await db.delete(warehouse)
            with self.assertRaises(IntegrityError):
                await db.commit()
            await db.rollback()
            self.assertEqual(len((await db.scalars(select(Warehouse))).all()), 1)

    async def test_hard_delete_escape_hatch_and_technical_tables(self):
        async with self.sessions() as db:
            db.add(Department(code="H", name="硬删"))
            await db.commit()
            db.info["hard_delete"] = True
            await db.execute(delete(Department).where(Department.code == "H"))
            await db.commit()
            db.info.pop("hard_delete")
            self.assertEqual(len(await self._raw(db, Department, code="H")), 0)  # 真的没了

    async def test_deleting_a_soft_object_with_orm_relationship_session_stays_usable(self):
        async with self.sessions() as db:
            db.add(Department(code="R", name="关系"))
            await db.commit()
            department = (await db.scalars(select(Department))).one()
            await db.delete(department)
            await db.commit()
            db.add(Department(code="R2", name="继续使用同一个会话"))
            await db.commit()
            self.assertEqual([d.code for d in (await db.scalars(select(Department))).all()], ["R2"])

    async def test_joins_subqueries_columns_and_updates_ignore_deleted_rows(self):
        async with self.sessions() as db:
            record = BusinessRecord(module="case", serial_no="J-1", title="联接案件")
            gone = BusinessRecord(module="case", serial_no="J-2", title="已删案件")
            db.add_all([record, gone])
            await db.flush()
            db.add_all([FileAttachment(record_id=record.id, original_name="a", stored_name="j1", path="/1", uploader="u"),
                        FileAttachment(record_id=gone.id, original_name="b", stored_name="j2", path="/2", uploader="u")])
            await db.commit()
            gone_id = gone.id
            await db.delete(gone)
            await db.commit()
            joined = (await db.execute(select(BusinessRecord.serial_no, FileAttachment.original_name)
                                       .join(FileAttachment, FileAttachment.record_id == BusinessRecord.id))).all()
            self.assertEqual(joined, [("J-1", "a")])
            self.assertEqual((await db.scalars(select(BusinessRecord.serial_no))).all(), ["J-1"])
            with_files = select(BusinessRecord.serial_no).where(exists().where(FileAttachment.record_id == BusinessRecord.id))
            self.assertEqual((await db.scalars(with_files)).all(), ["J-1"])
            result = await db.execute(update(BusinessRecord).where(BusinessRecord.id == gone_id).values(title="不该被改"))
            self.assertEqual(result.rowcount, 0)
            raw = await self._raw(db, BusinessRecord, id=gone_id)
            self.assertEqual(raw[0].title, "已删案件")

    async def test_bulk_delete_cascades_and_restore_reports_conflict(self):
        async with self.sessions() as db:
            first = BusinessRecord(module="case", serial_no="B-1", title="一")
            second = BusinessRecord(module="case", serial_no="B-2", title="二")
            db.add_all([first, second])
            await db.flush()
            db.add_all([FileAttachment(record_id=first.id, original_name="x", stored_name="b1", path="/b1", uploader="u"),
                        FileAttachment(record_id=second.id, original_name="y", stored_name="b2", path="/b2", uploader="u")])
            await db.commit()
            first_id = first.id
            result = await db.execute(delete(BusinessRecord).where(BusinessRecord.module == "case"))
            await db.commit()
            self.assertEqual(result.rowcount, 2)
            self.assertEqual((await db.scalars(select(FileAttachment))).all(), [])
            db.add(BusinessRecord(module="case", serial_no="B-1", title="同编号的新案件"))
            await db.commit()
            with self.assertRaises(IntegrityError):
                await db.run_sync(lambda sync: soft_delete.restore_rows(sync, "business_records", [first_id]))
                await db.commit()
            await db.rollback()

    async def test_technical_tables_keep_physical_delete(self):
        async with self.sessions() as db:
            db.add(SecurityPolicy())
            await db.commit()
            await db.execute(delete(SecurityPolicy))
            await db.commit()
            self.assertEqual((await db.scalars(select(SecurityPolicy))).all(), [])
            self.assertEqual(await db.scalar(select(func.count()).select_from(SecurityPolicy.__table__)), 0)


if __name__ == "__main__":
    unittest.main()

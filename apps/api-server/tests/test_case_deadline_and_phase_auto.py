"""陶威 11-02 同意：案件期限按未完成任务现算；民事案件每天凌晨自动改阶段（旧系统 P_Legal_Case_AutoUpdate）。"""
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import BusinessRecord, SystemConfig, SystemParameter, WorkflowEvent

BEIJING = timezone(timedelta(hours=8))


class CaseDeadlineAndPhaseAutoTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_deadline_is_earliest_open_task_of_anyone_else_one_year(self):
        from app.core.case_list_tasks import case_deadlines
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(id=1, module="case", serial_no="AJ1", title="有任务", status="文书准备", owner="a", data={"deadline": "2030-01-01"}),
                BusinessRecord(id=2, module="case", serial_no="AJ2", title="没任务", status="文书准备", owner="a", data={}),
                BusinessRecord(id=11, module="task", serial_no="RW11", title="别人的", status="待处理", owner="someone", data={"case_id": 1, "deadline": "2026-11-20"}),
                BusinessRecord(id=12, module="task", serial_no="RW12", title="更早", status="处理中", owner="b", data={"case_no": "AJ1", "deadline": "2026-11-10 09:00"}),
                BusinessRecord(id=13, module="task", serial_no="RW13", title="已作废", status="已取消", owner="b", data={"case_id": 1, "deadline": "2026-11-01"}),
                BusinessRecord(id=14, module="task", serial_no="RW14", title="已完成", status="已完成", owner="b", data={"case_id": 1, "deadline": "2026-11-02"}),
                BusinessRecord(id=15, module="task", serial_no="RW15", title="无效", status="待处理", owner="b", data={"case_id": 1, "deadline": "2026-11-03", "is_active": False}),
                BusinessRecord(id=16, module="task", serial_no="RW16", title="2号已完成", status="已完成", owner="b", data={"case_id": 2, "deadline": "2026-11-04"}),
            ])
            await db.commit()
            result = await case_deadlines([{"id": 1, "serial_no": "AJ1"}, {"id": 2, "serial_no": "AJ2"}], db)
        today = datetime.now(BEIJING).date()
        self.assertEqual(result[1], "2026-11-10")
        self.assertEqual(result[2], today.replace(year=today.year + 1).isoformat())

    async def test_civil_phase_rules_run_once_per_day(self):
        from app.core.case_phase_auto import apply_civil_case_phase_rules
        now = datetime(2026, 11, 3, 0, 40, tzinfo=BEIJING)
        async with self.sessions() as db:
            # 和生产一样：系统参数 id 另编，code 是旧阶段号；另有同名的内置阶段（11-03 生产按参数 id 查不到，整轮失败）。
            db.add(SystemParameter(id=74, category="case_phase", code="FIRST_POST_HEARING", name="一审庭后待判", is_active=True, extra={"case_type": "民事争议"}))
            for param_id, code, name in ((172, "101018", "一审庭后待判"), (185, "102016", "二审庭后待判"),
                                         (195, "103014", "再审庭后待判"), (164, "101010", "新案待分配"), (160, "101002", "新案")):
                db.add(SystemParameter(id=param_id, category="case_phase", code=code, name=name, is_active=True, extra={"case_type": "民事争议"}))
            civil = {"case_type_id": "110", "case_type": "民事争议"}
            db.add_all([
                BusinessRecord(id=1, module="case", serial_no="AJ1", title="一审到期", status="一审已立案", owner="a",
                               data={**civil, "case_phase_id": 101005, "first_instance_lawful_day": "2026-11-03T09:00:00"}),
                BusinessRecord(id=2, module="case", serial_no="AJ2", title="二审到期", status="二审已立案", owner="a",
                               data={**civil, "case_phase_id": 102003, "second_instance_lawful_day": "2026-11-03"}),
                BusinessRecord(id=3, module="case", serial_no="AJ3", title="新案满30天", status="新案", owner="a",
                               data={**civil, "case_phase_id": "101002", "phase_changed_at": "2026-10-03T10:00:00+08:00"}),
                BusinessRecord(id=4, module="case", serial_no="AJ4", title="新案未满", status="新案", owner="a",
                               data={**civil, "case_phase_id": "101002", "phase_changed_at": "2026-10-10T10:00:00+08:00"}),
                BusinessRecord(id=5, module="case", serial_no="AJ5", title="刑事不动", status="一审已立案", owner="a",
                               data={"case_type_id": "120", "case_phase_id": 101005, "first_instance_lawful_day": "2026-11-03"}),
                BusinessRecord(id=6, module="case", serial_no="AJ6", title="已在目标阶段", status="一审庭后待判", owner="a",
                               data={**civil, "case_phase_id": 101018, "first_instance_lawful_day": "2026-11-03"}),
                BusinessRecord(id=7, module="case", serial_no="AJ7", title="明天到期", status="一审已立案", owner="a",
                               data={**civil, "case_phase_id": 101005, "first_instance_lawful_day": "2026-11-04"}),
            ])
            await db.commit()
            # 新建时系统会把进入阶段时间记成当下；这里改成真实的进入时间。
            for case_id, entered in ((3, "2026-10-03T10:00:00+08:00"), (4, "2026-10-10T10:00:00+08:00")):
                record = await db.get(BusinessRecord, case_id)
                record.data = {**record.data, "phase_changed_at": entered}
            await db.commit()
            self.assertEqual(await apply_civil_case_phase_rules(db, now=datetime(2026, 11, 3, 0, 10, tzinfo=BEIJING)), 0)
            self.assertEqual(await apply_civil_case_phase_rules(db, now=now), 3)
            await db.commit()
            self.assertEqual(await apply_civil_case_phase_rules(db, now=now + timedelta(hours=1)), 0)
            phases = {record.id: (record.status, record.data["case_phase_id"]) for record in (await db.scalars(select(BusinessRecord))).all()}
            self.assertEqual(phases[1], ("一审庭后待判", 101018))
            self.assertEqual(phases[2], ("二审庭后待判", 102016))
            self.assertEqual(phases[3], ("新案待分配", 101010))
            self.assertEqual((await db.get(BusinessRecord, 1)).data["case_phase_parameter_id"], 172)
            self.assertEqual(int(phases[4][1]), 101002)
            self.assertEqual(phases[5][1], 101005)
            self.assertEqual(phases[7][1], 101005)
            events = (await db.scalars(select(WorkflowEvent))).all()
            self.assertEqual({(event.record_id, event.operator, event.action) for event in events},
                             {(1, "system", "自动修改案件阶段"), (2, "system", "自动修改案件阶段"), (3, "system", "自动修改案件阶段")})
            self.assertEqual((await db.scalar(select(SystemConfig).where(SystemConfig.key == "case_phase_auto_last_run"))).value["changed"], 3)


if __name__ == "__main__":
    unittest.main()

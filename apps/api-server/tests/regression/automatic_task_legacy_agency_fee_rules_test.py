"""Legacy agency-fee completion and completion-only transaction regressions."""

from datetime import date
import unittest

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.tasks import (
    _apply_case_automatic_task_rules, _case_fee_received_amounts,
    _case_has_outstanding_legacy_agency_fee,
)
from app.database import Base
from app.models import BusinessRecord, IncomingPayment, User, WorkflowEvent


class LegacyAgencyFeeAutomaticTaskRulesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="CODEX-AUTO-AGENCY-CASE", title="自动规则案件", customer="同名客户",
                status="一审立案受理", owner="owner", department="测试部", data={"legacy_case_id": 501},
            )
            db.add(case)
            await db.flush()
            self.case_id = case.id
            task = BusinessRecord(
                module="task", serial_no="CODEX-AUTO-AGENCY-TASK", title="催收代理费", customer="同名客户",
                status="处理中", owner="owner", department="测试部",
                data={"case_id": case.id, "auto_task_type": "agency_fee_collection:9001"},
            )
            db.add(task)
            await db.commit()
            self.task_id = task.id

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def add_fee(
        self,
        *,
        fee_type: str,
        amount: float,
        cashed: float = 0,
        active: str = "T",
        case_id: int | None = None,
        legacy_case_id: int = 501,
    ) -> int:
        async with self.sessions() as db:
            fee = BusinessRecord(
                module="finance", serial_no=f"CODEX-FEE-{fee_type}-{amount}", title="代理费", customer="同名客户",
                status="历史数据", owner="owner", department="测试部",
                data={
                    "case_id": self.case_id if case_id is None else case_id,
                    "legacy_case_fee_id": int(fee_type) + int(amount),
                    "legacy_record": {"CaseId": legacy_case_id, "CaseFeeTypeId": fee_type, "Amount": amount, "CashedAmount": cashed, "IsActived": active},
                },
            )
            db.add(fee)
            await db.commit()
            return fee.id

    async def task_status(self) -> str:
        async with self.sessions() as db:
            task = await db.get(BusinessRecord, self.task_id)
            return task.status

    async def test_only_exact_active_agency_fee_balance_controls_completion(self) -> None:
        await self.add_fee(fee_type="11020010", amount=100, cashed=100)
        await self.add_fee(fee_type="11020020", amount=50, cashed=50)
        await self.add_fee(fee_type="11010020", amount=999, cashed=0)
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            fees = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance"))).all())
            self.assertIs(_case_has_outstanding_legacy_agency_fee(case, fees, _case_fee_received_amounts(fees, [])), False)
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 13)), 0)
        self.assertEqual(await self.task_status(), "已完成")

    async def test_unpaid_or_inactive_or_unlinked_fees_do_not_produce_false_completion(self) -> None:
        await self.add_fee(fee_type="11020010", amount=100, cashed=20)
        await self.add_fee(fee_type="11020020", amount=300, cashed=0, active="F")
        await self.add_fee(fee_type="11020030", amount=400, cashed=400, case_id=987654)
        async with self.sessions() as db:
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 13)), 0)
        self.assertEqual(await self.task_status(), "处理中")

    async def test_unlinked_receipt_and_missing_fee_evidence_do_not_complete_task(self) -> None:
        async with self.sessions() as db:
            db.add(IncomingPayment(
                receipt_no="CODEX-UNLINKED-RECEIPT", received_date=date(2026, 8, 1), amount=999,
                payer_name="同名客户", status="已分配", operator="owner",
                allocations=[{"case_id": self.case_id, "case_no": "CODEX-AUTO-AGENCY-CASE", "amount": 999}],
            ))
            await db.commit()
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 13)), 0)
        self.assertEqual(await self.task_status(), "处理中")

    async def test_conflicting_current_case_link_cannot_be_overridden_by_legacy_case_id(self) -> None:
        fee_id = await self.add_fee(fee_type="11020030", amount=100, cashed=100)
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, fee_id)
            fee.data = {**fee.data, "case_record_id": 987654}
            await db.commit()
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 13)), 0)
        self.assertEqual(await self.task_status(), "处理中")

    async def test_case_no_only_legacy_fee_is_a_verified_relation(self) -> None:
        async with self.sessions() as db:
            fee = BusinessRecord(
                module="finance", serial_no="CODEX-CASE-NO-ONLY", title="代理费", customer="同名客户",
                status="历史数据", owner="owner", department="测试部",
                data={
                    "case_no": "CODEX-AUTO-AGENCY-CASE", "legacy_case_fee_id": 11020010,
                    "legacy_record": {"CaseFeeTypeId": 11020010, "Amount": 100, "CashedAmount": 100, "IsActived": "T"},
                },
            )
            db.add(fee)
            await db.commit()
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 13)), 0)
        self.assertEqual(await self.task_status(), "已完成")

    async def test_unknown_amount_or_null_or_nonfinite_cash_evidence_never_counts_as_settled(self) -> None:
        await self.add_fee(fee_type="11020010", amount=100, cashed=0)
        async with self.sessions() as db:
            fee = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "finance"))
            fee.data = {**fee.data, "legacy_record": {**fee.data["legacy_record"], "Amount": None, "CashedAmount": 100}}
            await db.commit()
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 13)), 0)
        self.assertEqual(await self.task_status(), "处理中")
        for invalid_cash in (None, float("nan"), float("inf")):
            async with self.sessions() as db:
                fee = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "finance"))
                fee.data = {**fee.data, "legacy_record": {**fee.data["legacy_record"], "Amount": 100, "CashedAmount": invalid_cash}}
                await db.commit()
                self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 13)), 0)
            self.assertEqual(await self.task_status(), "处理中")

    async def test_completion_only_scan_commits_after_notification_flush_without_active_recipients(self) -> None:
        fee_id = await self.add_fee(fee_type="11020040", amount=120)
        async with self.sessions() as db:
            sibling_task_ids = []
            for index in range(2):
                sibling = BusinessRecord(
                    module="task", serial_no=f"CODEX-LINKED-SIBLING-{index}", title="催收代理费",
                    customer="同名客户", status="处理中", owner="owner", department="测试部",
                    data={"case_id": self.case_id, "auto_task_type": f"agency_fee_collection:sibling-{index}"},
                )
                db.add(sibling)
                await db.flush()
                sibling_task_ids.append(sibling.id)
            db.add(IncomingPayment(
                receipt_no="CODEX-LINKED-RECEIPT", received_date=date(2026, 9, 12), amount=120,
                payer_name="同名客户", status="已分配", operator="owner",
                allocations=[{"case_id": self.case_id, "fee_record_id": fee_id, "amount": 120}],
            ))
            await db.commit()
            payment_selects = []

            def count_payment_selects(connection, cursor, statement, parameters, context, executemany):
                if "FROM incoming_payments" in statement:
                    payment_selects.append(statement)

            event.listen(self.engine.sync_engine, "before_cursor_execute", count_payment_selects)
            try:
                self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 13)), 0)
            finally:
                event.remove(self.engine.sync_engine, "before_cursor_execute", count_payment_selects)
            self.assertEqual(len(payment_selects), 1)
        # No User rows exist in this fixture, so notification lookup flushes the
        # task/event but creates no recipient notification or new task. A
        # separate session must still observe the committed completion.
        async with self.sessions() as db:
            statuses = list((await db.scalars(select(BusinessRecord.status).where(
                BusinessRecord.id.in_([self.task_id, *sibling_task_ids]),
            ).order_by(BusinessRecord.id))).all())
        self.assertEqual(statuses, ["已完成"] * 3)
        async with self.sessions() as db:
            events = list((await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == self.task_id,
            ))).all())
        self.assertEqual([(event.action, event.to_status) for event in events], [("业务状态联动自动完成", "已完成")])

    async def test_existing_document_archive_notary_and_refund_completions_share_scan_commit(self) -> None:
        async with self.sessions() as db:
            db.add(User(
                username="refund-assistant", display_name="退费助理", department="测试部",
                role="user", password_hash="x", is_active=True,
            ))
            cases = []
            for suffix, status in (
                ("DOCUMENT", "一审立案受理"), ("ARCHIVE", "已归档"),
                ("NOTARY", "一审准备开庭"), ("REFUND", "一审准备开庭"),
            ):
                case = BusinessRecord(
                    module="case", serial_no=f"CODEX-COMMIT-{suffix}", title=suffix, customer="提交测试客户",
                status=status, owner="owner", department="测试部", data={},
                )
                db.add(case); cases.append(case)
            await db.flush()
            cases[3].data = {"assistant_username": "refund-assistant"}
            refund = BusinessRecord(
                module="refund", serial_no="CODEX-COMMIT-REFUND-SOURCE", title="退费", customer="提交测试客户",
                status="处理中", owner="owner", department="测试部",
                data={"case_id": cases[3].id, "refund_requested_amount": 100, "refunded_amount": 100},
            )
            db.add(refund)
            await db.flush()
            definitions = (
                (cases[0], "document_preparation_stage"),
                (cases[1], "payment_received_30d_archive"),
                (cases[2], "notary_audit:10"),
                (cases[3], f"refund_application:{refund.id}"),
            )
            tasks = []
            for index, (case, task_type) in enumerate(definitions, start=1):
                task_data = {"case_id": case.id, "auto_task_type": task_type}
                if task_type.startswith("refund_application:"):
                    task_data["trigger_source_id"] = f"refund:{refund.id}"
                task = BusinessRecord(
                    module="task", serial_no=f"CODEX-COMMIT-TASK-{index}", title="既有自动任务",
                    customer="提交测试客户", status="处理中", owner="owner", department="测试部",
                    data=task_data,
                )
                db.add(task); tasks.append(task)
            await db.commit()
            task_ids = [task.id for task in tasks]
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 13)), 0)
        async with self.sessions() as db:
            statuses = list((await db.scalars(select(BusinessRecord.status).where(
                BusinessRecord.id.in_(task_ids),
            ).order_by(BusinessRecord.id))).all())
        self.assertEqual(statuses, ["已完成"] * 4)


if __name__ == "__main__":
    unittest.main()

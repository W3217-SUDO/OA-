"""旧系统同步来的未完成任务（陶威 2026-11-01）：任务列表显示截止日期和逾期，但不进到期提醒、不推钉钉。"""
import unittest
from datetime import date, timedelta

from app.core.tasks import _task_schedule_state
from app.models import BusinessRecord


def task(deadline: str, *, legacy: bool) -> BusinessRecord:
    data = {"source": "案件任务", "deadline": deadline}
    if legacy:
        data.update({"legacy_case_task": True, "legacy_task_id": 1})
    return BusinessRecord(module="task", serial_no="RW-1", title="任务", status="待处理", owner="codexuser", data=data)


class LegacyTaskScheduleTest(unittest.TestCase):
    def test_legacy_task_with_time_shows_deadline_and_overdue_without_reminder(self):
        overdue = (date.today() - timedelta(days=3)).isoformat() + "T18:27:31"
        deadline, days_remaining, status, reminder_due, text = _task_schedule_state(task(overdue, legacy=True))
        self.assertEqual(deadline, date.today() - timedelta(days=3))
        self.assertEqual(days_remaining, -3)
        self.assertEqual(status, "已逾期")
        self.assertFalse(reminder_due)
        self.assertEqual(text, "已逾期 3 天")
        due_soon = (date.today() + timedelta(days=1)).isoformat() + "T09:00:00"
        self.assertFalse(_task_schedule_state(task(due_soon, legacy=True))[3])

    def test_new_task_reminders_unchanged(self):
        overdue = (date.today() - timedelta(days=3)).isoformat()
        deadline, days_remaining, status, reminder_due, text = _task_schedule_state(task(overdue, legacy=False))
        self.assertEqual((days_remaining, status, reminder_due), (-3, "已逾期", True))
        self.assertEqual(text, "已逾期 3 天，今日提醒")
        self.assertTrue(_task_schedule_state(task((date.today() + timedelta(days=1)).isoformat(), legacy=False))[3])
        # 新任务带时分秒也能识别。
        self.assertTrue(_task_schedule_state(task((date.today() + timedelta(days=3)).isoformat() + "T10:00:00", legacy=False))[3])


if __name__ == "__main__":
    unittest.main()

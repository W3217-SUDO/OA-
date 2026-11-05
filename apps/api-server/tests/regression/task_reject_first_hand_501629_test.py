"""501629（tgn 11-05）：照老系统，只有第一手接收、不是自己发给自己的待处理任务可以拒绝。"""
import inspect
import unittest
from types import SimpleNamespace

from app.core.tasks import task_received_by_handoff, task_reject_block_reason


def _task(status="待处理", owner="lisi", **data):
    return SimpleNamespace(status=status, owner=owner, data={"initiator": "zhangsan", **data})


class TaskRejectFirstHand501629Test(unittest.TestCase):
    def test_first_hand_pending_task_can_be_rejected(self):
        self.assertEqual(task_reject_block_reason(_task()), "")
        self.assertEqual(task_reject_block_reason(_task(status="待接收")), "")

    def test_processing_task_cannot_be_rejected(self):
        self.assertEqual(task_reject_block_reason(_task(status="处理中")), "当前状态不能拒绝任务")

    def test_self_sent_task_cannot_be_rejected(self):
        self.assertEqual(task_reject_block_reason(_task(owner="zhangsan")), "自己发给自己的任务不能拒绝")

    def test_handed_over_task_cannot_be_rejected(self):
        self.assertTrue(task_received_by_handoff({"handoff_from": "wangwu", "received_by_handoff": True}))
        self.assertTrue(task_received_by_handoff({"handoff_from": "wangwu"}))  # 旧数据
        self.assertIn("转交来的任务不能拒绝", task_reject_block_reason(_task(handoff_from="wangwu", received_by_handoff=True)))

    def test_resent_task_is_first_hand_again(self):
        self.assertFalse(task_received_by_handoff({"handoff_from": "lisi", "resent_at": "2026-11-05T22:00:00"}))
        self.assertFalse(task_received_by_handoff({"handoff_from": "lisi", "received_by_handoff": False}))
        self.assertEqual(task_reject_block_reason(_task(handoff_from="wangwu", received_by_handoff=False)), "")

    def test_router_enforces_rule_and_marks_handoffs(self):
        from app.areas.tp import router

        self.assertIn("task_reject_block_reason(task)", inspect.getsource(router.reject_task))
        self.assertIn('"received_by_handoff": True', inspect.getsource(router.handoff_task))
        self.assertIn('"received_by_handoff": False', inspect.getsource(router.resend_task))


if __name__ == "__main__":
    unittest.main()

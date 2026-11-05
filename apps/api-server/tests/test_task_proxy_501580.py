"""501580（tgn 11-05 选 A）：真管理员或有“公司接受的任务”页面且勾了“批量修改任务”的人可代办别人任务；页面临时提升的 admin 不算。"""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.core.task_lifecycle_policy import task_actor_identity


def run(identity, payload):
    with patch("app.core.permissions._permission_payload_for_identity", AsyncMock(return_value=payload)):
        return asyncio.run(task_actor_identity(identity, None))


class TaskProxy501580Test(unittest.TestCase):
    def test_actual_admin_can_act_for_others(self):
        identity = {"username": "tgn", "role": "admin", "role_ids": ["admin"], "_actual_role": "admin", "_actual_role_ids": ["admin"]}
        self.assertEqual(run(identity, {})["role"], "admin")

    def test_role_with_company_page_and_batch_update_can_proxy(self):
        identity = {"username": "a", "role": "admin", "role_ids": ["admin", "user"], "_actual_role": "user", "_actual_role_ids": ["user"]}
        result = run(identity, {"menu_keys": ["task-company-accepted"], "action_keys": ["task.batch.update"]})
        self.assertEqual((result["role"], result.get("_task_proxy")), ("admin", True))

    def test_page_elevated_user_without_permission_cannot_proxy(self):
        identity = {"username": "b", "role": "admin", "role_ids": ["admin", "user"], "_actual_role": "user", "_actual_role_ids": ["user"]}
        self.assertNotEqual(run(identity, {"menu_keys": ["task-company-accepted"], "action_keys": ["task.complete"]})["role"], "admin")
        self.assertNotEqual(run(identity, {"menu_keys": ["task-my-accepted"], "action_keys": ["task.batch.update"]})["role"], "admin")


if __name__ == "__main__":
    unittest.main()

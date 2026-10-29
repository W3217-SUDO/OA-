"""不认识的个人动作只忽略不 409（2026-10-29 shenhe 因数据先于代码写入而登录不了）。"""
import unittest

from app.agent_permissions import AGENT_GLOBAL_MANAGE_ACTION, personal_action_keys


class PersonalActionKeysTolerantTest(unittest.TestCase):
    def test_unknown_personal_action_is_ignored(self):
        keys = personal_action_keys({"action_keys": [AGENT_GLOBAL_MANAGE_ACTION, "finance.future.only", AGENT_GLOBAL_MANAGE_ACTION, 3]})
        self.assertEqual(keys, [AGENT_GLOBAL_MANAGE_ACTION])

    def test_malformed_personal_actions_are_empty(self):
        self.assertEqual(personal_action_keys({"action_keys": "agent.settings.global.manage"}), [])
        self.assertEqual(personal_action_keys({}), [])


if __name__ == "__main__":
    unittest.main()

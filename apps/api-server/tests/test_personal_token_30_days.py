"""陶威 11-03 11:33 定：电脑连接 OA 的个人访问令牌有效期上限 30 天（原 90 天）。"""
import unittest

from pydantic import ValidationError

from app.agent_mcp import personal_tokens
from app.agent_mcp.router import AccessTokenInput


class PersonalToken30DaysTest(unittest.TestCase):
    def test_cap_is_30_days_on_service_and_api_input(self):
        self.assertEqual(personal_tokens.MAX_DAYS, 30)
        self.assertEqual(AccessTokenInput(name="笔记本", days=30).days, 30)
        with self.assertRaises(ValidationError):
            AccessTokenInput(name="笔记本", days=31)
        with self.assertRaises(ValidationError):
            AccessTokenInput(name="笔记本", days=90)


if __name__ == "__main__":
    unittest.main()

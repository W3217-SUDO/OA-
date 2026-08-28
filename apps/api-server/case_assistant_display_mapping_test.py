import unittest

from app.main import _apply_record_person_displays, _record_dict
from app.models import BusinessRecord, User


class CaseAssistantDisplayMappingTest(unittest.TestCase):
    def test_legacy_assistant_uses_stable_username_for_chinese_display_name(self):
        record = BusinessRecord(
            id=40503,
            module="case",
            serial_no="GDMS2400008",
            title="历史案件",
            customer="历史客户",
            status="一审立案受理",
            owner="admin",
            department="诉讼部",
            data={
                "assistant": "田明远",
                "assistant_username": "tianmingyuan",
                "legacy_record": {
                    "CaseAssistant": "tianmingyuan",
                    "CaseAssistantName": "田明远",
                },
            },
        )
        assistant = User(
            username="tianmingyuan",
            display_name="田明远",
            password_hash="unused",
            role="user",
            department="诉讼部",
            is_active=True,
            profile={},
        )

        result = _apply_record_person_displays(
            _record_dict(record), record, {assistant.username: assistant},
        )

        self.assertEqual(result["data"]["assistant_display_name"], "田明远")
        self.assertFalse(result["data"]["assistant_display_name_missing"])
        self.assertEqual(result["data"]["assistant_username_display_name"], "田明远")

    def test_current_case_without_assistant_username_keeps_resolvable_account_value(self):
        record = BusinessRecord(
            id=1,
            module="case",
            serial_no="CODEX-828-ASSISTANT",
            title="当前案件",
            customer="测试客户",
            status="文书准备",
            owner="admin",
            department="诉讼部",
            data={"assistant": "assistant01"},
        )
        assistant = User(
            username="assistant01",
            display_name="英文姓名也可见 Alice",
            password_hash="unused",
            role="user",
            department="诉讼部",
            is_active=True,
            profile={},
        )

        result = _apply_record_person_displays(
            _record_dict(record), record, {assistant.username: assistant},
        )

        self.assertEqual(result["data"]["assistant_display_name"], "英文姓名也可见 Alice")
        self.assertFalse(result["data"]["assistant_display_name_missing"])


if __name__ == "__main__":
    unittest.main()

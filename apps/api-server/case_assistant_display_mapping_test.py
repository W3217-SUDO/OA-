import unittest

from app.main import (
    PERSON_NAME_PLACEHOLDER,
    _apply_record_person_displays,
    _record_dict,
    _record_person_usernames,
)
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

    def test_legacy_chinese_name_without_username_is_preserved(self):
        record = BusinessRecord(
            id=40454,
            module="case",
            serial_no="SHMS2600371",
            title="历史民事案件",
            customer="历史客户",
            status="二审",
            owner="admin",
            department="诉讼部",
            data={"assistant": "朱淑旖", "assistant_username": ""},
        )

        result = _apply_record_person_displays(_record_dict(record), record, {})

        self.assertEqual(result["data"]["assistant_display_name"], "朱淑旖")
        self.assertNotEqual(result["data"]["assistant_display_name"], PERSON_NAME_PLACEHOLDER)
        self.assertFalse(result["data"]["assistant_display_name_missing"])

    def test_unresolvable_legacy_accounts_fall_back_to_parallel_name_list(self):
        record = BusinessRecord(
            id=2,
            module="case",
            serial_no="CODEX-828-MULTI-ASSISTANT",
            title="历史多人助理案件",
            customer="历史客户",
            status="文书准备",
            owner="admin",
            department="诉讼部",
            data={
                "assistant": "赵雪,吴立跃",
                "assistant_username": "zhaoxue,wuliyue",
            },
        )

        result = _apply_record_person_displays(_record_dict(record), record, {})

        self.assertEqual(result["data"]["assistant_display_name"], "赵雪、吴立跃")
        self.assertEqual(result["data"]["assistant_username_display_name"], "赵雪、吴立跃")
        self.assertFalse(result["data"]["assistant_display_name_missing"])
        self.assertNotIn(PERSON_NAME_PLACEHOLDER, str(result["data"]))

    def test_multi_assistant_usernames_are_loaded_individually(self):
        record = BusinessRecord(
            id=3,
            module="case",
            serial_no="CODEX-828-MULTI-LOOKUP",
            title="当前多人助理案件",
            customer="测试客户",
            status="文书准备",
            owner="admin",
            department="诉讼部",
            data={
                "assistant": "赵雪,吴立跃",
                "assistant_username": "zhaoxue,wuliyue",
            },
        )

        self.assertTrue({"zhaoxue", "wuliyue"}.issubset(_record_person_usernames(record)))

    def test_case_without_assistant_uses_dash_without_missing_placeholder(self):
        record = BusinessRecord(
            id=4,
            module="case",
            serial_no="CODEX-828-NO-ASSISTANT",
            title="无助理案件",
            customer="测试客户",
            status="文书准备",
            owner="admin",
            department="诉讼部",
            data={"assistant": "", "assistant_username": ""},
        )

        result = _apply_record_person_displays(_record_dict(record), record, {})

        self.assertEqual(result["data"]["assistant_display_name"], "—")
        self.assertFalse(result["data"]["assistant_display_name_missing"])


if __name__ == "__main__":
    unittest.main()

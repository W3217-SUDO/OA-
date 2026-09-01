from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("app") / "main.py"


class HrDisplayNameSelfEditRow9Test(unittest.TestCase):
    def test_uniqueness_excludes_current_employee_and_linked_user(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def _require_unique_hr_display_name")
        end = source.index('@app.get(f"{settings.api_prefix}/hr/employees")', start)
        branch = source[start:end]
        self.assertIn("BusinessRecord.id != employee_id", branch)
        self.assertIn("User.username != linked_username.strip().lower()", branch)

    def test_only_exact_normalized_names_conflict_and_other_people_still_block(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def _require_unique_hr_display_name")
        end = source.index('@app.get(f"{settings.api_prefix}/hr/employees")', start)
        branch = source[start:end]
        self.assertIn("func.lower(func.trim(BusinessRecord.title)) == name_key", branch)
        self.assertIn("func.lower(func.trim(User.display_name)) == name_key", branch)
        self.assertNotIn("ilike", branch)
        self.assertEqual(branch.count('detail="中文姓名已存在"'), 2)


    def test_account_only_employee_update_uses_the_same_uniqueness_gate(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def update_system_user(")
        end = source.index('@app.get(f"{settings.api_prefix}/system/users/{{user_id}}/permissions")', start)
        branch = source[start:end]
        self.assertIn("await _require_unique_hr_display_name(", branch)
        self.assertIn("linked_username=user.username", branch)


if __name__ == "__main__":
    unittest.main()

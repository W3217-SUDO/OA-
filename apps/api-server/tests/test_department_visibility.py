"""BUG20261031002 第③步：本部门数据 = 本部门 + 自己名下/自己负责的下级部门（含再往下各级）。"""
import unittest
from types import SimpleNamespace

from app.core.department_visibility import visible_department_names_from


def dept(id, name, parent=None, owner="", manager=""):
    return SimpleNamespace(id=id, name=name, parent_department_id=parent, owner_username=owner, manager=manager)


DEPARTMENTS = [
    dept(1, "诉讼一部", manager="boss"),
    dept(2, "A组", parent=1, owner="zhang"),
    dept(3, "A组-甲", parent=2, owner="wang"),
    dept(4, "B组", parent=1, owner="li"),
    dept(5, "诉讼二部"),
]


class DepartmentVisibilityTest(unittest.TestCase):
    def test_member_without_subordinates_sees_only_own_department(self):
        self.assertEqual(visible_department_names_from(DEPARTMENTS, "zhao", "诉讼一部"), {"诉讼一部"})

    def test_owner_sees_own_branch_but_not_colleagues_branch(self):
        self.assertEqual(visible_department_names_from(DEPARTMENTS, "ZHANG", "诉讼一部"), {"诉讼一部", "A组", "A组-甲"})

    def test_lower_owner_sees_only_below(self):
        self.assertEqual(visible_department_names_from(DEPARTMENTS, "wang", "A组"), {"A组", "A组-甲"})

    def test_manager_sees_whole_tree(self):
        self.assertEqual(visible_department_names_from(DEPARTMENTS, "boss", "诉讼一部"), {"诉讼一部", "A组", "A组-甲", "B组"})

    def test_child_without_owner_follows_parent(self):
        departments = [*DEPARTMENTS, dept(6, "C组", parent=1), dept(7, "C组-乙", parent=6, owner="sun")]
        self.assertEqual(visible_department_names_from(departments, "zhao", "诉讼一部"), {"诉讼一部", "C组"})

    def test_cycle_does_not_loop(self):
        looped = [dept(1, "甲", parent=2, owner="x"), dept(2, "乙", parent=1)]
        self.assertEqual(visible_department_names_from(looped, "x", ""), {"甲", "乙"})


if __name__ == "__main__":
    unittest.main()

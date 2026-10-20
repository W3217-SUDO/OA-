"""部门案件范围：PostgreSQL 上合并成一条正则的数组成员条件，必须与原逐人 LIKE '%"用户名"%' 完全等价。"""

from __future__ import annotations

import re
import unittest

from app.core.case_department_scope import _like_regex


def like_matches(text: str, pattern: str) -> bool:
    """按 PostgreSQL LIKE 语义（% 任意串、_ 单字符、\\ 转义）判断 text 是否匹配 pattern。"""
    regex, index = [], 0
    while index < len(pattern):
        char = pattern[index]
        if char == "\\" and index + 1 < len(pattern):
            index += 1
            regex.append(re.escape(pattern[index]))
        elif char == "%":
            regex.append(".*")
        elif char == "_":
            regex.append(".")
        else:
            regex.append(re.escape(char))
        index += 1
    return re.fullmatch("".join(regex), text, re.DOTALL) is not None


class DepartmentScopeRegexTest(unittest.TestCase):
    def test_combined_regex_equals_per_user_like(self):
        usernames = {"zhangsan", "li_si", "wang%wu", "a.b", "c\\_d", "(x)", "张三"}
        documents = [
            '["zhangsan"]', '["zhangsanfeng"]', '["lixsi"]', '["li_si", "other"]', '["wangABCwu"]',
            '["a.b"]', '["aXb"]', '["c_d"]', '["cXd"]', '["(x)"]', '["张三"]', '"zhangsan"', '[]', '',
            '[{"name": "zhangsan"}]', '["ZHANGSAN"]',
        ]
        combined = re.compile('"(' + "|".join(_like_regex(name) for name in sorted(usernames)) + ')"', re.DOTALL)
        for document in documents:
            with self.subTest(document=document):
                expected = any(like_matches(document, f'%"{name}"%') for name in usernames)
                self.assertEqual(combined.search(document) is not None, expected)

    def test_regex_special_characters_are_literal(self):
        self.assertEqual(_like_regex("a.b(c)[d]{e}|f^g$h*i+j?k"), r"a\.b\(c\)\[d\]\{e\}\|f\^g\$h\*i\+j\?k")
        self.assertEqual(_like_regex("x%y_z"), "x.*y.z")
        self.assertEqual(_like_regex("p\\%q\\_r"), "p%q_r")


if __name__ == "__main__":
    unittest.main()

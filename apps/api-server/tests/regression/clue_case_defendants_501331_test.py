"""501331（fwl 11-04）：已取证线索生成案件时，线索主体信息带成案件被告，证件号格式对才带。"""

import unittest

from app.areas.investigation.router import clue_defendants


class ClueCaseDefendantsTest(unittest.TestCase):
    def test_indictees_become_defendants_with_valid_identities(self):
        names, identities = clue_defendants({"indictees": [
            {"name": "4353", "nature": "个人", "identity_no": "5435345"},
            {"name": "郑州君学留商贸有限公司", "nature_code": "E", "identity_no": "91410100makktrgh48"},
            {"name": "郑州君学留商贸有限公司", "nature": "企业"},
            {"name": "张三", "nature": "个人", "identity_no": "11010119900307123X"},
        ], "opponent": "旧对方"})
        self.assertEqual(names, ["4353", "郑州君学留商贸有限公司", "张三"])
        self.assertEqual(identities, [
            {"name": "郑州君学留商贸有限公司", "organization_type": "公司企业", "identity_no": "91410100MAKKTRGH48"},
            {"name": "张三", "organization_type": "个人", "identity_no": "11010119900307123X"},
        ])

    def test_falls_back_to_opponent(self):
        self.assertEqual(clue_defendants({"indictees": [], "opponent": "甲公司、乙公司"}), (["甲公司", "乙公司"], []))
        self.assertEqual(clue_defendants({}), ([], []))


if __name__ == "__main__":
    unittest.main()

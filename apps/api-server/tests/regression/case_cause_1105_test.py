"""陶国南 11-05 13:10：所有模板统一取案由：案件 → 当前审级法院信息 → 旧系统 → 按权利类型推定。"""

import unittest

from app.core.case_cause import case_cause, case_cause_with_source


class CaseCauseTest(unittest.TestCase):
    def test_order(self):
        self.assertEqual(case_cause_with_source({"cause_or_charge": "十五、不正当竞争纠纷"}), ("不正当竞争纠纷", "案件"))
        self.assertEqual(case_cause_with_source({"second_court_cause": "侵害著作权纠纷", "first_court_cause": "甲"}, "二审审理中"), ("侵害著作权纠纷", "法院信息"))
        self.assertEqual(case_cause_with_source({"legacy_record": {"CauseName": "侵害商标权纠纷"}}), ("侵害商标权纠纷", "旧系统"))
        self.assertEqual(case_cause_with_source({"case_type": "民事争议", "case_right_type_id": "110010", "legacy_record": {"CauseName": None}}),
                         ("侵害商标权纠纷", "按权利类型推定"))

    def test_no_inference_outside_civil_or_when_disabled(self):
        self.assertEqual(case_cause({"case_type": "法律顾问", "case_right_type_id": "110010"}), "")
        self.assertEqual(case_cause({"case_type": "民事争议", "case_right_type_id": "110010"}, infer=False), "")
        self.assertEqual(case_cause({"cause_or_charge": "null"}), "")


if __name__ == "__main__":
    unittest.main()

"""501189（陶国南 11-03 10:18）：案件智能体按案件实际类型和案由选手册，合同纠纷不再套用知识产权手册。"""
import unittest
from datetime import date

from app.case_workflow_rules import build_case_workflow_guide, case_kind


def guide_for(cause, documents=()):
    return build_case_workflow_guide({"case": {"status": "新案待分配", "data": {"case_type": "民事争议", "cause_or_charge": cause}},
                                      "documents": list(documents)}, reference_date=date(2026, 11, 3))


class CaseManualByCauseTest(unittest.TestCase):
    def test_contract_dispute_uses_contract_flow_and_materials(self):
        guide = guide_for("买卖合同纠纷", [{"name": "买卖合同.pdf"}, {"name": "增值税发票.pdf"}])
        self.assertEqual(guide["manual"]["name"], "合同纠纷案件办案流程")
        self.assertEqual(guide["manual"]["case_kind"], "合同纠纷")
        self.assertEqual(guide["manual"]["cause"], "买卖合同纠纷")
        codes = {item["code"]: item for item in guide["materials"]}
        self.assertEqual(codes["contract"]["status"], "uploaded")
        self.assertEqual(codes["performance"]["status"], "uploaded")
        self.assertNotIn("知识产权", guide["manual"]["name"])
        self.assertFalse(any("公证书" in str(item) for item in guide["materials"]))

    def test_ip_disputes_keep_the_ip_manual(self):
        for cause in ("侵害商标权纠纷", "侵害作品信息网络传播权纠纷", "侵害外观设计专利权纠纷", "十五、不正当竞争纠纷"):
            self.assertEqual(guide_for(cause)["manual"]["name"], "知识产权案件标准化操作手册", cause)

    def test_kind_by_cause(self):
        cases = {"民间借贷纠纷": "contract", "建设工程施工合同纠纷": "contract", "十、合同纠纷": "contract",
                 "劳动合同纠纷": "civil", "十七、劳动争议": "civil", "离婚纠纷": "civil", "机动车交通事故责任纠纷": "civil",
                 "": "civil", None: "civil"}
        for cause, kind in cases.items():
            self.assertEqual(case_kind({"data": {"cause_or_charge": cause}}), kind, cause)
        self.assertEqual(guide_for("离婚纠纷")["manual"]["name"], "民商事诉讼案件通用办案流程")

    def test_missing_cause_uses_general_flow_and_asks_to_confirm(self):
        """思法汇成 11-03 10:47：案由没填的，提醒确认案由，否则适用通用诉讼流程。"""
        manual = guide_for("")["manual"]
        self.assertEqual(manual["name"], "民商事诉讼案件通用办案流程")
        self.assertTrue(manual["cause_missing"])
        self.assertIn("确认并补填案由", manual["notice"])
        self.assertNotIn("cause_missing", guide_for("买卖合同纠纷")["manual"])


if __name__ == "__main__":
    unittest.main()

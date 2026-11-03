"""501226：尽调报告风险部分——火山企业风险库和企查查 736 整理成同一结构；重复公示只算一条；欠税取最新余额；按终本、失信、破产判断执行风险。"""

import unittest
from types import SimpleNamespace

from app.areas.legal import case_parties, party_risk

JUDICIAL = (
    "主键(id),企业被执行案件id(company_executed_id),企业被执行情况信息明细(company_executed_content_details),"
    "终本案件id(end_execution_case_id),终本案件情况信息明细(end_execution_case_content_detail),立案案件id(filing_id),立案企业涉案角色名称(filing_party_role_name),"
    "立案时间(filing_filing_time),立案法院(filing_court),立案案由(filing_case_reason),立案原告(filing_plaintiff)\n"
    '1,e1,"{""executed_start_date"":""2026-10-22"",""executed_court"":""通州法院"",""executed_amount"":100000.0}",,,,,,,,\n'
    '2,e2,"{""executed_start_date"":""2026-10-22"",""executed_court"":""通州法院"",""executed_amount"":100000.0}",,,,,,,,\n'
    '3,,,t1,"{""end_execution_case_filing_date"":""2025-01-21 08:00:00"",""end_execution_end_date"":""2025-12-31 08:00:00"",""end_execution_court"":""通州法院"",""end_execution_enforcement_target"":""962368.3"",""end_execution_unfulfilled_amount"":""580344.72""}",,,,,,\n'
    '4,,,,,f1,被告,2025-06-09 08:00:00,通州法院,借款合同纠纷,"[{""name"": ""某银行""}, {""name"": ""甲公司""}]"\n'
)
RISKS = (
    "主键(id),风险类型标记(risk_type),更新标志(is_delete),发布日期(own_tax_publish_date),欠税税种(own_tax_tax_category),欠税金额(own_tax_amount),欠税余额(own_tax_balance)\n"
    "r1,own_tax,0,2025-10-31,增值税,2284603.05,2284603.05\n"
    "r2,own_tax,0,2025-10-23,增值税,2284603.05,2284603.05\n"
    "r3,own_tax,0,2025-07-18,增值税,2284696.78,2284696.78\n"
)
SUMMARY = {"企业名称": "甲公司", "统一社会信用代码": "91320612MA24U8T39J", "是否有失信记录，1有，0无": "0", "是否有欠税记录，1有，0无": "1"}


class PartyRiskTest(unittest.TestCase):
    def risk(self):
        return party_risk.normalize_volc(SUMMARY, party_risk.csv_rows(JUDICIAL), party_risk.csv_rows(RISKS), queried_at="2026-11-03T16:30:00")

    def test_volc_normalize_dedupes_and_latest_tax(self):
        sections = self.risk()["sections"]
        self.assertEqual(sections["executed"]["count"], 1, "同一案件重复公示只算一条")
        self.assertEqual(sections["own_tax"]["count"], 2)
        self.assertEqual(sections["own_tax"]["amount"], 2284603.05, "欠税取最新余额，不累加")
        self.assertEqual(sections["end_execution"]["amount"], 580344.72)
        self.assertEqual(sections["filing"]["items"][0]["other"], "某银行", "对方去掉本企业")

    def test_enforceability(self):
        conclusion, reasons = party_risk.enforceability(self.risk())
        self.assertIn("执行风险高：已有终本记录", conclusion)
        self.assertTrue(any("最新欠税余额 228.46 万元" in reason for reason in reasons))
        clean, reasons = party_risk.enforceability({"sections": {}, "flags": {}})
        self.assertIn("执行风险较低", clean)
        self.assertEqual(reasons, [])

    def test_qcc736_same_structure(self):
        risk = party_risk.normalize_qcc736({"Name": "甲公司", "ShiXinItems": [{"Liandate": "2025-01-01", "Anno": "(2025)苏0612执1号", "Executegov": "通州法院"}],
                                            "Partners": [{"StockName": "乙", "StockPercent": "60%"}]}, queried_at="2026-11-03")
        self.assertEqual(risk["sections"]["dishonest"]["count"], 1)
        self.assertIn("失信", party_risk.enforceability(risk)[0])
        self.assertEqual(risk["sections"]["partners"]["items"][0]["name"], "乙")

    def test_report_with_and_without_risk(self):
        from io import BytesIO
        from docx import Document

        def text(content):
            document = Document(BytesIO(content))
            return "\n".join([p.text for p in document.paragraphs] + [c.text for t in document.tables for r in t.rows for c in r.cells])

        record = SimpleNamespace(serial_no="HZMS1", title="测试")
        detail = {"name": "甲公司", "credit_code": "91320612MA24U8T39J", "status": "存续", "queried_at": "2026-11-03"}
        full = text(case_parties.render_party_docx(record, "甲公司", "被告", "due_diligence", detail, self.risk()))
        self.assertIn("胜诉后能不能执行到：执行风险高", full)
        self.assertIn("终结本次执行：1 条", full)
        self.assertIn("火山方舟专业数据集", full)
        self.assertNotIn("失信被执行人\n", full.split("本报告未核查的事项")[-1], "火山覆盖的类目不再列为未核查")
        bare = text(case_parties.render_party_docx(record, "甲公司", "被告", "due_diligence", detail))
        self.assertIn("风险扫描接口未开通", bare)
        self.assertIn("失信被执行人", bare.split("本报告未核查的事项")[-1])


if __name__ == "__main__":
    unittest.main()

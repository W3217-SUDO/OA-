"""501601（高勤兰 11-05）：专利年费各搜索框按包含匹配，去掉空格（全角半角）、不分大小写后比较。"""
import unittest
from datetime import date

from app.areas.ipr import annual_fee_monitor as monitor


def row(**values):
    base = {"applicant": "", "customer": "", "case_source": "", "case_type": "", "writer": "", "serial_no": "", "application_no": "",
            "case_phase": "", "procurator": "", "application_date": date(2016, 1, 1)}
    return {**base, **values}


class AnnualFeeSearchTest(unittest.TestCase):
    def test_partial_spaces_and_case(self):
        rows = [row(applicant="上海海迅 机电工程有限公司", serial_no="HDPU1600401", application_no="2016 2 0123456.7"),
                row(applicant="望江县鸦滩镇陈运华商店", serial_no="SHPI1810773", application_no="201810000001.1")]
        search = lambda **f: [r["serial_no"] for r in monitor._filter_rows(rows, f, None, None)]
        self.assertEqual(search(applicant="海迅"), ["HDPU1600401"])
        self.assertEqual(search(applicant="海迅机电"), ["HDPU1600401"], "名称里的空格不影响")
        self.assertEqual(search(applicant="海　迅 "), ["HDPU1600401"], "搜索词里的全角/半角空格不影响")
        self.assertEqual(search(case_no="201620123456"), ["HDPU1600401"], "申请号去掉空格比较")
        self.assertEqual(search(case_no="hdpu16"), ["HDPU1600401"], "字母不分大小写")
        self.assertEqual(search(applicant="海讯"), [], "错别字搜不到")
        self.assertEqual(search(applicant="   "), ["HDPU1600401", "SHPI1810773"], "只有空格等于没填")


if __name__ == "__main__":
    unittest.main()

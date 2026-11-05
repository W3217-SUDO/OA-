"""280146（高勤兰 11-05 14:02）：Word 年费清单里三个金额前后留白一样、带下划线，句末中文句号。"""
import io
import unittest

import docx

from app.areas.ipr import annual_fee_monitor as monitor
from app.areas.ipr.annual_fee_notice_template import annual_fee_notice_template


class WordAmountSentenceTest(unittest.TestCase):
    def test_even_amounts(self):
        document = docx.Document(io.BytesIO(annual_fee_notice_template()))
        paragraphs = list(document.paragraphs) + [p for t in document.tables for r in t.rows for c in r.cells for p in c.paragraphs]
        monitor._even_amount_sentence(paragraphs)
        target = next(p for p in paragraphs if "$2" in p.text)
        monitor._fill_placeholders(target, {"$2": "3600", "$3": "300", "$4": "3900"})
        pad = "　　"
        self.assertEqual(target.text, f"贵方此次应支付我方费用应缴年费合计为：{pad}3600{pad}元；年费手续费为100元/项，合计为：{pad}300{pad}元；总计为：{pad}3900{pad}元。")
        underlined = [run.text for run in target.runs if run.underline]
        self.assertEqual(underlined, [f"{pad}3600{pad}", f"{pad}300{pad}", f"{pad}3900{pad}"])


if __name__ == "__main__":
    unittest.main()

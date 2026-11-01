"""陶威 11-01 同意 A2：整部法律确认一次后自动逐条取完，到末尾自动停，上限 300 条。"""
import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.areas.capability_market import remote_full_law as full_law


def article(n):
    return SimpleNamespace(is_error=False, structured_content={
        "lawTitle": "中华人民共和国数据安全法", "articleLabel": f"第{n}条", "content": f"第{n}条　内容{n}",
        "documentNo": "主席令第84号", "timeliness": "现行有效", "implementDate": "2021-09-01",
        "citation": {"url": f"https://www.pkulaw.com/chl/x.html?way=mcp#tiao_{n}"}})


EMPTY = SimpleNamespace(is_error=False, structured_content={"content": None, "citation": {}})


class FakeSession:
    def __init__(self, total):
        self.total, self.calls = total, []

    async def call_tool(self, name, arguments):
        self.calls.append(int(arguments["articleNumber"]))
        number = int(arguments["articleNumber"])
        return article(number) if number <= self.total else EMPTY


class FullLawFetchTest(unittest.IsolatedAsyncioTestCase):
    async def test_stops_after_the_last_article(self):
        session = FakeSession(55)
        articles, calls, complete = await full_law.fetch_articles(session, "数据安全法", full_law.planned_calls(55))
        self.assertEqual(len(articles), 55)
        self.assertTrue(complete)
        self.assertLessEqual(calls, 64)  # 最多多取一批（8 次）用来确认到了末尾
        self.assertEqual([a["label"] for a in articles[:2]], ["第1条", "第2条"])

    async def test_limit_reached_is_reported_incomplete(self):
        session = FakeSession(500)
        articles, calls, complete = await full_law.fetch_articles(session, "某法", full_law.planned_calls(300))
        self.assertEqual((len(articles), calls, complete), (300, 300, False))

    async def test_unknown_law_and_remote_error(self):
        with self.assertRaises(HTTPException) as caught:
            await full_law.fetch_articles(FakeSession(0), "不存在的法", 10)
        self.assertEqual(caught.exception.status_code, 404)

        class Broken(FakeSession):
            async def call_tool(self, name, arguments):
                return SimpleNamespace(is_error=True, structured_content=None)
        with self.assertRaises(HTTPException):
            await full_law.fetch_articles(Broken(5), "某法", 10)

    def test_plan_and_word_text(self):
        self.assertEqual(full_law.planned_calls(55), 58)
        self.assertEqual(full_law.planned_calls(400 - 100), 300)
        for bad in (0, -1, True, "55"):
            with self.assertRaises(HTTPException):
                full_law.planned_calls(bad)
        self.assertIn("最多调用 58 次", full_law.plan_summary("数据安全法", 58, 25))
        self.assertIn("最多约 1450 积分", full_law.plan_summary("数据安全法", 58, 25))
        self.assertIn("以北大法宝控制台为准", full_law.plan_summary("数据安全法", 58, None))
        title, text = full_law.law_markdown([full_law._article(article(1)),
                                             full_law._article(article(2))], True)
        self.assertEqual(title, "中华人民共和国数据安全法")
        self.assertIn("第1条　内容1", text)
        self.assertIn("来源：北大法宝（https://www.pkulaw.com/chl/x.html?way=mcp）", text)


if __name__ == "__main__":
    unittest.main()

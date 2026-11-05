// 501613：知识产权中心“我的案件”——剩余天数和查询参数。
import assert from "node:assert/strict";
import test from "node:test";
import dayjs from "dayjs";

const { remainingDays, myCaseQueryParams, IPR_MY_CASE_GROUPS } = await import("../src/ipr/myCases.ts");

test("剩余天数：截止日减今天，过期显示已过期，没有截止日留空", () => {
  const today = dayjs("2026-11-05");
  assert.equal(remainingDays("2026-11-15T00:00:00", today), "10");
  assert.equal(remainingDays("2026-11-05", today), "0");
  assert.equal(remainingDays("2026-11-01", today), "已过期");
  assert.equal(remainingDays("", today), "");
});

test("分组和筛选参数：前五组去掉失效，只看非诉，空的筛选不带", () => {
  assert.deepEqual(IPR_MY_CASE_GROUPS.map((item) => item.label), ["案件管理人", "我是案源人", "我是代理人", "我是撰稿人", "我的案件", "失效案件"]);
  assert.deepEqual(myCaseQueryParams("my:mine", { applicant: " 甲公司 ", customer: "", application_dates: [dayjs("2026-01-01"), null] }),
    { role_view: "my:mine", case_category: "non_litigation", applicant: "甲公司", date_from: "2026-01-01" });
});

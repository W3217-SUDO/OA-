// 501368（陶国南 11-04 17:27）：企业信息查询页可以生成/重新生成并查看企业基本信息表、尽职调查报告。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("../src/crm/CompanyLibraryPage.tsx", import.meta.url), "utf8");

test("每条企业记录可以生成和查看两种文档", () => {
  assert.match(page, /api\.post\("\/company-library\/documents", \{ keyword: companyKey\(company\), kind \}\)/);
  assert.match(page, /api\.get\("\/company-library\/documents", \{ params: \{ keyword: companyKey\(company\) \} \}\)/);
  assert.match(page, /\{versions\.length \? "重新生成" : "生成"\}/);
  assert.match(page, /"企业基本信息表" : "尽职调查报告"/);
  assert.match(page, /信息表\/尽调报告/);
});

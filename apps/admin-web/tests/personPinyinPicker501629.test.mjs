// 501629（tgn 11-05）：任务选人只能从在职人员里选；选人框支持拼音首字母。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const component = read("../src/components/KeywordPersonSelect.tsx");
const helper = component.slice(component.indexOf("// pinyin-helpers:start"), component.indexOf("// pinyin-helpers:end"));
const { outputText } = ts.transpileModule(helper, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2019 } });
const { pinyinInitials, personKeywordMatches } = await import(`data:text/javascript,${encodeURIComponent(outputText)}`);

test("姓名转拼音首字母", () => {
  assert.equal(pinyinInitials("曹亚迪"), "cyd");
  assert.equal(pinyinInitials("陶国南"), "tgn");
  assert.equal(pinyinInitials("范文玲"), "fwl");
  assert.equal(pinyinInitials("思法汇成"), "sfhc");
  assert.equal(pinyinInitials("吕布"), "lb");
  assert.equal(pinyinInitials("重庆渝富律师事务所"), "cqyflssws");
  assert.equal(pinyinInitials("曾小明"), "zxm");
});

test("选人框匹配：姓名、账号包含，或拼音首字母", () => {
  assert.equal(personKeywordMatches("cyd", "曹亚迪", "caoyadi"), true);
  assert.equal(personKeywordMatches("yd", "曹亚迪", "caoyadi"), true);
  assert.equal(personKeywordMatches("caoya", "曹亚迪", "caoyadi"), true);
  assert.equal(personKeywordMatches("亚迪", "曹亚迪", "caoyadi"), true);
  assert.equal(personKeywordMatches("tgn", "思法汇成", "tgn"), true);
  assert.equal(personKeywordMatches("xyz", "曹亚迪", "caoyadi"), false);
  assert.equal(personKeywordMatches("", "曹亚迪", "caoyadi"), true);
});

test("公用选人框用 personKeywordMatches，提示写明拼音首字母", () => {
  assert.match(component, /personKeywordMatches\(input, option\?\.label, option\?\.value\)/);
  assert.match(component, /请输入姓名、拼音首字母、账号或部门关键词/);
});

test("批量转交接收人、重新派发新负责人、查询条件负责人都是选人框", () => {
  const modals = read("../src/tp/TaskActionModals.tsx");
  const list = read("../src/tp/TaskList.tsx");
  const page = read("../src/tp/TaskCenterPage.tsx");
  assert.match(modals, /label="新负责人"[\s\S]{0,200}<KeywordPersonSelect/);
  assert.match(modals, /taskBatchAction === "handoff"[\s\S]{0,300}<KeywordPersonSelect/);
  assert.match(list, /<Form\.Item label="负责人" name="owner">[\s\S]{0,120}<KeywordPersonSelect/);
  assert.match(page, /owner_username: nextQuery\.owner \|\| ""/);
  assert.match(page, /if \(query\.owner && row\.owner !== query\.owner\) return false;/);
});

test("任务中心不再有 VIP任务 页面，案件详情客户任务仍可标记 VIP", () => {
  const app = read("../src/App.tsx");
  const caseCenter = read("../src/legal/CaseCenterPage.tsx");
  assert.doesNotMatch(app, /route === "vip-tasks"/);
  assert.doesNotMatch(app, /import\("\.\/VipTaskCenterPage"\)/);
  assert.match(app, /item\.key !== "vip-tasks"/);
  assert.match(caseCenter, /<Checkbox>标记为VIP任务<\/Checkbox>/);
});

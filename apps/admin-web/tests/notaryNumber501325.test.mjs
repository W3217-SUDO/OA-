// 501325（fwl 11-04）：选好公证处后按模板填公证书号，年份按取证日期，编号留 xxxxx 给调查员补。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import ts from "typescript";

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const code = ts.transpileModule(read("investigation/notaryNumber.ts"), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const { fillNotaryNumber, hasNotaryPlaceholder } = await import(`data:text/javascript,${encodeURIComponent(code)}`);

test("旧系统和新系统两种模板都能填好年份，编号留 xxxxx", () => {
  assert.equal(fillNotaryNumber("(yyyy)沪徐证经字第xxxxx号", 2026), "(2026)沪徐证经字第xxxxx号");
  assert.equal(fillNotaryNumber("（{year}）沪东证经字第{serial}号", 2026), "（2026）沪东证经字第xxxxx号");
  assert.equal(fillNotaryNumber("（yyyy）厦海证民字第××××号", 2027), "（2027）厦海证民字第xxxxx号");
  assert.equal(fillNotaryNumber("（2025）桂陆证字第3360号", 2026), "（2026）桂陆证字第xxxxx号");
  assert.equal(fillNotaryNumber("", 2026), "");
});

test("还留着 xxxxx 时不能保存，补完编号就可以", () => {
  assert.equal(hasNotaryPlaceholder("(2026)沪徐证经字第xxxxx号"), true);
  assert.equal(hasNotaryPlaceholder("(2026)沪徐证经字第12345号"), false);
  assert.equal(hasNotaryPlaceholder(""), false);
});

test("取证弹窗选机构、改日期时自动填，不覆盖手填的；提交前检查占位", () => {
  const modal = read("investigation/CollectionModal.tsx");
  assert.match(modal, /if \("notary_institution" in changed \|\| "collected_at" in changed\) fillNotaryFromTemplate\(all\);/);
  assert.match(modal, /if \(!current \|\| current === autoFilled\.current\)/);
  assert.match(modal, /请把公证书号里的 xxxxx 换成实际编号/);
  assert.match(read("investigation/hooks/useInvestigationBootstrap.ts"), /template: String\(item\.number_template \|\| ""\)\.trim\(\)/);
});

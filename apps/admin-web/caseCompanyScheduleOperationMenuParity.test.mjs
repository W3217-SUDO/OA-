import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("./src/case-center.css", import.meta.url), "utf8");

const readArrayFactory = (name) => {
  const match = source.match(new RegExp(`export const ${name} = \\(\\) => (\\[[\\s\\S]*?\\]);`));
  assert.ok(match, `${name} should be declared`);
  return new Function(`return (${match[1]});`)();
};

test("case detail primary operation menu follows the legacy order", () => {
  assert.deepEqual(readArrayFactory("getLegacyCaseDetailPrimaryOperationLabels"), [
    "修改基本信息",
    "修改案件阶段",
    "修改公证信息",
    "修改开庭律师",
    "修改当事人",
    "修改法院信息",
    "修改诉讼或判决金额",
    "申请归档",
    "更多操作",
  ]);
});

test("legacy more-operation submenu opens to the left", () => {
  assert.deepEqual(readArrayFactory("getLegacyCaseDetailMoreOperationLabels"), [
    "生成授权委托书",
    "生成一审所函(我方原告)",
    "生成一审所函(我方被告)",
    "生成二审所函(我方上诉)",
    "生成二审所函(对方上诉)",
    "生成执行所函",
    "生成身份证明",
    "案件合并",
    "复制案件",
  ]);
  assert.match(source, /placement="bottomRight"/);
  assert.match(source, /data-testid="case-detail-more-operation-panel"/);
  assert.match(css, /\.case-detail-legacy-submenu-panel\{[^}]*right:calc\(100% - 1px\)/);
  assert.match(css, /\.case-detail-legacy-submenu:hover>\.case-detail-legacy-submenu-panel/);
});

test("every row-13 document entry calls its distinct backend type and reveals the persisted folder", () => {
  assert.match(source, /counselDetailCapabilities\.can_generate_document && !detailEditLocked/);
  assert.doesNotMatch(source, /counselDetailCapabilities\.can_write && !detailEditLocked && <>\s*<Button type="text" block onClick=\{\(\) => void generateCaseDocument/);
  for (const documentType of [
    "authorization-letter",
    "first-instance-appellant-lawyer-letter",
    "first-instance-appellee-lawyer-letter",
    "second-instance-appellant-lawyer-letter",
    "second-instance-appellee-lawyer-letter",
    "execution-lawyer-letter",
    "identity-certificate",
  ]) {
    assert.match(source, new RegExp(`generateCaseDocument\\("${documentType}"\\)`));
  }
  assert.match(source, /message\.success\(`\$\{data\.original_name \|\| "案件文书"\}已生成并归入案件附件`\)/);
  assert.match(source, /const targetCategory = String\(data\.category \|\| "案件文档全部"\)/);
  assert.match(source, /setActiveCounselDocCategory\(targetCategory\)/);
});

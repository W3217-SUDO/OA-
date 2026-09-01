import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { filterCaseFileTypesForCaseType } from "./src/caseRelationConsumption.mjs";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("document toolbar exposes every legacy generation operation", () => {
  for (const label of [
    "生成归档封面", "生成授权委托书", "生成一审所函(我方原告)", "生成一审所函(我方被告)",
    "生成二审所函(我方上诉)", "生成二审所函(对方上诉)", "生成执行所函", "生成身份证明",
    "生成结算提成表", "生成代收代付赔偿款申请单",
  ]) assert.ok(source.includes(label), label);
  assert.match(source, />生成操作<\/Button>/);
});

test("more operations expose delete, seal and document-folder move", () => {
  assert.match(source, /key:"delete",label:"删除"/);
  assert.match(source, /key:"seal",label:"申请用印"/);
  assert.match(source, /key:"move",label:"更改文档目录"/);
  assert.match(source, /cases\/\$\{viewingCounselCase\.id\}\/attachments\/move/);
});

test("delete continues through the atomic case attachment endpoint", () => {
  assert.match(source, /api\.post\("\/cases\/attachments\/delete"/);
  assert.doesNotMatch(source, /<Button danger onClick=\{deleteCounselAttachments\}>删除选中<\/Button>/);
});

test("an empty relation configuration keeps the complete document catalog available", () => {
  const catalog = [
    { id: 1, code: "SUBJECT", name: "主体及委托资料" },
    { id: 2, code: "COURT", name: "法院诉讼文书" },
  ];
  assert.deepEqual(
    filterCaseFileTypesForCaseType("民事争议", catalog, {
      sources: [{ id: 110, name: "民事争议" }],
      targets: catalog,
      relations: {},
    }),
    catalog,
  );
});

test("move destinations stay inside the case-document tree", () => {
  assert.match(source, /getCaseDocumentMoveCategoryOptions/);
  assert.match(source, /options=\{counselMoveCategoryOptions\}/);
  assert.doesNotMatch(source, /options=\{counselUploadCategoryOptions\}\/>\<\/Form\.Item\>\s*\<Alert type="info"/);
});

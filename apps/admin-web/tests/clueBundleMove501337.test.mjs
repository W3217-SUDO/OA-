// 501337：线索、证物、该线索的费用为一体，移任何一项整条一起移。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const page = read("../src/legal/CaseCenterPage.tsx");
const panel = read("../src/legal/CaseDetail/CaseCluesPanel.tsx");
const header = read("../src/legal/CaseDetail/CaseDetailHeader.tsx");

test("移费弹窗可选所属线索并预览一起移的证物和费用", () => {
  assert.match(page, /label="所属线索" name="clue_id"/);
  assert.match(page, /不属于线索（只移这笔费用）/);
  assert.match(page, /<ClueBundlePreview caseId=\{viewingCounselCase\?\.id\}/);
});

test("线索信息页签可把一条线索移到其他案子", () => {
  assert.match(panel, />移到其他案子<\/Button>/);
  assert.match(page, /\/cases\/\$\{movingClue\.caseRow\.id\}\/clues\/\$\{movingClue\.clue\.id\}\/move-case/);
});

test("案件头公证书号、仓库位置按关联线索的证物显示", () => {
  assert.match(header, /evidenceCertificates\|\|viewingCase\.data\.notarial_no/);
  assert.match(header, /evidenceLocations\|\|viewingCase\.data\.warehouse/);
});

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const modalStart = source.indexOf('title="新增提成"');
const modalEnd = source.indexOf('open={Boolean(paymentPackagePreview)}', modalStart);
const modal = source.slice(modalStart, modalEnd);

test("row 12 opens the dedicated commission preview instead of the generic fee drawer", () => {
  assert.match(source, /key==="commission"\?void openCaseCommission\(\)/);
  assert.match(source, /\/commission-preview/);
  assert.doesNotMatch(source, /key==="commission"\?handleInternalFeeAction\("create"\)/);
});

test("row 12 dedicated modal restores all legacy commission columns", () => {
  for (const heading of ["案号", "费用类型", "支付对象", "基数", "参考提成", "实际金额", "备注", "操作"]) {
    assert.match(modal, new RegExp(heading));
  }
  assert.match(modal, /提成基数取当前选中的代理费金额/);
  assert.match(modal, /未配置对应提成/);
});

test("row 12 submits one atomic batch and refreshes internal settlement", () => {
  assert.match(source, /api\.post\(`\/cases\/\$\{viewingCounselCase\.id\}\/commissions`/);
  assert.match(source, /source_fee_id: caseCommissionPreview\.source_fee\.id/);
  assert.match(source, /preview_key: row\.preview_key/);
  assert.match(source, /openCounselDetail\(viewingCounselCase, "internal-fees"\)/);
});

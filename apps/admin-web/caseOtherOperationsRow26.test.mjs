import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const backend = fs.readFileSync(new URL("../api-server/app/main.py", import.meta.url), "utf8");

test("案件律所费用其他操作与旧系统六项菜单一致", () => {
  for (const label of ["法院退费", "申请付款", "申请开票", "修改", "删除", "标记不缴费"]) {
    assert.match(page, new RegExp(`label:\"${label}\"`));
  }
  assert.match(page, /key===\"edit\"\)return editCaseFee\(selectedFirmFee!\)/);
  assert.match(page, /key===\"delete\"\)return deleteCaseFee\(selectedFirmFee!\)/);
  assert.match(page, /key===\"no-payment\"\)return markCaseFeeNoPayment\(selectedFirmFee!\)/);
  assert.match(page, /api\.post\(`\/finance\/fees\/\$\{row\.id\}\/mark-no-payment`/);
});

test("标记不缴费是受权限和状态保护的持久化操作", () => {
  assert.match(backend, /@app\.post\(f\"\{settings\.api_prefix\}\/finance\/fees\/\{\{fee_id\}\}\/mark-no-payment\"\)/);
  assert.match(backend, /await _require_record_owner_or_manager\(item, identity, db\)/);
  assert.match(backend, /item\.status not in \{\"草稿\", \"已退回\"\}/);
  assert.match(backend, /item\.status = \"不缴费\"/);
  assert.match(backend, /\"payment_status\": \"不缴费\"/);
  assert.match(backend, /action=\"案件费用标记不缴费\"/);
});

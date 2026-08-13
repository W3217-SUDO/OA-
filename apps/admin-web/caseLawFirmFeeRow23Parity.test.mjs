import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const source = fs.readFileSync(path.join(import.meta.dirname, "src", "CaseCenterPage.tsx"), "utf8");

test("row 23 law-firm fee dialog keeps case contract and deadline fields", () => {
  assert.match(source, /Form\.List name="items"/);
  assert.match(source, /已创建 \$\{created\.length\} 条费用草稿/);
  assert.match(source, /MinusCircleOutlined/);
  assert.match(source, /PlusOutlined/);
  assert.match(source, /\["items", 0, "expense_subtype"\]/);
  assert.match(source, /label="合同号" name="contract_record_id"/);
  assert.match(source, /label="截止日期" name="deadline"/);
  assert.match(source, /formatRequiredDate\(values\.deadline, "截止日期"\)/);
});

test("row 23 exposes extended law-firm fee types with official-fee mapping", () => {
  for (const subtype of ["诉讼费", "保全费", "鉴定费", "公证费", "公告费", "执行费"]) {
    assert.match(source, new RegExp(`"${subtype}"`));
  }
  assert.match(source, /\["官费","诉讼费","保全费","鉴定费","公证费","公告费","执行费"\]\.includes\(subtype\)/);
});

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 23 firm fee form keeps a system contract selector and all legacy fee branches", () => {
  assert.match(source, /label="合同号" name="contract_record_id"/);
  assert.match(source, /请选择关联合同/);
  for (const feeType of ["官费", "诉讼费", "保全费", "鉴定费", "公证费", "公告费", "执行费", "第三方费用", "代理费", "其他费用"]) {
    assert.match(source, new RegExp(`"${feeType}"`));
  }
  for (const field of ["费用名称", "费用归属", "费用类别", "金额", "经办人员", "收款单位", "缴费法院\/机构", "缴费通知文号", "说明"]) {
    assert.match(source, new RegExp(`label="${field}`));
  }
});

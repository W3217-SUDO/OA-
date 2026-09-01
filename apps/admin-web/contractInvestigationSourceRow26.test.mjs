import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract investigation modal exposes the immutable customer and contract source", () => {
  const modalStart = source.indexOf('title={`新建调查任务：');
  const modalEnd = source.indexOf('title="选择城市"', modalStart);
  const modal = source.slice(modalStart, modalEnd);

  assert.ok(modalStart > 0 && modalEnd > modalStart);
  assert.match(modal, /title="来源合同与客户"/);
  assert.match(modal, /label="绑定客户"[\s\S]*investigating\?\.data\.customer_name[\s\S]*investigating\?\.customer/);
  assert.match(modal, /label="合同编号"[\s\S]*investigating\?\.serial_no/);
  assert.match(modal, /label="合同名称"[\s\S]*investigating\?\.title/);
  assert.match(modal, /investigationError[\s\S]*<Alert type="error" showIcon message=\{investigationError\}/);
});

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/InvestigationCenterPage.tsx", import.meta.url),
  "utf8",
);

test("历史迁移调查新增子任务不再显示无法选择的关联合同必填项", () => {
  assert.match(source, /const isLegacyInvestigationRecord = \(row: Row \| null\)/);
  assert.match(source, /data\.migration_source[\s\S]*?data\.legacy_investigation_id[\s\S]*?data\.legacy_record/);
  assert.match(source, /!isLegacyInvestigationRecord\(taskTarget\)[\s\S]*?label="关联合同"/);
});

test("非迁移且未绑定合同的调查仍保留合同绑定门禁", () => {
  assert.match(source, /!taskTarget\?\.data\.contract_id[\s\S]*?!taskTarget\?\.data\.contract_record_id[\s\S]*?rules=\{\[\{ required: true, message: "请绑定与调查客户一致的合同" \}\]\}/);
});

test("过期门禁仅限制当前任务，不阻断历史迁移任务继续分配", () => {
  assert.match(
    source,
    /createSubtask\s*&&\s*!isLegacyInvestigationRecord\(row\)\s*&&[\s\S]*?authorizationEnd\.isBefore/,
  );
});


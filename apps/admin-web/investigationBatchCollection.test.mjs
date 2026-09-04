import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");

test("线索列表底部主取证按钮提供单个和批量两个真实动作", () => {
  const actionArea = source.slice(
    source.indexOf("businessActionLabels.map"),
    source.indexOf("open={createOpen}"),
  );
  assert.match(actionArea, /label === "取证" \? \([\s\S]*?<Dropdown[\s\S]*?key: "single", label: "单个取证"[\s\S]*?key: "batch", label: "批量取证"/);
  assert.match(actionArea, /key === "single"[\s\S]*?runOriginalAction\(label\)[\s\S]*?openBatchCollection\(\)/);
  assert.match(actionArea, /<Button>取证<\/Button>/);
  assert.match(source, /登记取证[\s\S]*?onClick=\{\(\) => openSingleCollection\(r\)\}|onClick=\{\(\) => openSingleCollection\(r\)\}[\s\S]*?登记取证/);
});

test("批量取证校验多选和状态并调用批量接口", () => {
  assert.match(source, /targets\.length < 2[\s\S]*?请至少选择两条待取证线索/);
  assert.match(source, /row\.status !== "待取证"[\s\S]*?仅待取证线索可批量办理/);
  assert.match(source, /api\.post\("\/investigations\/clues\/batch-collect"[\s\S]*?clue_ids: batchCollectionTargets\.map/);
  assert.match(source, /message\.success\(`已为 \$\{data\.collected\} 条线索批量登记取证`\)/);
  assert.match(source, /setSelectedClues\(\[\]\)/);
});

test("批量弹窗不允许把同一附件错误关联给多条线索", () => {
  assert.match(source, /batchCollectionTargets\.length === 0 && <Form\.Item label="证据文件">/);
});

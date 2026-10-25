import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { hardcodedPopupWidths, localStatusColorMaps, scanSources } from "./popupStatusScan.mjs";

// 基线记录的是统一规范之前的存量；迁移一个模块就把它从基线里删掉或调小，只许减少，不许增加。
const baseline = JSON.parse(readFileSync(new URL("./popupStatusBaseline.json", import.meta.url), "utf8"));
const current = scanSources();

function compare(kind, advice) {
  const problems = [];
  const files = new Set([...Object.keys(baseline[kind]), ...Object.keys(current[kind])]);
  for (const file of [...files].sort()) {
    const allowed = baseline[kind][file] ?? 0;
    const actual = current[kind][file] ?? 0;
    if (actual > allowed) problems.push(`${file}：${actual} 处（基线 ${allowed}），${advice}`);
    if (actual < allowed) problems.push(`${file}：已减少到 ${actual} 处，请把 popupStatusBaseline.json 里的基线改成 ${actual || "删除该行"}`);
  }
  assert.deepEqual(problems, []);
}

test("弹窗和侧滑不再新增写死的宽度", () => {
  compare("popupWidths", "请改用 components/common/popupSize.ts 的 POPUP_WIDTH，侧滑用 size 而不是 width");
});

test("模块不再新建自己的状态颜色表", () => {
  compare("statusMaps", "请改用 components/common/StatusTag.tsx，新状态加到 statusTone.ts");
});

test("扫描规则能认出写死宽度和自建颜色表", () => {
  assert.equal(hardcodedPopupWidths('<Modal open width={760} title="a">'), 1);
  assert.equal(hardcodedPopupWidths('<Modal width={preview ? 1000 : 760}>'), 1);
  assert.equal(hardcodedPopupWidths('<Drawer size="min(760px, 95vw)">'), 1);
  assert.equal(hardcodedPopupWidths("<Drawer width={POPUP_WIDTH.md}>"), 1);
  assert.equal(hardcodedPopupWidths("<Modal width={POPUP_WIDTH.md} onOk={() => save({ a: 1 })}>"), 0);
  assert.equal(hardcodedPopupWidths("<Drawer size={POPUP_WIDTH.lg}>"), 0);
  assert.equal(hardcodedPopupWidths("<Modal open>"), 0);
  assert.equal(localStatusColorMaps("const statusColors: Record<string, string> = {"), 1);
  assert.equal(localStatusColorMaps("const STATUS_COLORS = {"), 1);
  assert.equal(localStatusColorMaps("const statusOptions = ["), 0);
});

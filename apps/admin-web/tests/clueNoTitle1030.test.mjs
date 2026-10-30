// BUG20261030008：线索没有“标题/事项”（旧系统也没有），店铺名称单独一项；新增、修改、列表、详情都不再出现标题。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(`../src/investigation/${path}`, import.meta.url), "utf8");
const drawer = read("ClueCreateDrawer.tsx");
const edit = read("EditRecordModal.tsx");
const page = read("InvestigationCenterPage.tsx");
const header = read("ClueDetail/ClueDetailHeader.tsx");

test("新增线索表单没有标题/事项，店铺名称仍在", () => {
  assert.ok(!drawer.includes("标题/事项"));
  assert.ok(!drawer.includes('name="title"'));
  assert.ok(drawer.includes('label="店铺名称" name="shop_name"'));
});

test("修改线索不显示标题，保存不提交标题", () => {
  assert.match(edit, /editTarget\?\.module !== "clue" && \(\s*<Form\.Item\s*label="标题\/事项"/);
  assert.ok(page.includes('...(editTarget.module === "clue" ? {} : { title: v.title }),'));
  assert.ok(page.includes('title: targetModule === "clue" ? "" : values.title,'));
});

test("线索列表和详情不显示标题，店铺名称不拿标题顶替", () => {
  assert.ok(page.includes('...(tab === "clue" ? [] : [{ title: "标题/事项"'));
  assert.ok(page.includes('render: (_: unknown, r: Row) => r.data.shop_name || "—",'));
  assert.ok(header.includes('investigationDetail.module === "clue" ? [] : [{'));
  assert.ok(header.includes('children: investigationDetail.data.shop_name || "—",'));
});

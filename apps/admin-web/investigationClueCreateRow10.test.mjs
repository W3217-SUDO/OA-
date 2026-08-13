import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const source = await readFile(
  new URL("./src/InvestigationCenterPage.tsx", import.meta.url),
  "utf8",
);
const createModalStart = source.indexOf('title="新建调查线索"');
const createModal = source.slice(
  createModalStart,
  source.indexOf('initialTab === "notary-import-files"', createModalStart),
);

test("8.13 row 10 restores the legacy clue-report fields and actions", () => {
  const labels = [
    "线索编号",
    "调查员",
    "标题/事项",
    "客户",
    "侵权方式",
    "销售渠道",
    "侵权产品",
    "店铺链接",
    "店铺名称",
    "店铺Id",
    "有无产品",
    "调查日期",
    "调查辅助员",
    "备注",
    "附件",
  ];
  for (const label of labels) assert.match(createModal, new RegExp(label));
  assert.match(createModal, /暂存线索/);
  assert.match(createModal, /提交审批/);
  assert.match(createModal, /CLUE_SALES_CHANNEL_OPTIONS/);
  assert.match(createModal, /\{ value: true, label: "有" \}/);
  assert.match(createModal, /\{ value: false, label: "无" \}/);
});

test("8.13 row 10 sends legacy clue fields through the actual record payload", () => {
  for (const field of [
    "sales_channel",
    "shop_name",
    "store_url",
    "shop_id",
    "investigation_assistant",
  ]) {
    assert.match(source, new RegExp(`${field}: values\\.${field}`));
  }
  assert.match(source, /has_product: Boolean\(values\.has_product\)/);
  assert.match(source, /platform: values\.sales_channel \|\| ""/);
  assert.match(source, /sales_channel: row\.data\.sales_channel \|\| row\.data\.platform \|\| ""/);
  assert.match(source, /label: "销售渠道"/);
  assert.match(source, /label: "店铺名称"/);
});

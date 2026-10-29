// BUG20261029003：待取证线索取证时证物存放处选填，没库位也能点“确认已取证”。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const modal = fs.readFileSync(new URL("../src/investigation/CollectionModal.tsx", import.meta.url), "utf8");

test("证物存放处不再必填，确认按钮不因库位禁用", () => {
  assert.ok(!modal.includes("请选择证物存放处"));
  assert.ok(!/okButtonProps=\{\{ disabled: collectionStorage/.test(modal));
  const field = modal.slice(modal.indexOf('label="证物存放处"'), modal.indexOf("<Cascader"));
  assert.ok(!field.includes("required"));
  assert.match(modal, /label="取证机构"[\s\S]*?rules=\{\[\{ required: true, min: 2 \}\]\}/);
  assert.match(modal, /label="取证日期"[\s\S]*?rules=\{\[\{ required: true \}\]\}/);
});

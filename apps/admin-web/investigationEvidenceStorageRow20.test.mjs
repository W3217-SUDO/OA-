import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");
const collectionModal = source.slice(
  source.indexOf('open={Boolean(collectionTarget)}'),
  source.indexOf('open={Boolean(evidenceSource)}'),
);

test("取证弹窗使用单一证物存放处树并由真实仓库目录分组库位", () => {
  assert.match(source, /const collectionStorageOptions = warehouseCatalog[\s\S]*?warehouse\.is_active[\s\S]*?warehouse\.locations[\s\S]*?location\.is_active/);
  assert.match(source, /label="证物存放处"[\s\S]*?name="evidence_storage_path"[\s\S]*?<Cascader[\s\S]*?options=\{collectionStorageOptions\}/);
  assert.doesNotMatch(collectionModal, /label="仓库" name="warehouse_id"/);
  assert.doesNotMatch(collectionModal, /label="库位" name="storage_location_id"/);
});

test("树形选择仍提交稳定仓库和库位 ID 并支持已有值回显", () => {
  assert.match(source, /onChange=\{\(path\) => collectionForm\.setFieldsValue\(\{[\s\S]*?warehouse_id: Number\(path\?\.\[0\]\)[\s\S]*?storage_location_id: Number\(path\?\.\[1\]\)/);
  assert.match(source, /evidence_storage_path:[\s\S]*?\[Number\(r\.data\.warehouse_id\), Number\(r\.data\.storage_location_id\)\]/);
  assert.match(source, /<Form\.Item name="warehouse_id" hidden>/);
  assert.match(source, /<Form\.Item name="storage_location_id" hidden>/);
});

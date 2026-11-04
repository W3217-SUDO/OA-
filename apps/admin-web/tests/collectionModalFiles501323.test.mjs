// 501323（fwl 11-04）：取证弹窗换线索后，证据文件框不留上一条线索的文件。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const modal = readFileSync(new URL("../src/investigation/CollectionModal.tsx", import.meta.url), "utf8");

test("文件框按线索重建，清空选择时把框里的文件名也清掉", () => {
  assert.match(modal, /key=\{collectionTarget\?\.id \?\? "none"\}/);
  assert.match(modal, /if \(!collectionFiles\.length && fileInput\.current\) fileInput\.current\.value = "";/);
  assert.match(modal, /ref=\{fileInput\}/);
});

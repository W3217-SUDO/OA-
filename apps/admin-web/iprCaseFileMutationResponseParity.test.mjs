import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const helper = await import(new URL("./src/iprCaseDetailParity.mjs", import.meta.url));
const page = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

test("IPR file mutation responses preserve legacy PostResponse failures", () => {
  assert.deepEqual(
    helper.normalizeIprMutationResponse({ data: { IsSuccess: false, Message: "legacy file delete failed" } }, "fallback ok"),
    { ok: false, message: "legacy file delete failed" },
  );
  assert.deepEqual(
    helper.normalizeIprMutationResponse({ data: { IsSuccess: true, Message: "legacy file deleted" } }, "fallback ok"),
    { ok: true, message: "legacy file deleted" },
  );
  assert.equal(
    helper.assertIprMutationSuccess({ data: { IsSuccess: true } }, "fallback ok"),
    "fallback ok",
  );
  assert.throws(
    () => helper.assertIprMutationSuccess({ data: { IsSuccess: false, Message: "legacy file delete failed" } }, "fallback ok"),
    /legacy file delete failed/,
  );
  assert.equal(
    helper.getIprApiErrorMessage({ response: { data: { Message: "legacy file delete failed" } } }, "fallback error"),
    "legacy file delete failed",
  );
});

test("IPR file actions check PostResponse before success messages or refresh", () => {
  assert.match(page, /assertIprMutationSuccess/);
  assert.match(page, /const uploadResult = assertIprMutationSuccess\(\s*uploadResponse,/);
  assert.match(page, /const batchUploadResult = assertIprMutationSuccess\(\s*batchUploadResponse,/);
  assert.match(page, /const markResult = assertIprMutationSuccess\(\s*markResponse,/);
  assert.match(page, /const batchMarkResult = assertIprMutationSuccess\(\s*batchMarkResponse,/);
  assert.match(page, /const deleteResult = assertIprMutationSuccess\(\s*deleteResponse,/);
  assert.match(page, /getIprApiErrorMessage\(e, "批量上传案件文档失败"\)/);
  assert.match(page, /getIprApiErrorMessage\(e, "标记已转失败"\)/);
  assert.match(page, /getIprApiErrorMessage\(e, "批量标记已转失败"\)/);
});

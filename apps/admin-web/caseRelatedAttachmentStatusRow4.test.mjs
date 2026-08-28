import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case related folders send the case authorization context", () => {
  assert.match(source, /data\.append\("source_case_id", String\(viewingCounselCase\.id\)\)/);
  assert.match(source, /case_id:isRelatedDocumentFolder\?viewingCounselCase\.id:undefined/);
});

test("related customer and contract folders expose the case delete action", () => {
  assert.doesNotMatch(source, /can_delete_attachment && !isRelatedDocumentFolder/);
  assert.match(source, /can_delete_attachment && <Button danger onClick=\{deleteCounselAttachments\}>删除选中<\/Button>/);
});

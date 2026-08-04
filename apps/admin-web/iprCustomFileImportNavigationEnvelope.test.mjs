import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/IprCustomFileImportPage.tsx", import.meta.url), "utf8");
const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  source,
  /import \{ assertIprMutationSuccess, getIprApiErrorMessage \} from "\.\/iprCaseDetailParity\.mjs";/,
  "Custom IPR file import should reuse the legacy mutation envelope helpers.",
);

assert.match(
  source,
  /const openLinkedIprCase = \(item: IprCase\) => \{[\s\S]*?params\.set\("page", item\.data\.case_kind === "商标" \? "ipr-trademark" : "ipr-patent"\);[\s\S]*?params\.set\("record_id", String\(item\.id\)\)/,
  "Custom IPR file import should preserve the IPR record_id detail target.",
);

assert.match(
  source,
  /const openLinkedIprCase = \(item: IprCase\) => \{[\s\S]*?window\.history\.pushState\([\s\S]*?window\.dispatchEvent\(new PopStateEvent\("popstate"\)\)/,
  "Custom IPR file import should navigate in-app without reloading the shell.",
);

assert.doesNotMatch(
  source,
  /window\.location\.assign/,
  "Custom IPR file import should not hard-refresh linked IPR cases.",
);

assert.match(
  source,
  /onClick=\{\(\)=>openLinkedIprCase\(item\)\}/,
  "Custom IPR file import linked case column should call the in-app navigation helper.",
);

for (const marker of [
  "assertIprMutationSuccess(uploadResponse",
  "assertIprMutationSuccess(saveResponse",
  "assertIprMutationSuccess(matchResponse",
  "assertIprMutationSuccess(confirmResponse",
  "assertIprMutationSuccess(batchUploadResponse",
]) {
  assert.ok(source.includes(marker), "missing legacy mutation success guard: " + marker);
}

for (const fallback of [
  "自定义文件解析失败",
  "候选文件保存失败",
  "确认导入失败",
  "批量上传失败",
]) {
  assert.match(
    source,
    new RegExp("getIprApiErrorMessage\\(e,\\s*\"" + fallback + "\"\\)"),
    "missing legacy error message fallback: " + fallback,
  );
}

assert.match(
  center,
  /new URLSearchParams\(window\.location\.search\)\.get\("record_id"\)/,
  "IPR center should still consume record_id for linked detail opening.",
);

console.log("ipr custom file import navigation and envelope: PASS");

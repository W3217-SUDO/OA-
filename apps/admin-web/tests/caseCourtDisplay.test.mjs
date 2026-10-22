import assert from "node:assert/strict";
import fs from "node:fs";
import ts from "typescript";
import { test } from "node:test";

const source = fs.readFileSync(new URL("../src/legal/courtDisplay.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;
const exports = {};
new Function("exports", compiled)(exports);
const { caseCourtDisplay } = exports;

test("法院名称只取服务端展示状态，未知代码明确失败且原值不变", () => {
  const data = {
    first_court_name: "黔0201",
    first_court_case_no: "（2026）黔0201民初11035号",
    court_displays: {
      first: { status: "resolved", name: "六盘水钟山区人民法院", raw: "黔0201", error: "" },
      second: { status: "unresolved", name: "", raw: "CODEXDOCCT-UNKNOWN", error: "无法解析" },
      execution: { status: "empty", name: "", raw: "", error: "" },
    },
  };
  const saved = structuredClone(data);
  assert.equal(caseCourtDisplay(data, "first"), "六盘水钟山区人民法院");
  assert.equal(caseCourtDisplay(data, "second"), "法院无法解析（CODEXDOCCT-UNKNOWN），请完善法院参数");
  assert.equal(caseCourtDisplay(data, "execution"), "—");
  assert.equal(caseCourtDisplay(data, "retrial"), "法院名称未加载");
  assert.deepEqual(data, saved);
});

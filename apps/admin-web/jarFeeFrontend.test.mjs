import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("./src/JarFeeManager.tsx", import.meta.url), "utf8");
const finance = readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const app = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

for (const route of [
  'api.get("/finance/jar-fees"',
  'api.post("/finance/jar-fees", payload)',
  'api.put(`/finance/jar-fees/${editing.id}`, payload)',
  'api.delete(`/finance/jar-fees/${row.id}`)',
  'api.post(`/finance/jar-fees/${statusTarget.id}/status`',
  'api.get(`/finance/jar-fees/${row.id}/files`)',
  'api.post(`/finance/jar-fees/${fileTarget.id}/files`, body)',
  'api.get(`/finance/jar-fees/${fileTarget.id}/files/${file.id}/download`',
  'api.delete(`/finance/jar-fees/${fileTarget.id}/files/${file.id}`)',
  'api.get("/finance/jar-fees/export"',
]) assert.ok(page.includes(route), `missing JAR API route: ${route}`);

for (const status of ["待确认", "已确认", "已入账", "已作废"]) {
  assert.ok(page.includes(status), `missing JAR status: ${status}`);
}
assert.ok(finance.includes('initialView === "finance-jar"'));
assert.ok(finance.includes("<JarFeeManager onNavigate={onNavigate} />"));
assert.ok(app.includes('{ key: "finance-jar", label: "JAR交案费管理" }'));
assert.ok(page.includes("const [queryDraft, setQueryDraft]"));
assert.ok(page.includes("const [appliedQuery, setAppliedQuery]"));
assert.ok(page.includes("fileTargetIdRef.current === row.id"));
assert.ok(page.includes("can_manage_files"));
assert.ok(page.includes("allowed_statuses"));
assert.ok(page.includes("editorReadonly"));
assert.ok(page.includes('placeholder="输入合同编号查询"'));
console.log("JAR_FINANCE_FRONTEND_OK");

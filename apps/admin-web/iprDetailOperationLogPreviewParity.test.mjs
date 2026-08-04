import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /\[iprOperationLogDetail, setIprOperationLogDetail\] = useState<IprOperationLog \| null>\(null\)/,
  "IPR detail should keep the selected operation log for its read-only detail view.",
);

assert.match(
  center,
  /dataSource=\{iprOperationLogs\}[\s\S]*?title: "操作"[\s\S]*?onClick=\{\(\) => setIprOperationLogDetail\(row\)\}/,
  "IPR operation log rows should expose the existing log detail entry.",
);

assert.match(
  center,
  /open=\{!!iprOperationLogDetail\}[\s\S]*?title="案件操作日志详情"[\s\S]*?iprOperationLogDetail\.action[\s\S]*?iprOperationLogDetail\.comment[\s\S]*?iprOperationLogDetail\.operator/,
  "IPR operation log detail should render loaded action, operator, and comment without another request.",
);

console.log("ipr detail operation log preview parity: PASS");

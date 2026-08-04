import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /\[iprBusinessLogDetail, setIprBusinessLogDetail\] = useState<IprBusinessLog \| null>\(null\)/,
  "IPR detail should keep the selected business log for its read-only detail view.",
);

assert.match(
  center,
  /dataSource=\{iprBusinessLogs\}[\s\S]*?title: "内容"[\s\S]*?onClick=\{\(\) => setIprBusinessLogDetail\(row\)\}/,
  "IPR business log rows should expose the existing log detail entry.",
);

assert.match(
  center,
  /open=\{!!iprBusinessLogDetail\}[\s\S]*?title="案件业务日志详情"[\s\S]*?iprBusinessLogDetail\.content[\s\S]*?iprBusinessLogDetail\.created_by/,
  "IPR business log detail should render loaded content and creator without another request.",
);

console.log("ipr detail business log preview parity: PASS");

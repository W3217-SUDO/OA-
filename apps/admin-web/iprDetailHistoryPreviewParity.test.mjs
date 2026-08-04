import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /\[iprHistoryDetail, setIprHistoryDetail\] = useState<IprHistoryItem \| null>\(null\)/,
  "IPR detail should keep the selected case history item for its read-only detail view.",
);

assert.match(
  center,
  /dataSource=\{iprHistory\}[\s\S]*?title: "事项"[\s\S]*?onClick=\{\(\) => setIprHistoryDetail\(row\)\}/,
  "IPR case history rows should expose the existing item detail entry.",
);

assert.match(
  center,
  /open=\{!!iprHistoryDetail\}[\s\S]*?title="案件事项详情"[\s\S]*?iprHistoryDetail\.action[\s\S]*?iprHistoryDetail\.comment[\s\S]*?iprHistoryDetail\.operator/,
  "IPR case history detail should render loaded action, comment, and operator without another request.",
);

console.log("ipr detail history preview parity: PASS");

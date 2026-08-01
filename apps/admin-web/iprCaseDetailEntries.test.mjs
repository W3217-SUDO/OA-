import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

const required = [
  "案件事项记录",
  "`/records/${caseId}/history`",
  "loadIprHistory(record.id)",
  "案件文书与附件",
  "案件提醒",
  "案件业务日志与操作日志",
  "维护期限/年费/费率",
];
for (const marker of required) {
  if (!source.includes(marker)) throw new Error(`missing IPR detail entry: ${marker}`);
}
if (!source.includes("dataSource={iprHistory}")) throw new Error("history endpoint is not rendered");
console.log("ipr case detail entries: PASS");

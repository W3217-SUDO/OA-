import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /\[reminderDetail, setReminderDetail\] = useState<IprReminder \| null>\(null\)/,
  "IPR detail should keep the selected reminder for its read-only detail view.",
);

assert.match(
  center,
  /title: "提醒内容",[\s\S]*?onClick=\{\(\) => setReminderDetail\(row\)\}/,
  "IPR reminder rows should let users open the existing reminder data for review.",
);

assert.match(
  center,
  /open=\{!!reminderDetail\}[\s\S]*?title="案件提醒详情"[\s\S]*?reminderDetail\.event_type[\s\S]*?reminderDetail\.content/,
  "IPR reminder detail should show the loaded reminder type and content without another backend request.",
);

console.log("ipr detail reminder preview parity: PASS");

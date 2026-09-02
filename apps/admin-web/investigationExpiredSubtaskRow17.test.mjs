import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /createSubtask[\s\S]*authorizationEnd\.isBefore\(dayjs\(\), "day"\)[\s\S]*Modal\.error\(\{[\s\S]*title: "无法新建子任务"[\s\S]*content: "该任务已过期，不允许新建子任务"[\s\S]*return;/);
assert.doesNotMatch(source, /createSubtask\s*&&\s*!isLegacyInvestigationRecord\(row\)\s*&&[\s\S]*?authorizationEnd\.isBefore/);
assert.match(source, /新增子任务:[\s\S]*requireSingleRow\("新增子任务", \(row\) => void openTasks\(row, true\)\)/);

console.log("9.1 row 17 expired investigation subtask gate passed");

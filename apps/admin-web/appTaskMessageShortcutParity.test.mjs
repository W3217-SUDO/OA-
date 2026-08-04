import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("top toolbar restores the legacy task-message shortcut", () => {
  assert.match(source, /MessageOutlined/, "the shell should expose a recognizable task-message icon");
  assert.match(source, /aria-label="任务消息"/, "the task-message control should remain accessible");
  assert.match(source, /onClick=\{\(\) => navigate\("task-reminders"\)\}/, "the shortcut should activate the existing task-reminders route");
});

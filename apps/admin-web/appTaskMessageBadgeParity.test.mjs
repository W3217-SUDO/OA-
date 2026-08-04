import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("topbar restores the legacy task-message unread badge", () => {
  assert.match(
    source,
    /Badge,/,
    "the shell should import the antd badge component",
  );
  assert.match(
    source,
    /taskUnreadCount/,
    "the shell should keep task unread count state",
  );
  assert.match(
    source,
    /\/tasks\/unread-messages/,
    "the shell should poll the existing task unread messages endpoint",
  );
  assert.match(
    source,
    /unread_messages/,
    "the badge count should come from the endpoint unread_messages field",
  );
  assert.match(
    source,
    /<Badge count=\{taskUnreadCount\}/,
    "the task-message shortcut should render an unread badge",
  );
});

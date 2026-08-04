import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/NotificationCenter.tsx", import.meta.url), "utf8");

test("notification drawer restores the legacy message-center shortcut", () => {
  assert.match(source, /更多内部消息/, "the drawer should expose the legacy message-center label");
  assert.match(source, /onNavigate\("user-messages"\)/, "the shortcut should reuse the existing message-center route");
  assert.match(source, /setOpen\(false\)/, "navigating to the message center should close the notification drawer");
});

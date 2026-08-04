import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/NotificationCenter.tsx", import.meta.url), "utf8");

test("notification drawer restores the legacy in-place message detail", () => {
  assert.match(source, /const \[selectedNotice, setSelectedNotice\] = useState<Notice \| null>\(null\);/, "the drawer should retain the selected notice for detail presentation");
  assert.doesNotMatch(source, /message\s*:\s*['"]user-messages['"]/, "internal messages should open in place instead of bypassing their detail");
  assert.match(source, /setSelectedNotice\(nextNotice\)/, "unrouted notices should open their detail after being marked read");
  assert.match(source, /<Modal\s+open=\{Boolean\(selectedNotice\)\}/, "the selected notice should render in a detail modal");
});

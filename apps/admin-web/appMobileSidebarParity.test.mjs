import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("mobile sidebar preserves the legacy open-and-close workspace behavior", () => {
  assert.match(source, /const \[isNarrowViewport, setIsNarrowViewport\] = useState\(false\)/, "the shell should track the responsive breakpoint");
  assert.match(source, /const \[mobileSidebarOpen, setMobileSidebarOpen\] = useState\(false\)/, "the shell should track the temporary mobile sidebar state");
  assert.match(source, /const sidebarCollapsed = isNarrowViewport\s*\? !mobileSidebarOpen\s*: collapsed && !sidebarHoverExpanded/, "mobile collapse should be independent of the saved desktop preference");
  assert.match(source, /if \(isNarrowViewport\) \{\s*setMobileSidebarOpen\(\(open\) => !open\);/, "the header control should toggle the mobile sidebar");
  assert.match(source, /breakpoint="lg"/, "the sidebar should switch at the legacy narrow-screen boundary");
  assert.match(source, /onBreakpoint=\{\(broken\) => \{\s*setIsNarrowViewport\(broken\);/, "the breakpoint callback should update mobile state");
  assert.match(source, /collapsedWidth=\{isNarrowViewport \? 0 : 50\}/, "the narrow sidebar should hide completely when closed");
  assert.match(source, /collapsed=\{sidebarCollapsed\}/, "the Sider should use the responsive collapsed state");
  assert.match(source, /onClick=\{\(\) => \{\s*if \(isNarrowViewport && mobileSidebarOpen\) setMobileSidebarOpen\(false\);\s*\}\}/, "clicking content should close an open mobile sidebar");
});

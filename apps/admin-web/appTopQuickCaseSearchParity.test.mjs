import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("topbar restores the legacy case-list quick keyword search", () => {
  assert.match(
    source,
    /aria-label="案件快捷搜索"/,
    "the shell should expose a topbar quick search entry",
  );
  assert.match(
    source,
    /placeholder="案号、法院号、案件名、客户名、任务内容"/,
    "the quick search should keep the legacy keyword hint",
  );
  assert.match(
    source,
    /sessionStorage\.setItem\(\s*"sunhold:case-list-return"/,
    "the quick search should hand the keyword to the case list context",
  );
  assert.match(
    source,
    /query: \{ keyword \}/,
    "the case list context should carry the keyword query",
  );
  assert.match(
    source,
    /\["case-company", "case-dept", "case-mine"\]\.find/,
    "the quick search should pick the first authorized case list route",
  );
  assert.match(
    source,
    /navigate\(target\)/,
    "the quick search should open the authorized case list route",
  );
});

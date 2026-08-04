import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/GlobalSearch.tsx", import.meta.url), "utf8");

test("global search submits and renders legacy single-character keywords", () => {
  assert.doesNotMatch(source, /if \(q\.length < 2\)/, "a non-empty legacy keyword should not be blocked by a new minimum length");
  assert.match(source, /const \{ data \} = await api\.get\("\/search", \{ params: \{ q \} \}\)/, "the existing global search endpoint should receive every non-empty keyword");
  assert.match(source, /\{query\.trim\(\) \? \(/, "business results should render for a one-character keyword");
  assert.doesNotMatch(source, /输入至少 2 个字符/, "the empty-state feedback should not contradict supported one-character search");
});

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case creation uses searchable active employee options for source people", () => {
  assert.match(source, /const resolveCasePersonValue = \(source: string\)/);
  assert.match(source, /label="案源人" name="source_person"><Select allowClear showSearch optionFilterProp="label" options=\{caseAssistantOptions\}/);
  assert.doesNotMatch(source, /label="案源人" name="source_person"><Input/);
});

test("contract-originated source people resolve to an employee option identity", () => {
  assert.match(source, /source_person:resolveCasePersonValue\(resolveCaseSourcePerson\(selected\)\)/);
});

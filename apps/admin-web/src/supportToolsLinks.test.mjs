import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const app = fs.readFileSync(new URL("./App.tsx", import.meta.url), "utf8");

test("patent office support tool uses the current official search service", () => {
  assert.match(
    app,
    /label: "国家知识产权局专利局",\s+href: "https:\/\/pss-system\.cponline\.cnipa\.gov\.cn\/conventionalSearch"/,
  );
  assert.doesNotMatch(app, /pss-system\.cnipa\.gov\.cn\/sipopublicsearch/);
});

test("support tools open external services in a separate protected tab", () => {
  assert.match(app, /target="_blank"/);
  assert.match(app, /rel="noreferrer"/);
});

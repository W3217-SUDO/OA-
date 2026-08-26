import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const app = fs.readFileSync(new URL("./App.tsx", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("./dashboard.css", import.meta.url), "utf8");

test("dashboard follows the legacy three-row desktop layout", () => {
  const metrics = app.indexOf('className="metrics reference-metrics dashboard-metrics-panel"');
  const todo = app.indexOf('className="dashboard-card compact-todo-card"');
  const hearing = app.indexOf('className="dashboard-card target-hearing-card"');
  const trend = app.indexOf('className="dashboard-card target-trend-card"');
  const latest = app.indexOf('className="dashboard-card latest-cases-card"');
  const civil = app.indexOf('className="dashboard-card civil-card"');

  assert.ok(metrics > 0);
  assert.ok(metrics < todo && todo < hearing && hearing < trend && trend < latest && latest < civil);
  assert.match(css, /grid-template-areas:"metrics todo" "hearing trend" "latest civil"/);
  assert.match(css, /grid-template-columns:minmax\(0,3fr\) minmax\(300px,1fr\)/);
});

test("desktop dashboard uses compact legacy card and table density", () => {
  assert.match(css, /reference-metrics \.metric\{height:84px/);
  assert.match(css, /compact-todo-card\{grid-area:todo;height:178px/);
  assert.match(css, /target-hearing-card\{grid-area:hearing;height:290px/);
  assert.match(css, /latest-cases-card\{grid-area:latest;height:404px/);
  assert.match(css, /ant-table-tbody>tr>td\{height:29px/);
});

test("narrow dashboards keep a single-column usable order", () => {
  assert.match(
    css,
    /@media\(max-width:1100px\).*grid-template-areas:"metrics" "todo" "hearing" "trend" "latest" "civil"/,
  );
});

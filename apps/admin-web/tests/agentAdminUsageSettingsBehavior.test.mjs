import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src");
const read = relative => fs.readFileSync(path.join(root, relative), "utf8");

test("管理员页面提供全局 Skill、全局 MCP、能力市场和运行状态入口", () => {
  const page = read("AgentAdminPage.tsx");
  assert.match(page, /CapabilityMarket/);
  assert.match(page, /key: "global"/);
  assert.match(page, /key: "mcp"/);
  assert.match(page, /key: "market"/);
  assert.match(page, /key: "overview"/);
  assert.match(page, /\/agent-admin\/overview/);
});

test("管理员页面使用真实技能与个人技能接口，不伪造成功状态", () => {
  const page = read("AgentAdminPage.tsx");
  assert.match(page, /\/agent\/global-skills/);
  assert.match(page, /\/agent-admin\/skills\/users\//);
  assert.match(page, /message\.error/);
  assert.match(page, /message\.success/);
  assert.match(read("capability-market/CapabilityMarket.tsx"), /\/capability-market/);
});

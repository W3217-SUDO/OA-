import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync("src/CustomerCenterPage.tsx", "utf8");
const api = fs.readFileSync("../api-server/app/main.py", "utf8");

test("customer more-actions no longer offer separate level or key-change approvals", () => {
  const menu = page.slice(page.indexOf("const originalActionItems"), page.indexOf("const runOriginalAction"));
  assert.doesNotMatch(menu, /key:\s*"level"/);
  assert.doesNotMatch(menu, /key:\s*"key-change"/);
  assert.match(page, /key:\s*"edit"/);
});

test("legacy customer approval URLs reject writes and direct users to edit", () => {
  for (const name of [
    "submit_customer_level_change",
    "review_customer_level_change",
    "submit_customer_key_change",
    "review_customer_key_change",
  ]) {
    const start = api.indexOf(`async def ${name}`);
    const body = api.slice(start, api.indexOf("\n\n@app", start));
    assert.match(body, /raise HTTPException\(status_code=410/);
    assert.match(body, /客户编辑/);
  }
});

test("customer edit keeps direct business fields and filters system fields", () => {
  assert.match(page, /filterCustomerPatchData\(editableData\)/);
  assert.doesNotMatch(page, /details\.level\s*=\s*editing\.data\.level/);
  assert.doesNotMatch(page, /details\.credit_code\s*=\s*editing\.data\.credit_code/);
  const parity = fs.readFileSync("src/customerParity.mjs", "utf8");
  assert.match(parity, /\"is_shared\"/);
  assert.match(parity, /\"level_change\"/);
  assert.match(parity, /\"key_change\"/);
});

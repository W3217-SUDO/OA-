import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer contact tabs restore the legacy refresh action without a new endpoint", () => {
  assert.ok(
    source.includes(`const refreshCustomerContacts = () => {
    if (!contacts) return;
    void loadContactPage(contacts);
  };`),
    "refresh should reuse the current contact page loader",
  );

  const refreshButtonCount =
    source.split("onClick={() => void refreshCustomerContacts()}>刷新</Button>").length - 1;
  assert.equal(refreshButtonCount, 3, "every customer contact tab should expose a refresh action");
  assert.ok(source.includes("icon={<ReloadOutlined />}"), "refresh should use the established reload icon");
});

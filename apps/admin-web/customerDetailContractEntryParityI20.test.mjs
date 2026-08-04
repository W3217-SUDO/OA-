import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer details retain legacy contract list and create entries", () => {
  assert.match(source, /const openCustomerContractCreate = \(customer: Customer\) =>/);

  const viewTabsStart = source.indexOf('className="customer-view-tabs"');
  const drawerTabsStart = source.indexOf('title={`客户详情：${contacts?.title || ""}`}');
  assert.ok(viewTabsStart >= 0 && drawerTabsStart > viewTabsStart);

  const detailTabs = source.slice(viewTabsStart, drawerTabsStart);
  const drawerTabs = source.slice(drawerTabsStart);
  for (const tabs of [detailTabs, drawerTabs]) {
    assert.match(tabs, /key: "contracts"/);
    assert.match(tabs, /onClick=\{\(\) => openCustomerContracts\(contacts\)\}/);
    assert.match(tabs, /canManageCurrentCustomer && <Button[^>]*onClick=\{\(\) => openCustomerContractCreate\(contacts\)\}/);
  }
});

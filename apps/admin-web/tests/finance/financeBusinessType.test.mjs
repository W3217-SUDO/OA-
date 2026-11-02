import assert from "node:assert/strict";
import test from "node:test";

// 501099：业务类型随当前页面（地址栏 page）带上。
globalThis.window = { location: { search: "" } };
const storage = new Map();
globalThis.localStorage = { getItem: (key) => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) };
function signIn(user) { localStorage.setItem("user", JSON.stringify(user)); }
const businessType = await import("../../src/finance/services/financeBusinessType.ts");

function onPage(page) {
  window.location.search = page ? `?page=${page}` : "";
}

test("非诉财务中心固定非诉，我的/部门回款只在回款列表带归属", () => {
  onPage("ipr-finance-receipts-mine");
  assert.deepEqual(businessType.financeBusinessParams("/finance/incoming-payments", "get"), { business_type: "非诉", owner_scope: "mine" });
  assert.deepEqual(businessType.financeBusinessParams("/finance/incoming-payments", "post"), { business_type: "非诉" });
  onPage("ipr-finance-receipts-dept");
  assert.deepEqual(businessType.financeBusinessParams("/finance/incoming-payments", "get"), { business_type: "非诉", owner_scope: "dept" });
  assert.equal(businessType.canChooseFinanceBusinessType(), false);
});

test("财务中心默认诉讼，可按页切到全部或非诉；其他入口不带", () => {
  onPage("finance-receipts-manage");
  signIn({ actual_role_ids: ["user"], menu_keys: ["finance-receipts-claim"] });
  assert.equal(businessType.canChooseFinanceBusinessType(), false, "诉讼律师没有切换");
  signIn({ actual_role_ids: ["user"], menu_keys: ["finance-receipts-manage"] });
  assert.equal(businessType.canChooseFinanceBusinessType(), true, "财务可切换");
  assert.deepEqual(businessType.financeBusinessParams("/finance/incoming-payments", "get"), { business_type: "诉讼" });
  businessType.setFinanceBusinessType("全部");
  assert.deepEqual(businessType.financeBusinessParams("/finance/incoming-payments", "get"), { business_type: "全部" });
  onPage("finance-invoice-company");
  assert.equal(businessType.financeBusinessType(), "诉讼");
  for (const page of ["platform-finance-overview-manage", "dashboard", ""]) {
    onPage(page);
    assert.deepEqual(businessType.financeBusinessParams("/finance/incoming-payments", "get"), {});
  }
});

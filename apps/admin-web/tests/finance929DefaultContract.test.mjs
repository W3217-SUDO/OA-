import assert from "node:assert/strict";
import test from "node:test";
import { buildCaseFeeContractOptions, defaultCaseFeeContractId } from "../src/caseFeeContractOptions.mjs";

test("R3 案件所绑合同为默认值，用户仍可选择同客户同板块的另一合同", () => {
  const contracts = [
    { id: 3420, serial_no: "CODEX-929-R03-A", customer: "测试客户", title: "合同A", data: { contract_body: "律所" } },
    { id: 3422, serial_no: "CODEX-929-R03-B", customer: "测试客户", title: "合同B", data: { contract_body: "律所" } },
    { id: 3424, serial_no: "CODEX-929-R03-C", customer: "测试客户", title: "合同C", data: { contract_body: "平台" } },
  ];
  const source = { customer: "测试客户", data: { contract_id: 3420, contract_no: "CODEX-929-R03-A" } };
  assert.equal(defaultCaseFeeContractId(contracts, source, "律所"), 3420);
  assert.deepEqual(buildCaseFeeContractOptions(contracts, source, null, "律所").map(row => row.value), [3420, 3422]);
  assert.equal(defaultCaseFeeContractId(contracts, source, "平台"), undefined);
  assert.equal(defaultCaseFeeContractId(contracts, source, "内部"), undefined);
  assert.equal(defaultCaseFeeContractId(contracts, { ...source, data: { contract_no: "CODEX-929-R03-A" } }, "律所"), 3420);
  assert.equal(defaultCaseFeeContractId(contracts, { ...source, data: { contract_id: 999, contract_no: "CODEX-929-R03-A" } }, "律所"), undefined);
  assert.equal(defaultCaseFeeContractId(contracts, { ...source, customer: "其他客户" }, "律所"), undefined);
});

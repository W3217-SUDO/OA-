import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadSourceHelpers = () => {
  const block = source.match(
    /const CONTRACT_PAYMENT_SOURCE_KEYS = [\s\S]*?(?=\nexport default function FinanceCenterPage)/,
  );
  assert.ok(block, "contract payment source helpers should exist");
  const javascript = ts.transpileModule(block[0], {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({ URLSearchParams });
  vm.runInContext(
    `${javascript}\n` +
      "globalThis.__parse = parseContractPaymentSource;" +
      "globalThis.__matches = matchesContractPaymentSource;",
    context,
  );
  return {
    parse: context.__parse,
    matches: context.__matches,
  };
};

const completeSearch = (overrides = {}) =>
  new URLSearchParams({
    payment_no: "FK20260802001",
    contract_no: "SHHT2510026",
    customer: "CODEX-H2客户",
    amount: "1250.5",
    source_id: "806",
    source_module: "contract_payment",
    return_page: "contract-detail-595-SHHT2510026",
    ...overrides,
  }).toString();

const plain = (value) => JSON.parse(JSON.stringify(value));

test("ordinary my-payment visits stay outside contract source mode", () => {
  const { parse } = loadSourceHelpers();
  assert.deepEqual(plain(parse("finance-payment-mine", "?page=finance-payment-mine")), {
    active: false,
  });
  assert.deepEqual(
    plain(parse("finance-payment-waiting", `?${completeSearch()}`)),
    { active: false },
  );
});

test("complete contract source parameters are parsed without losing exact values", () => {
  const { parse } = loadSourceHelpers();
  assert.deepEqual(
    plain(parse("finance-payment-mine", `?${completeSearch()}`)),
    {
      active: true,
      ok: true,
      paymentNo: "FK20260802001",
      contractNo: "SHHT2510026",
      customer: "CODEX-H2客户",
      amount: 1250.5,
      sourceId: 806,
      sourceModule: "contract_payment",
      returnPage: "contract-detail-595-SHHT2510026",
    },
  );
});

test("partial source parameters fail explicitly instead of opening the normal list", () => {
  const { parse } = loadSourceHelpers();
  const result = plain(
    parse("finance-payment-mine", "?page=finance-payment-mine&payment_no=FK-ONLY"),
  );
  assert.equal(result.active, true);
  assert.equal(result.ok, false);
  assert.match(result.error, /缺少参数/);
  assert.match(result.error, /合同号/);
  assert.match(result.error, /返回路径/);
});

test("wrong module, invalid id, and invalid amount are rejected", () => {
  const { parse } = loadSourceHelpers();
  assert.match(
    parse("finance-payment-mine", `?${completeSearch({ source_module: "finance" })}`).error,
    /来源模块无效/,
  );
  assert.match(
    parse("finance-payment-mine", `?${completeSearch({ source_id: "0" })}`).error,
    /来源ID无效/,
  );
  assert.match(
    parse("finance-payment-mine", `?${completeSearch({ amount: "0" })}`).error,
    /金额无效/,
  );
});

test("return route must identify the same contract and a positive detail id", () => {
  const { parse } = loadSourceHelpers();
  assert.match(
    parse(
      "finance-payment-mine",
      `?${completeSearch({ return_page: "contract-detail-595-OTHER" })}`,
    ).error,
    /返回路径无效/,
  );
  assert.match(
    parse(
      "finance-payment-mine",
      `?${completeSearch({ return_page: "contract-detail-0-SHHT2510026" })}`,
    ).error,
    /返回路径无效/,
  );
});

test("exact matching covers source module, id, payment, contract, customer, and amount", () => {
  const { parse, matches } = loadSourceHelpers();
  const target = parse("finance-payment-mine", `?${completeSearch()}`);
  const row = {
    id: 806,
    serial_no: "FK20260802001",
    customer: "CODEX-H2客户",
    data: {
      _source_module: "contract_payment",
      contract_no: "SHHT2510026",
      amount: 1250.5,
    },
  };
  assert.equal(matches(row, target), true);
  for (const changed of [
    { ...row, id: 807 },
    { ...row, serial_no: "FK-OTHER" },
    { ...row, customer: "其他客户" },
    { ...row, data: { ...row.data, _source_module: "finance" } },
    { ...row, data: { ...row.data, contract_no: "OTHER" } },
    { ...row, data: { ...row.data, amount: 1250.51 } },
  ]) {
    assert.equal(matches(changed, target), false);
  }
});

test("Finance page wires URL parsing into exact defaults and a no-fallback row gate", () => {
  assert.match(
    source,
    /parseContractPaymentSource\(initialView,\s*contractPaymentSourceSearch\)/,
  );
  assert.match(
    source,
    /contractPaymentSource\.active\s*&&\s*contractPaymentSource\.ok[\s\S]*?paymentNo:\s*contractPaymentSource\.paymentNo[\s\S]*?contractNo:\s*contractPaymentSource\.contractNo[\s\S]*?customer:\s*contractPaymentSource\.customer/,
  );
  assert.match(
    source,
    /if \(contractPaymentSource\.active\) \{[\s\S]*?if \(!contractPaymentSource\.ok\) return \[\];[\s\S]*?contractPayments\.filter[\s\S]*?matchesContractPaymentSource/,
  );
});

test("source mode renders explicit invalid and missing-target failures plus exact return", () => {
  assert.match(source, /合同付款来源定位失败/);
  assert.match(source, /未找到合同付款来源记录或当前账号无权查看/);
  assert.match(source, /返回合同详情/);
  assert.match(
    source,
    /onNavigate\?\.\(contractPaymentSource\.returnPage\)/,
  );
});

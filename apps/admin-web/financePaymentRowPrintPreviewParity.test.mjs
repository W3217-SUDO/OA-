import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

const loadPaymentPrintPreviewBuilder = () => {
  const start = source.indexOf("const createPaymentPrintPreview");
  const end = source.indexOf("\n\nexport default function FinanceCenterPage", start);
  assert.notEqual(start, -1, "payment print preview builder should exist");
  assert.notEqual(end, -1, "payment print preview builder should be extractable");
  const javascript = ts.transpileModule(source.slice(start, end), {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.None,
    },
  }).outputText;
  const context = vm.createContext({
    money: (value) => `¥ ${Number(value || 0).toFixed(2)}`,
  });
  vm.runInContext(
    `${javascript}\nglobalThis.__createPreview = createPaymentPrintPreview;`,
    context,
  );
  return context.__createPreview;
};

test("single payment print opens a same-origin read-only preview", () => {
  const createPreview = loadPaymentPrintPreviewBuilder();
  const row = {
    id: 7,
    serial_no: "CODEX-F3-PRINT-001",
    title: "公告费",
    customer: "测试客户",
    owner: "Admin",
    data: {
      payment_package_no: "P260802-12345678",
      case_no: "SHMS2301160",
      contract_no: "SHHT2110006",
      contract_title: "测试客户_知识产权维权合同",
      expense_subtype: "官费",
      fee_type: "官方费用",
      fee_type_name: "公告费",
      applicant: "曾瓴杰",
      payer: "测试客户",
      payee: "备用收款单位",
      description: "只读预览",
    },
  };
  const preview = createPreview(
    row,
    [
      {
        id: 1,
        finance_record_id: 7,
        transaction_type: "付款",
        transaction_date: "2026-08-01",
        amount: 100,
        counterparty: "旧收款单位",
        voucher_no: "OLD",
        operator: "旧经办人",
        remark: "旧流水",
      },
      {
        id: 2,
        finance_record_id: 7,
        transaction_type: "付款",
        transaction_date: "2026-08-02",
        amount: 200,
        counterparty: "扫码交费",
        voucher_no: "V-001",
        operator: "管理者",
        remark: "最新流水",
      },
      {
        id: 3,
        finance_record_id: 7,
        transaction_type: "回款",
        transaction_date: "2026-08-03",
        amount: 999,
      },
    ],
    "管理者",
    "2026-08-02 12:00",
  );

  assert.deepEqual(JSON.parse(JSON.stringify(preview)), {
    documentTitle: "CODEX-F3-PRINT-001付款单",
    packageNo: "P260802-12345678",
    serialNo: "CODEX-F3-PRINT-001",
    paymentDate: "2026-08-02",
    feeTitle: "公告费",
    attribute: "官费",
    feeType: "公告费",
    customer: "测试客户",
    caseNo: "SHMS2301160",
    contractNo: "SHHT2110006",
    contractTitle: "测试客户_知识产权维权合同",
    applicant: "曾瓴杰",
    applicantDisplayName: "",
    payer: "测试客户",
    payerDisplayName: "",
    payee: "扫码交费",
    amount: "¥ 200.00",
    voucherNo: "V-001",
    operator: "管理者",
    operatorDisplayName: "",
    remark: "最新流水",
    creator: "管理者",
    printTime: "2026-08-02 12:00",
  });
  assert.equal(createPreview(row, [], "管理者", "2026-08-02 12:00"), null);
});

test("single payment preview stays inside the finance page and can print or cancel", () => {
  const printStart = source.indexOf("  const printPayment");
  const printEnd = source.indexOf("\n  const createInvoice", printStart);
  assert.notEqual(printStart, -1, "single payment print handler should exist");
  assert.notEqual(printEnd, -1, "single payment print handler should be extractable");
  const printHandler = source.slice(printStart, printEnd);

  assert.match(
    source,
    /const \[paymentPrintPreview, setPaymentPrintPreview\]\s*=\s*useState<PaymentPrintDocumentData \| null>/,
  );
  assert.match(source, /setPaymentPrintPreview\(preview\)/);
  assert.match(source, /paymentPrintPreviewPage/);
  assert.match(source, /onClick=\{\(\) => window\.print\(\)\}/);
  assert.match(source, /onClick=\{\(\) => setPaymentPrintPreview\(null\)\}/);
  for (const label of [
    "打包流水号：",
    "打印日期：",
    "收款单位：",
    "付款总金额：",
    "属性：",
    "请款单号：",
    "合同编号：",
    "合同名称：",
    "案号",
    "费用类型",
    "申请人",
    "交款人",
    "备注：",
    "小计",
    "客户管理人签字：",
    "审批人签字：",
    "出纳签字：",
  ]) {
    assert.ok(source.includes(label), `preview should preserve legacy field label: ${label}`);
  }
  assert.doesNotMatch(printHandler, /URL\.createObjectURL/);
  assert.doesNotMatch(printHandler, /new Blob\(\[html\]/);
  assert.doesNotMatch(printHandler, /window\.open\(url/);
});

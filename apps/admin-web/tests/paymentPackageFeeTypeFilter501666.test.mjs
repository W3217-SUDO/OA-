import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const constants = readFileSync(new URL("../src/finance/constants.ts", import.meta.url), "utf8");
const page = readFileSync(new URL("../src/finance/FinanceCenterPage.tsx", import.meta.url), "utf8");

test("501666 package list sends selected fee type codes to the server", () => {
  assert.match(constants, /packageFeeTypes\(query\.routeField4\)\.length \? \{ fee_types: packageFeeTypes\(query\.routeField4\)\.join\(","\) \}/);
  assert.match(constants, /item !== "请选择" && item !== "全部"/);
});

test("501666 package rows are not re-filtered by fee type in the browser", () => {
  assert.match(page, /if \(activeRouteConfig\.source === "paymentPackages"\) return true;/);
});

const actions = readFileSync(new URL("../src/finance/services/paymentsActions.tsx", import.meta.url), "utf8");

test("501666 payment print page has a separate 提交 and 提交并打印 prints after submit", () => {
  assert.match(page, /onClick=\{\(\) => void submitInternalPaymentPackage\("submit"\)\}>\s*提交\s*<\/Button>/);
  assert.match(page, /submitInternalPaymentPackage\("print"\)\.then\(\(ok\) => \{\s*if \(ok\) confirmPaymentWordPrint\(\(\) => downloadPaymentPrintWord\(packageNo\)\);/);
  assert.match(actions, /setPaymentPackagePreview\(mode === "submit" \? null : \{ \.\.\.paymentPackagePreview, submitted: true \}\);/);
});

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("finance person resolver accepts any explicit display name and never falls back to username", () => {
  const resolver = source.slice(
    source.indexOf("const financePersonDisplayName"),
    source.indexOf("const [originalQueryDraft"),
  );
  assert.match(resolver, /if \(explicitName\) return explicitName/);
  assert.match(resolver, /if \(!key\) return "—"/);
  assert.match(resolver, /financePersonNameMap\.get\(key\) \|\| \(\/\[㐀-鿿\]\/.test\(key\) \? key : "—"\)/);
  assert.doesNotMatch(resolver, /姓名待维护/);
  assert.doesNotMatch(resolver, /currentUser\.displayName \|\| currentUser\.username/);
});

test("payment print preview resolves every visible person", () => {
  assert.match(source, /financePersonDisplayName\(paymentPrintPreview\.operator, paymentPrintPreview\.operatorDisplayName\)/);
  assert.match(source, /financePersonDisplayName\(paymentPrintPreview\.applicant, paymentPrintPreview\.applicantDisplayName\)/);
  assert.match(source, /financePersonDisplayName\(paymentPrintPreview\.payer, paymentPrintPreview\.payerDisplayName\)/);
  assert.match(source, /financePersonDisplayName\(paymentPrintPreview\.creator, paymentPrintPreview\.creator\)/);
});

test("invoice details resolve applicant and recipient display names", () => {
  assert.equal((source.match(/invoiceDetailData\.applicant_display_name/g) || []).length >= 3, true);
  assert.equal((source.match(/invoiceDetailData\.recipient_display_name/g) || []).length >= 2, true);
  assert.doesNotMatch(source, /invoiceDetailData\.recipient \|\| ""/);
});

test("settlement and archive contexts resolve submitters reviewers and linked people", () => {
  for (const field of [
    "reviewer_display_name",
    "applied_by_display_name",
    "archive_payment_reviewer_display_name",
    "archive_reviewer_display_name",
    "archive_submitter_display_name",
    "handling_lawyer_display_names",
    "assistant_display_name",
  ]) {
    assert.match(source, new RegExp(field));
  }
});

test("settlement task log and allocation history resolve visible operators", () => {
  assert.match(source, /负责人[\s\S]{0,180}financePersonDisplayName\(value, row\.owner_display_name\)/);
  assert.match(source, /操作人[\s\S]{0,180}financePersonDisplayName\(value, row\.operator_display_name\)/);
  assert.match(source, /分配人[\s\S]{0,180}financePersonDisplayName\(value, row\.allocated_by_display_name\)/);
});

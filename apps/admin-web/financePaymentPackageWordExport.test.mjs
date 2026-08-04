import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/FinanceCenterPage.tsx', import.meta.url), 'utf8');

test('payment package print page exposes legacy Word export action', () => {
  assert.ok(source.includes('const downloadPaymentPrintWord = async (packageNoOverride?: string) => {'));
  assert.ok(source.includes('packageNoOverride || paymentPrintPreview?.packageNo || ""'));
  assert.ok(source.includes('paymentPackageWordExportPath(packageNo)'));
  assert.ok(source.includes('onClick={() => void downloadPaymentPrintWord(paymentPackagePrintData.package_no)}'));
  assert.ok(source.includes('下载 Word'));
});

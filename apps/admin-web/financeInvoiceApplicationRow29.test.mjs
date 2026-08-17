import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("./src/finance-center.css", import.meta.url), "utf8");

test("row 29 renders the legacy invoice workflow as four sections", () => {
  assert.match(source, /finance-invoice-request-drawer/);
  assert.match(source, /<h3>申请信息<\/h3>/);
  assert.match(source, /<h3>发票内容<\/h3>/);
  assert.match(source, /<h3>服务项<\/h3>/);
  assert.match(source, /<h3>发票明细<\/h3>/);
  for (const field of ["合同编号", "外部合同号", "案件名称", "案件阶段", "案号", "费用类型", "费用金额", "已到账金额", "已开票金额", "本次开票", "选择"]) {
    assert.match(source, new RegExp(`>${field}<`));
  }
  assert.match(styles, /\.finance-invoice-request-table/);
});

test("row 29 binds source fees instead of reopening three relationship selectors", () => {
  assert.match(source, /const sourceFee = candidateRows\.find/);
  assert.match(source, /该费用当前不可申请开票（已申请、已开票或不在可开票范围内），未打开开票申请。/);
  assert.match(source, /setInvoiceSourceFeeId\(sourceFee\.id\)/);
  assert.match(source, /applyInvoiceFeeSelection\(nextIds\)/);
  const drawerStart = source.indexOf('className="finance-invoice-request-drawer"');
  const invoiceDrawer = source.slice(drawerStart, source.indexOf("</Drawer>", drawerStart));
  assert.doesNotMatch(invoiceDrawer, /label="关联案件"[\s\S]{0,500}<Select/);
  assert.doesNotMatch(invoiceDrawer, /label="关联合同"[\s\S]{0,500}<Select/);
  assert.doesNotMatch(invoiceDrawer, /label="关联案件费用"[\s\S]{0,500}<Select/);
});

test("row 29 maps the complete customer invoice profile while keeping it editable", () => {
  assert.match(source, /const buildInvoiceCustomerDefaults/);
  assert.match(source, /data\.taxpayer_id \|\| data\.credit_code \|\| data\.unified_social_credit_code/);
  assert.match(source, /data\.bank_account/);
  assert.match(source, /data\.bank_name/);
  assert.match(source, /data\.invoice_address \|\| data\.registered_address/);
  assert.match(source, /data\.invoice_phone \|\| data\.phone \|\| data\.office_phone/);
  assert.match(source, /name="invoice_title"[\s\S]{0,160}<Input \/>/);
  assert.match(source, /name="taxpayer_id"[\s\S]{0,160}<Input \/>/);
  assert.match(source, /name="bank_account"[\s\S]{0,160}<Input \/>/);
  assert.match(source, /name="bank_name"[\s\S]{0,160}<Input \/>/);
});

import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const styles = fs.readFileSync(new URL("./src/case-center.css", import.meta.url), "utf8");

test("case detail document tabs wrap the folder tree and file list", () => {
  const documentTab = page.indexOf('{key:"documents",label:"文档信息"');
  const tree = page.indexOf('className="case-detail-doc-tree"', documentTab);
  const fileList = page.indexOf('className="case-document-list"', tree);

  assert.ok(documentTab >= 0);
  assert.ok(tree > documentTab);
  assert.ok(fileList > tree);
  assert.doesNotMatch(page.slice(documentTab, fileList), /case-doc-all|全部文档/);
  assert.match(styles, /\.case-documents-layout\{grid-template-columns:280px minmax\(0,1fr\)/);
});

test("case folders use the legacy order and aligned yellow folder icons", () => {
  const treeStart = page.indexOf("const counselDocTree=[");
  const treeEnd = page.indexOf("];", treeStart);
  const tree = page.slice(treeStart, treeEnd);

  const customer = tree.indexOf('label:"客户文档"');
  const contract = tree.indexOf('label:"合同文档"');
  const caseFolder = tree.indexOf('label:"案件文档"');
  const investigation = tree.indexOf('label:"调查文档"');
  assert.ok(customer < contract && contract < caseFolder && caseFolder < investigation);
  assert.match(page, /FolderOpenOutlined className="case-doc-icon"/);
  assert.match(page, /FolderOutlined className="case-doc-icon"/);
  assert.match(styles, /\.case-doc-icon\{[^}]*color:#e8b834/);
  assert.match(styles, /\.case-doc-child\{padding-left:25px\}/);
});

test("case detail follows the legacy court and document-table layout", () => {
  assert.match(page, /className="case-court-summary" aria-label="法院信息"/);
  assert.match(page, /<strong>一审法院<\/strong>/);
  assert.match(page, /<strong>执行法院<\/strong>/);
  assert.match(page, /title:"序号"/);
  assert.match(page, /title:"上传时间"/);

  const table = page.indexOf('pagination={getCaseFilePagination()}');
  const toolbar = page.indexOf('className="case-document-toolbar"');
  assert.ok(table >= 0 && toolbar > table, "legacy action toolbar should render below the file table");
  assert.match(styles, /\.case-detail-body-grid\{grid-template-columns:minmax\(0,1fr\) 250px/);
});

test("customer and contract document folders load attachments from their linked records", () => {
  assert.match(page, /setCounselDetailCustomerAttachments/);
  assert.match(page, /setCounselDetailContractAttachments/);
  assert.match(page, /customerRecordId \? api\.get\("\/attachments"/);
  assert.match(page, /contractRecordId \? api\.get\("\/attachments"/);
  assert.match(page, /activeCounselDocCategory==="客户文档"[\s\S]*counselDetailCustomerAttachments/);
  assert.match(page, /activeCounselDocCategory==="合同文档"[\s\S]*counselDetailContractAttachments/);
  assert.match(page, /data\.append\("record_id", String\(targetRecordId\)\)/);
});

test("fee settlement and task tabs preserve legacy tables and bottom actions", () => {
  for (const heading of ["合同编号", "费用类型", "退费", "回款日期", "回款金额", "开票日期", "发票号"]) {
    assert.match(page, new RegExp(`title:\"${heading}\"`));
  }
  assert.match(page, /label:"法院退费"/);
  assert.match(page, /label:"申请付款"/);
  assert.match(page, /label:"申请开票"/);
  for (const heading of ["收款人", "提成类型", "已申请付款金额", "已付款金额", "付款时间", "备注"]) {
    assert.match(page, new RegExp(`title:\"${heading}\"`));
  }
  assert.match(page, /<Button onClick=\{\(\)=>handleInternalFeeAction\("create"\)\}>新增费用<\/Button>/);
  assert.match(page, /title:"标题"/);
  assert.match(page, /title:"提交时间"/);
  assert.match(page, />发布任务<\/Button>/);
  for (const heading of ["\u7ebf\u7d22\u53f7", "\u8c03\u67e5\u65f6\u95f4", "\u5e97\u94fa\u540d\u79f0", "\u5e97\u94fa\u5730\u5740", "\u516c\u8bc1\u4e66\u53f7", "\u516c\u8bc1\u4e66\u72b6\u6001", "\u516c\u8bc1\u4e66\u5165\u5e93\u65f6\u95f4", "\u4ef6\u6570", "\u4ed3\u5e93\u540d\u79f0", "\u4ed3\u5e93\u4f4d\u7f6e", "\u8bc1\u7269\u72b6\u6001"]) {
    assert.match(page, new RegExp(`title:"${heading}"`));
  }
  assert.match(page, /const casePersonDisplayName =/);
  assert.match(page, /row\.owner_display_name\|\|casePersonDisplayName\(row\.owner\)/);
  assert.match(styles, /\.case-legacy-bottom-actions\{margin:/);
});

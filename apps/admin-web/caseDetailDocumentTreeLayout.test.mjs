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
  assert.match(page, /title:"文档日期"/);

  const table = page.indexOf('pagination={getCaseFilePagination()}');
  const toolbar = page.indexOf('className="case-document-toolbar"');
  assert.ok(table >= 0 && toolbar > table, "legacy action toolbar should render below the file table");
  assert.match(styles, /\.case-detail-body-grid\{grid-template-columns:minmax\(0,1fr\) 250px/);
});

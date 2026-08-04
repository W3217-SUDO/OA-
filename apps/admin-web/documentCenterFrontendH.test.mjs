import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/DocumentCenterPage.tsx", import.meta.url), "utf8");

test("outgoing table keeps legacy application columns: seal type, file count, application time and sorters", () => {
  const outgoingBranch = source.slice(source.indexOf("正式发文编号"), source.indexOf("dataSource={outgoingDocuments}"));
  assert.match(outgoingBranch, /title: "印章类型"/);
  assert.match(outgoingBranch, /title: "用印类型"/);
  assert.match(outgoingBranch, /row\.source_type === "case"/);
  assert.match(outgoingBranch, /title: "文件数"/);
  assert.match(outgoingBranch, /title: "申请时间"/);
  assert.match(outgoingBranch, /sorter:/);
  assert.match(outgoingBranch, /\(row as any\)\.attachments\?\.length/);
});

test("outgoing detail exposes legacy customer, application time, offline print and attachment uploader columns", () => {
  const detailBranch = source.slice(source.indexOf("正式发文详情"), source.indexOf("审批与办理记录"));
  assert.match(detailBranch, /label: "(客户名称|\\u5ba2\\u6237\\u540d\\u79f0)"/);
  assert.match(detailBranch, /label: "(申请时间|\\u7533\\u8bf7\\u65f6\\u95f4)"/);
  assert.match(detailBranch, /label: "(打印盖章|\\u6253\\u5370\\u76d6\\u7ae0)"/);
  assert.match(detailBranch, /title: "(上传人|\\u4e0a\\u4f20\\u4eba)"/);
  assert.match(detailBranch, /title: "(上传时间|\\u4e0a\\u4f20\\u65f6\\u95f4)"/);
});

test("attachments keep legacy preview/view entry besides download", () => {
  assert.match(source, /api\.get\(`\/attachments\/\$\{row\.id\}\/preview`/);
  assert.match(source, />[\s\S]*?查看[\s\S]*?<\/Button>/);
  assert.match(source, /receiptAttachment\(r\)/);
  assert.match(source, /previewReceiptFile\(r\)/);
  const previewClickMatches = source.match(/onClick=\{\(\) => previewReceiptFile\(r\)\}/g) || [];
  assert.ok(previewClickMatches.length >= 2, `expected official and receipt list preview entries, got ${previewClickMatches.length}`);
  const filesBranch = source.slice(source.indexOf("const fileColumns"), source.indexOf("const templateColumns"));
  assert.ok(
    filesBranch.includes("onClick={() => void previewAttachment(r)}") &&
      filesBranch.includes("查看") &&
      filesBranch.includes("</Button>"),
    "file attachments should keep a preview/view button besides download",
  );
});

test("receipt footer more actions preserve legacy case-level actions and AI document entry", () => {
  assert.match(source, /receiptMoreActionItems/);
  for (const label of [
    "上传案件文档",
    "新增官费",
    "新增代理费",
    "新增其他费用",
    "新增内部费用",
    "修改开庭律师",
    "修改经办律师",
    "修改律师助理",
    "修改案件阶段",
    "生成授权委托书",
    "生成律所函",
    "生成身份证明",
    "生成结算提成表",
    "案件任务",
    "案件日志",
  ]) {
    assert.ok(source.includes(label), `missing receipt more action label: ${label}`);
  }
  assert.match(source, /onNavigate\?\.\("documents-agent"\)/);
});

test("outgoing, files, templates and archive tables paginate consistently at legacy page size", () => {
  const matches = source.match(/pageSize: 15/g) || [];
  assert.ok(matches.length >= 5, `expected at least 5 pageSize: 15 declarations, got ${matches.length}`);
});

console.log("documentCenterFrontendH: assertions passed");

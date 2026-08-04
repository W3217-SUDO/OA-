import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const backend = fs.readFileSync(path.resolve(process.cwd(), "..", "api-server", "app", "main.py"), "utf8");
const oldRoot = path.resolve(process.cwd(), "..", "..", "..", "旧系统归档源码", "SH.CRM.WEB");
const oldOfficialDocumentFileController = fs.readFileSync(
  path.join(oldRoot, "Areas", "AWS", "Controllers", "OfficialDocumentFileController.cs"),
  "utf8",
);

function sourceHas(source, pattern) {
  return pattern.test(source);
}

function sliceBetween(source, startToken, endToken) {
  const start = source.indexOf(startToken);
  assert.notEqual(start, -1, "missing source anchor: " + startToken);
  const end = source.indexOf(endToken, start + startToken.length);
  assert.notEqual(end, -1, "missing source end anchor: " + endToken);
  return source.slice(start, end);
}

test("legacy official-document attachment list defaults to server-side 15-row paging", () => {
  assert.match(
    oldOfficialDocumentFileController,
    /public ActionResult List\(string id\)[\s\S]*?model\.PageSize = 15[\s\S]*?model\.PageNo = 1/,
  );
  assert.match(
    oldOfficialDocumentFileController,
    /OfficialDocumentFiles\(string officialDocumentGuid, int\? pageNo, int\? pageSize\)[\s\S]*?result\.PageSize = pageSize > 0 \? pageSize\.Value : 15[\s\S]*?result\.TotalItemCount = officialDocumentFiles\.Count[\s\S]*?Skip\(result\.PageSize \* \(result\.PageNo - 1\)\)[\s\S]*?Take\(result\.PageSize\)/,
  );
});

test("SealCenter front end consumes paged seal attachment lists without local slicing", () => {
  const gaps = [];
  const loadDetailFiles = sliceBetween(page, "const loadDetailFiles = async", "const openDetail = async");
  const openDetail = sliceBetween(page, "const openDetail = async", "const downloadAttachment = async");
  const loadFileList = sliceBetween(page, "const loadFileList = async", "const openFileList = async");
  const openFileList = sliceBetween(page, "const openFileList = async", "const previewAttachment = async");
  const detailTable = sliceBetween(page, "dataSource={attachments}", "columns={[");
  const detailDrawer = sliceBetween(page, "open={Boolean(detail)}", "open={fileListOpen}");
  const fileListModal = sliceBetween(page, "open={fileListOpen}", "</Modal>");

  if (!sourceHas(loadDetailFiles, /api\.get\("\/attachments"[\s\S]*?page[\s\S]*?page_size/)) {
    gaps.push("loadDetailFiles must request /attachments with page and page_size.");
  }
  if (!sourceHas(openDetail, /api\.get\("\/attachments"[\s\S]*?page:\s*1[\s\S]*?page_size:\s*sealFilePagination\.defaultPageSize/)) {
    gaps.push("openDetail must load the first attachment page using sealFilePagination.defaultPageSize.");
  }
  if (!sourceHas(loadFileList, /api\.get\("\/attachments"[\s\S]*?page[\s\S]*?page_size/)) {
    gaps.push("loadFileList must request /attachments with page and page_size.");
  }
  if (!sourceHas(openFileList, /loadFileList\(row,\s*1,\s*sealFilePagination\.defaultPageSize\)/)) {
    gaps.push("openFileList must load the first attachment page using sealFilePagination.defaultPageSize.");
  }
  if (!sourceHas(page, /(attachmentTotal|fileListTotal)/)) {
    gaps.push("SealCenter must store response.total separately from the current attachment page items.");
  }
  if (sourceHas(loadDetailFiles + loadFileList, /\.slice\s*\(/)) {
    gaps.push("SealCenter must not fake server paging by slicing a local full attachment list.");
  }
  if (!sourceHas(detailDrawer, /pagination=\{\{[\s\S]*?current:\s*attachmentPage[\s\S]*?pageSize:\s*attachmentPageSize[\s\S]*?total:\s*attachmentTotal[\s\S]*?onChange/)) {
    gaps.push("The detail drawer attachment table must bind current/pageSize/total/onChange.");
  }
  assert.match(detailTable, /dataSource=\{attachments\}/);
  if (!sourceHas(fileListModal, /pagination=\{\{[\s\S]*?current:\s*fileListPage[\s\S]*?pageSize:\s*fileListPageSize[\s\S]*?total:\s*fileListTotal[\s\S]*?onChange/)) {
    gaps.push("The file-count attachment modal must use paged data instead of pagination={false}.");
  }

  assert.deepEqual(gaps, []);
});

test("backend /attachments still lacks the page/page_size contract", () => {
  assert.match(
    backend,
    /async def list_attachments\([^)]*(page|page_size)[^)]*Query/s,
    "FastAPI /attachments must accept page/page_size before seal attachment lists can page server-side.",
  );
});

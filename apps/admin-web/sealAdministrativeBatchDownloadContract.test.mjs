import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("administrative pending list enables batch download only after selecting applications", () => {
  assert.match(
    page,
    /initialView === "seal-admin-pending"[\s\S]*?<Button\s+disabled=\{!selectedRows\.length\}\s+onClick=\{\(\) => downloadSelectedSealFiles\(\)\}\s*>\s*打包下载\s*<\/Button>/,
  );
});

test("batch download posts selected application IDs and saves the ZIP response", () => {
  assert.match(
    page,
    /const packageDownload = async \(selected: SealRow\[\]\) =>[\s\S]*?postSealBlob\(\s*"\/seals\/applications\/batch-download",\s*\{ application_ids: selected\.map\(\(row\) => row\.id\) \},\s*\{ responseType: "blob" \}/,
  );
  assert.match(page, /a\.download = `用印文件-\$\{dayjs\(\)\.format\("YYYYMMDD"\)\}\.zip`/);
  assert.match(page, /URL\.createObjectURL\(res\.data\)/);
});

test("individual attachment download remains available beside administrative ZIP download", () => {
  assert.match(page, /api\.get\(`\/attachments\/\$\{item\.id\}\/download`,\s*\{\s*responseType: "blob"/);
});

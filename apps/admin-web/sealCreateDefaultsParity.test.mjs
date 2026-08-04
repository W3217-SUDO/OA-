import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const page = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
const oldCreate = fs.readFileSync(
  path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "../../../旧系统归档源码/SH.CRM.WEB/Areas/AWS/Views/OfficialDocument/PartialView/Create.cshtml",
  ),
  "utf8",
);

test("legacy create defaults electronic seal and offline print to enabled", () => {
  assert.match(
    oldCreate,
    /OfficialDocument_Basic_IsElectronicSeal_0[\s\S]*?value="true"[\s\S]*?checked="checked"/,
  );
  assert.match(
    oldCreate,
    /OfficialDocument_Basic_IsOfflinePrint_1[\s\S]*?value="true"[\s\S]*?checked="checked"/,
  );
  assert.match(
    page,
    /openApplication = \(row\?: SealRow\) =>[\s\S]*?is_electronic_seal:\s*true[\s\S]*?is_offline_print:\s*true/,
  );
});

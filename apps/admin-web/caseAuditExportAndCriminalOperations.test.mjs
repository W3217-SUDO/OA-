import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("案件导出菜单标明范围与实际文件格式", () => {
  assert.match(source, /label:"导出选中（Excel）"/);
  assert.match(source, /label:"导出当前查询（Excel）"/);
  assert.match(source, /label:"导出选中（CSV）"/);
  assert.match(source, /label:"导出当前查询（CSV）"/);
  assert.match(source, /label: "导出选中归档清单（Excel）"/);
  assert.match(source, /label: "导出选中二维码（Word）"/);
  assert.match(source, /selectedOnly\?"法律顾问案件-选中\.csv":"法律顾问案件-全部\.csv"/);
  assert.match(source, /counselListMode \? void exportCounselCases\(true\) : exportSelectedCasesExcel\(true\)/);
  assert.match(source, /counselListMode \? void exportCounselCases\(false\) : exportSelectedCasesExcel\(false\)/);
  assert.match(source, /if \(key === "selected-manifest"\) exportArchiveManifest\(\)/);
  assert.match(source, /if \(key === "selected-qr-word"\) exportCaseQrWord\(\)/);
});

test("刑事案件详情操作区提供法院维护入口", () => {
  assert.match(
    source,
    /viewingCounselCase\.data\.case_type === "刑事案件"[\s\S]*?openCriminalMaintenance\(viewingCounselCase, "courts"\)/,
  );
});

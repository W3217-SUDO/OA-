import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("./src/investigation/InvestigationCenterPage.tsx", import.meta.url), "utf8");
const header = readFileSync(new URL("./src/investigation/ClueDetail/ClueDetailHeader.tsx", import.meta.url), "utf8");
const panel = readFileSync(new URL("./src/investigation/ClueDetail/ClueEvidencePanel.tsx", import.meta.url), "utf8");
const modal = readFileSync(new URL("./src/investigation/InvestigationDetailModal.tsx", import.meta.url), "utf8");

test("audit queues use the protected audit scope and legacy approval action", () => {
  assert.match(page, /internalClueAuditTabs = new Set\(\["clue-audit-pending", "clue-audit-refused"\]\)/);
  assert.match(page, /internalClueAuditTabs\.has\(initialTab\)\s*\? "audit"/);
  assert.match(page, /"clue-audit-pending": \["查询", "刷新", "修改", "审批"\]/);
  assert.doesNotMatch(page, /"clue-audit-pending": \[[^\]]*转交审核人/);
  assert.doesNotMatch(page, /<Button type="link" onClick=\{\(\) => void openTurnOnAudit\(r\)\}>/);
});

test("clue detail projects source task fields and formats subject data", () => {
  assert.match(header, /formatSubjectDisplay/);
  assert.match(header, /source_task_start_date/);
  assert.match(header, /source_task_end_date/);
  assert.match(header, /source_task_assigner_display_name/);
  assert.match(header, /evidenceStatuses = new Set\(\["待取证", "已取证", "待公证", "已转案件"\]\)/);
  assert.match(panel, /showEvidence: boolean/);
  assert.match(modal, /showEvidence/);
});


import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { createRequire } from "node:module";
import ts from "typescript";

const policyPath = path.join(process.cwd(), "src", "sealWorkflowPolicy.ts");
const javascript = ts.transpileModule(fs.readFileSync(policyPath, "utf8"), {
  fileName: policyPath,
  compilerOptions: {
    esModuleInterop: true,
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const module = { exports: {} };
const wrapper = vm.runInThisContext(
  `(function (require, module, exports, __filename, __dirname) { ${javascript}\n})`,
  { filename: policyPath },
);
wrapper(createRequire(import.meta.url), module, module.exports, policyPath, path.dirname(policyPath));

const {
  canBatchDeleteSealFiles,
  canBatchStampSealRows,
  canBatchWithdrawSealRows,
  canSealAction,
  canSealWithdraw,
  createSealActionGate,
  createSealAssetAuditRequestTracker,
  mergeSealAssetSnapshot,
  sealFilePagination,
  sealAttachmentListFailureMessage,
  formatSealAttachmentSize,
  getSealAttachmentExtension,
  canViewSealAssetAudit,
  shouldCloseSealAssetAuditAfterDelete,
  sealAssetAuditFailureMessage,
  sealAssetAuditPagination,
  sealQueryFailureMessage,
  selectedSealRows,
  compareSealDateValues,
  toSealAuditRows,
} = module.exports;

test("seal file pagination keeps the legacy default, six options and GO", () => {
  assert.equal(sealFilePagination.defaultPageSize, 15);
  assert.deepEqual(sealFilePagination.pageSizeOptions, [10, 15, 20, 50, 100, 200]);
  assert.equal(sealFilePagination.showQuickJumper.goButton, "GO");
});

test("seal asset audit pagination and permission helper match the backend contract", () => {
  assert.equal(sealAssetAuditPagination.defaultPageSize, 15);
  assert.deepEqual(sealAssetAuditPagination.pageSizeOptions, [10, 15, 20, 50, 100, 200]);
  assert.equal(sealAssetAuditPagination.showQuickJumper.goButton, "GO");
  assert.equal(canViewSealAssetAudit("admin"), true);
  assert.equal(canViewSealAssetAudit("manager"), true);
  assert.equal(canViewSealAssetAudit("user"), false);
  assert.equal(canViewSealAssetAudit(""), false);
  assert.equal(shouldCloseSealAssetAuditAfterDelete(7, 7), true);
  assert.equal(shouldCloseSealAssetAuditAfterDelete(7, 8), false);
  assert.equal(shouldCloseSealAssetAuditAfterDelete(7, null), false);
  const tracker = createSealAssetAuditRequestTracker();
  const firstRequest = tracker.next();
  const secondRequest = tracker.next();
  assert.equal(tracker.isCurrent(firstRequest), false);
  assert.equal(tracker.isCurrent(secondRequest), true);
  tracker.invalidate();
  assert.equal(tracker.isCurrent(secondRequest), false);
  assert.equal(sealAssetAuditFailureMessage(403), "当前账号无权查看印章资产审计");
  assert.equal(sealAssetAuditFailureMessage(404), "印章不存在");
  assert.equal(sealAssetAuditFailureMessage(422), "审计日期范围无效");
});

test("seal asset snapshot merge replaces only the matching asset and preserves misses", () => {
  const current = [
    { id: 1, code: "A-1", usage_count: 2 },
    { id: 2, code: "A-2", usage_count: 4 },
    { id: 3, code: "A-3", usage_count: 6 },
  ];
  const latest = { id: 2, code: "A-2", usage_count: 5 };
  assert.deepEqual(mergeSealAssetSnapshot(current, latest), [
    { id: 1, code: "A-1", usage_count: 2 },
    { id: 2, code: "A-2", usage_count: 5 },
    { id: 3, code: "A-3", usage_count: 6 },
  ]);
  assert.deepEqual(mergeSealAssetSnapshot(current, null), current);
});

test("seal audit projection preserves persisted fields and derives fallback round", () => {
  const rows = toSealAuditRows([
    { id: 1, action: "用印审批通过", to_status: "待用印", operator: "a", comment: "ok", created_at: "2026-08-03T01:00:00Z" },
    { id: 2, action: "编辑", to_status: "待用印", operator: "b", comment: "noise", created_at: "2026-08-02T01:00:00Z" },
    { id: 3, action: "用印审批拒绝", audit_status: "R", audit_date: "2026-08-01", audit_content: "理由", audit_round: 4, operator: "c", comment: "ignored", created_at: "2026-08-01T01:00:00Z" },
    { id: 4, action: "用印审批驳回", to_status: "已拒绝", operator: "d", comment: "驳回原因", created_at: "2026-07-31T01:00:00Z" },
  ]);
  assert.equal(rows.length, 3);
  assert.deepEqual(rows[0], {
    id: 1,
    auditor: "a",
    audit_status: "待用印",
    audit_date: "2026-08-03T01:00:00Z",
    audit_content: "ok",
    audit_round: 1,
  });
  assert.deepEqual(rows[1], {
    id: 3,
    auditor: "c",
    audit_status: "R",
    audit_date: "2026-08-01",
    audit_content: "理由",
    audit_round: 4,
  });
  assert.equal(rows[2].audit_status, "已拒绝");
  assert.equal(rows[2].audit_content, "驳回原因");
});

test("seal selection and draft batch-delete gate are runtime helpers", () => {
  const rows = [{ id: 1 }, { id: 2 }, { id: 3 }];
  assert.deepEqual(selectedSealRows(rows, [3, 1]), [{ id: 1 }, { id: 3 }]);
  assert.equal(canBatchDeleteSealFiles("草稿", [1]), true);
  assert.equal(canBatchDeleteSealFiles("待审批", [1]), false);
  assert.equal(canBatchDeleteSealFiles("草稿", []), false);
});

test("seal batch stamp and withdraw gates require compatible pending states", () => {
  assert.equal(canBatchStampSealRows([{ status: "待用印" }, { status: "待用印" }]), true);
  assert.equal(canBatchStampSealRows([{ status: "待用印" }, { status: "已用印" }]), false);
  assert.equal(canBatchStampSealRows([]), false);
  assert.equal(canBatchWithdrawSealRows([{ status: "待审批" }, { status: "待用印" }]), true);
  assert.equal(canBatchWithdrawSealRows([{ status: "待审批" }, { status: "草稿" }]), false);
});

test("seal date sorter compares legacy application and audit timestamps", () => {
  assert.equal(compareSealDateValues("2026-08-02", "2026-08-01") > 0, true);
  assert.equal(compareSealDateValues("", "2026-08-01") < 0, true);
});

test("seal query and attachment list failures retain explicit status semantics", () => {
  assert.equal(sealQueryFailureMessage(403), "当前账号无权查询用印记录");
  assert.equal(sealQueryFailureMessage(409), "用印查询条件已失效，请刷新后重试");
  assert.equal(sealAttachmentListFailureMessage(404), "用印申请或文件列表不存在");
  assert.equal(sealAttachmentListFailureMessage(409), "当前状态不允许查看文件列表");
});

test("seal attachment metadata keeps size and extension projections readable", () => {
  assert.equal(formatSealAttachmentSize(0), "0 B");
  assert.equal(formatSealAttachmentSize(1024), "1 KB");
  assert.equal(formatSealAttachmentSize(1024 * 1024), "1 MB");
  assert.equal(getSealAttachmentExtension("Evidence.PDF"), "PDF");
  assert.equal(getSealAttachmentExtension("untitled"), "");
});

test("seal action controls retain state gates while backend owns permission checks", () => {
  assert.equal(canSealAction("approve", { status: "待审批" }), true);
  assert.equal(canSealAction("approve", { status: "待审批", role: "staff" }), true);
  assert.equal(canSealAction("reject", { status: "待用印" }), false);
  assert.equal(canSealAction("stamp", { status: "待用印" }), true);
  assert.equal(canSealAction("archive", { status: "已用印" }), true);
  assert.equal(canSealAction("archive", { status: "待用印" }), false);
});

test("withdraw control retains the existing pending-state gate", () => {
  assert.equal(canSealWithdraw({ status: "待审批", owner: "alice" }), true);
  assert.equal(canSealWithdraw({ status: "待用印", owner: "alice" }), true);
  assert.equal(canSealWithdraw({ status: "已用印", owner: "alice" }), false);
});

test("seal action gate admits one in-flight action and rejects duplicates", () => {
  const gate = createSealActionGate();
  assert.equal(gate.tryEnter(), true);
  assert.equal(gate.tryEnter(), false);
  gate.leave();
  assert.equal(gate.tryEnter(), true);
});

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
  createSealDetailRequestTracker,
  createSealFileListRequestTracker,
  createSealPreviewRequestTracker,
  mergeSealAssetSnapshot,
  sealFilePagination,
  sealAttachmentListFailureMessage,
  formatSealAttachmentSize,
  getSealAttachmentExtension,
  legacySealApplicationDefaults,
  canViewSealAssetAudit,
  shouldCloseSealAssetAuditAfterDelete,
  sealAssetAuditFailureMessage,
  sealAssetAuditPagination,
  sealErrorMessage,
  sealResponseIsFailure,
  sealQueryFailureMessage,
  selectedSealRows,
  compareSealDateValues,
  toSealAuditRows,
} = module.exports;

test("new seal application defaults match the legacy case-seal flow and prefer a contract seal", () => {
  assert.deepEqual(
    legacySealApplicationDefaults([
      { id: 1, seal_type: "公章", status: "可用" },
      { id: 2, seal_type: "合同章", status: "可用" },
      { id: 3, seal_type: "合同章", status: "停用" },
    ]),
    {
      use_type: "案件用印",
      seal_asset_id: 2,
      copies: 1,
      source_attachment_ids: [],
      delivery_method: "现场用印",
      is_electronic_seal: true,
      is_offline_print: true,
    },
  );
  assert.equal(legacySealApplicationDefaults([{ id: 1, seal_type: "公章", status: "可用" }]).seal_asset_id, 1);
  assert.equal(legacySealApplicationDefaults([]).seal_asset_id, undefined);
});

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

test("seal detail request tracker invalidates stale detail responses", () => {
  const tracker = createSealDetailRequestTracker();
  const firstRequest = tracker.next();
  const secondRequest = tracker.next();
  assert.equal(tracker.isCurrent(firstRequest), false);
  assert.equal(tracker.isCurrent(secondRequest), true);
  tracker.invalidate();
  assert.equal(tracker.isCurrent(secondRequest), false);
});

test("file-list and preview trackers reject A-late/B-fast and closed responses", () => {
  const fileListTracker = createSealFileListRequestTracker();
  const fileA = fileListTracker.next();
  const fileB = fileListTracker.next();
  assert.equal(fileListTracker.isCurrent(fileA), false);
  assert.equal(fileListTracker.isCurrent(fileB), true);
  fileListTracker.invalidate();
  assert.equal(fileListTracker.isCurrent(fileB), false);

  const previewTracker = createSealPreviewRequestTracker();
  const previewA = previewTracker.next();
  const previewB = previewTracker.next();
  assert.equal(previewTracker.isCurrent(previewA), false);
  assert.equal(previewTracker.isCurrent(previewB), true);
  previewTracker.invalidate();
  assert.equal(previewTracker.isCurrent(previewB), false);
});

test("seal audit projection preserves persisted fields and derives fallback round", () => {
  const rows = toSealAuditRows([
    { id: 1, action: "用印审批通过", to_status: "待用印", operator: "a", comment: "ok", created_at: "2026-08-03T01:00:00Z" },
    { id: 2, action: "编辑", to_status: "待用印", operator: "b", comment: "noise", created_at: "2026-08-02T01:00:00Z" },
    { id: 3, action: "用印审批拒绝", audit_status: "R", audit_date: "2026-08-01", audit_content: "理由", audit_round: 4, operator: "c", comment: "ignored", created_at: "2026-08-01T01:00:00Z" },
    { id: 5, action: "用印审批通过", audit_status: "A", audit_date: "2026-08-02", audit_content: "同意", audit_round: 5, operator: "e" },
    { id: 4, action: "用印审批驳回", to_status: "已拒绝", operator: "d", comment: "驳回原因", created_at: "2026-07-31T01:00:00Z" },
  ]);
  assert.equal(rows.length, 4);
  assert.deepEqual(rows[0], {
    id: 1,
    auditor: "a",
    audit_status: "待用印",
    audit_date: "2026-08-03T01:00:00Z",
    audit_content: "ok",
    audit_round: 1,
    current_step: rows[0].audit_status,
  });
  assert.deepEqual(rows[1], {
    id: 3,
    auditor: "c",
    audit_status: "审批拒绝",
    audit_date: "2026-08-01",
    audit_content: "理由",
    audit_round: 4,
    current_step: "",
  });
  assert.equal(rows[2].audit_status, "审批通过");
  assert.equal(rows[2].audit_content, "同意");
  assert.equal(rows[3].audit_status, "已拒绝");
  assert.equal(rows[3].audit_content, "驳回原因");
});

test("seal audit projection keeps explicit rejection and current step", () => {
  const rejected = toSealAuditRows([
    { id: 9, action: "驳回", operator: "reviewer", comment: "补充材料", created_at: "2026-08-03T02:00:00Z", current_step: "审批驳回" },
  ]);
  assert.equal(rejected.length, 1);
  assert.equal(rejected[0].current_step, "审批驳回");
});

test("seal response matrix preserves legacy PostResponse and FastAPI detail failures", () => {
  assert.equal(sealResponseIsFailure({ IsSuccess: false, Message: "旧失败" }), true);
  assert.equal(sealResponseIsFailure({ is_success: false, message: "旧失败" }), true);
  assert.equal(sealResponseIsFailure({ items: [], total: 0 }), false);
  assert.equal(sealErrorMessage({ IsSuccess: false, Message: "旧失败" }, "fallback"), "旧失败");
  assert.equal(sealErrorMessage({ response: { status: 409, data: { detail: "服务端冲突" } } }, "fallback"), "服务端冲突");
  assert.equal(sealErrorMessage({ response: { status: 403, data: {} } }, "无权限"), "无权限");
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

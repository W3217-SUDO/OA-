import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import {
  CONTRACT_ATTACHMENT_ACCEPT,
  CONTRACT_ATTACHMENT_MAX_BYTES,
  CONTRACT_ATTACHMENT_LOCKED_STATUSES,
  buildContractApprovalPayload,
  buildContractDraftDefaults,
  canActOnContractApproval,
  canMutateContractAttachments,
  filterContractCaseOptions,
  resolveContractCustomerSelection,
  validateContractAttachment,
  validateContractDraftValues,
} from "./src/contractWorkflowPolicy.mjs";

const pageSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

const profile = { username: "admin", department: "上海分所" };
const customer = { id: 13, serial_no: "SHKH1810649", title: "客户甲", owner: "admin" };

test("contract draft defaults and required field validation follow the legacy create form", () => {
  const defaults = buildContractDraftDefaults({ serialNo: "HT20260802123456", profile, customer });
  assert.equal(defaults.serial_no, "HT20260802123456");
  assert.equal(defaults.status, "草稿");
  assert.equal(defaults.type, "法律顾问合同");
  assert.equal(defaults.contract_body, "律所");
  assert.equal(defaults.fee_type, "固定收费");
  assert.equal(defaults.amount, 0);
  assert.equal(defaults.customer_id, 13);
  assert.equal(defaults.title, "客户甲合同");
  assert.deepEqual(validateContractDraftValues({ customer_id: 13, title: "合同甲" }), []);
  assert.deepEqual(validateContractDraftValues({ customer_id: 0, title: " " }), ["customer_id", "title"]);
});

test("customer and case selectors keep exact relation and safe empty states", () => {
  assert.equal(resolveContractCustomerSelection(13, [customer], null, profile), customer);
  assert.equal(resolveContractCustomerSelection(99, [customer], null, profile), null);
  const linked = { id: 99, name: "客户乙", serial_no: "SHKH000099" };
  assert.deepEqual(resolveContractCustomerSelection(99, [], linked, profile), {
    id: 99,
    serial_no: "SHKH000099",
    title: "客户乙",
    owner: "admin",
    data: { customer_managers: ["admin"] },
  });
  const cases = [
    { id: 1, serial_no: "A-1", title: "甲案", customer: "客户甲" },
    { id: 2, serial_no: "B-1", title: "乙案", customer: "客户乙" },
    { id: 3, serial_no: "C-1", title: "未回传客户", customer: "" },
  ];
  assert.deepEqual(filterContractCaseOptions(cases, "客户甲").map((item) => item.id), [1, 3]);
});

test("approval actions enforce current-node ownership and trim the decision payload", () => {
  assert.equal(canActOnContractApproval("审批中", "admin", "admin", "staff"), true);
  assert.equal(canActOnContractApproval("审批中", "other", "admin", "staff"), false);
  assert.equal(canActOnContractApproval("审批中", "other", "admin", "admin"), true);
  assert.equal(canActOnContractApproval("草稿", "admin", "admin", "admin"), false);
  assert.deepEqual(buildContractApprovalPayload(false, "  缺少附件  "), { approved: false, comment: "缺少附件" });
});

test("attachment actions preserve legacy accept list, size guard, and locked statuses", () => {
  assert.match(CONTRACT_ATTACHMENT_ACCEPT, /\.pdf/);
  assert.match(CONTRACT_ATTACHMENT_ACCEPT, /\.docx/);
  assert.equal(CONTRACT_ATTACHMENT_MAX_BYTES, 20 * 1024 * 1024);
  assert.deepEqual(CONTRACT_ATTACHMENT_LOCKED_STATUSES, ["审批中", "已归档"]);
  assert.equal(validateContractAttachment(null), "请选择合同附件");
  assert.equal(validateContractAttachment({ size: 0 }), "文件没有任何内容");
  assert.equal(validateContractAttachment({ size: CONTRACT_ATTACHMENT_MAX_BYTES + 1 }), "单个文件不能超过 20MB");
  assert.equal(validateContractAttachment({ size: 1 }), null);
  assert.equal(canMutateContractAttachments("草稿"), true);
  assert.equal(canMutateContractAttachments("审批中"), false);
  assert.equal(canMutateContractAttachments("已归档"), false);
});

test("contract center integrates the second-batch policy at each workflow boundary", () => {
  assert.match(pageSource, /buildContractDraftDefaults\(/);
  assert.match(pageSource, /validateContractDraftValues\(/);
  assert.match(pageSource, /resolveContractCustomerSelection\(/);
  assert.match(pageSource, /filterContractCaseOptions\(/);
  assert.match(pageSource, /canActOnContractApproval\(/);
  assert.match(pageSource, /buildContractApprovalPayload\(/);
  assert.match(pageSource, /validateContractAttachment\(/);
  assert.match(pageSource, /canMutateContractAttachments\(/);
  assert.match(pageSource, /notFoundContent="没有匹配客户/);
  assert.match(pageSource, /没有可用审批人/);
  assert.doesNotMatch(pageSource, /label="合同附件" required=\{!editing\}/, "legacy draft attachments are optional");
});

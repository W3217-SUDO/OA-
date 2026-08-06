import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/contractCreateContext.ts", import.meta.url), "utf8");
const contractPage = readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");
const appShell = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const workflowPolicy = readFileSync(new URL("./src/contractWorkflowPolicy.mjs", import.meta.url), "utf8");

test("new contracts receive the compact SHHT legacy-style number", () => {
  assert.match(source, /const sequenceSeed = value\.month\(\) \* 31 \+ value\.date\(\)/);
  assert.match(source, /`SHHT\$\{value\.format\("YY"\)\}\$\{compactSequence\.toString\(\)\.padStart\(5, "0"\)\}`/);
  assert.doesNotMatch(source, /HT\$\{value\.format\("YYYYMMDDHHmmss"\)\}/);
});

test("customer prefill still consumes the legacy customer context once and caches it", () => {
  assert.match(source, /const CUSTOMER_CONTEXT_KEY = "sunhold:contract-customer"/);
  assert.match(source, /storage\.removeItem\(CUSTOMER_CONTEXT_KEY\)/);
  assert.match(source, /if \(initialized\) return cached/);
  assert.match(source, /reset: \(\) => \{/);
});

test("direct contract-new navigation clears stale customer context", () => {
  assert.match(source, /CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY = "sunhold:contract-customer-route-source"/);
  assert.match(source, /clearContractCustomerContext/);
  assert.match(appShell, /normalizedRoute === "contract-new"/);
  assert.match(appShell, /sessionStorage\.getItem\(CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY\) !== "customer"/);
  assert.match(appShell, /clearContractCustomerContext\(sessionStorage\)/);
  assert.match(
    readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8"),
    /sessionStorage\.setItem\("sunhold:contract-customer-route-source", "customer"\)/,
  );
  assert.match(contractPage, /sessionStorage\.getItem\(CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY\) !== "customer"/);
  assert.match(contractPage, /clearContractCustomerContext\(sessionStorage\)/);
  const directNewRouteEffect = contractPage.slice(
    contractPage.indexOf('if (initialView !== "contract-new")'),
    contractPage.indexOf('}, [initialView]);', contractPage.indexOf('if (initialView !== "contract-new")')),
  );
  assert.match(directNewRouteEffect, /if \(customerContext\) \{[\s\S]{0,120}startCreate\(customerContext\);[\s\S]{0,120}return;/);
  assert.match(directNewRouteEffect, /startCreate\(\);\s*$/);
  assert.doesNotMatch(directNewRouteEffect, /recoverWizard/);
  assert.match(contractPage, /const newContractRouteInitializedRef = useRef\(false\);/);
  assert.match(directNewRouteEffect, /if \(newContractRouteInitializedRef\.current\) return;/);
  assert.match(directNewRouteEffect, /newContractRouteInitializedRef\.current = true;/);
});

test("contract center draft creation lets the server assign the final contract number", () => {
  assert.match(contractPage, /serial_no: target \? v\.serial_no \|\| target\.serial_no \|\| createContractNumber\(\) : ""/);
});

test("new contract approval fields only select configured approvers and do not expose settings", () => {
  assert.match(contractPage, /const approvalOptions = buildChinesePersonOptions\(directory, \(user: DirectoryUser\) => Boolean\(user\.can_approve_contract\)\)/);
  assert.match(contractPage, /placeholder="请选择后台已配置的合同审批人"/);
  assert.match(contractPage, /title="设置合同审批人"/);
  assert.match(contractPage, /initialView !== "contract-approver-settings"/);
  assert.doesNotMatch(contractPage, /label=\{contractApproverLabel\}[\s\S]{0,120}Button[\s\S]{0,80}设置审批人/);
  assert.doesNotMatch(contractPage, /placeholder="请选择合同审批流程人员"/);
});

test("contract investigation loads the configured supervisor instead of choosing the first directory user", () => {
  assert.match(contractPage, /api\.get\("\/investigations\/assignment-supervisor"\)/);
  assert.match(contractPage, /owner: supervisor\.username/);
  assert.doesNotMatch(contractPage, /const supervisor = directory\.find/);
  assert.match(contractPage, /调查主管配置加载失败/);
});

test("new contract basic info is editable instead of fixed defaults", () => {
  assert.match(contractPage, /const CONTRACT_TYPE_OPTIONS = \["法律顾问合同", "争议解决合同", "框架合作合同", "非诉项目合同", "其他"\]\.map/);
  assert.match(contractPage, /label="合同类别" name="type"[\s\S]{0,220}<Select allowClear showSearch optionFilterProp="label" placeholder="请选择合同类别" options=\{CONTRACT_TYPE_OPTIONS\}/);
  assert.match(contractPage, /label="合同名称"[\s\S]{0,120}name="title"[\s\S]{0,160}<Input/);
  assert.doesNotMatch(workflowPolicy, /type: "法律顾问合同"/);
  assert.match(workflowPolicy, /title: customer\?\.title \? `\$\{customer\.title\}合同` : undefined/);
});

test("customer-side contract creation pre-fills an editable customer contract name", () => {
  assert.match(workflowPolicy, /title: customer\?\.title \? `\$\{customer\.title\}合同` : undefined/);
  assert.match(contractPage, /customer: linkedContext \? \{ id: linkedContext\.id, title: linkedContext\.name \} : null/);
  assert.match(contractPage, /<Form\.Item label="合同名称" name="title"[\s\S]{0,180}<Input/);
});

test("new contract wizard keeps the legacy four-step approval and seal flow", () => {
  assert.match(contractPage, /CONTRACT_CREATE_STEP_TITLES = \["合同基本信息", "提交审批", "合同审批", "合同用印"\]/);
  assert.match(contractPage, /wizardStep === 3[\s\S]{0,180}contract-seal-step/);
  assert.match(contractPage, /api\.post\(`\/contracts\/\$\{wizardDraft\.id\}\/seal-application`/);
  assert.match(contractPage, /保存用印草稿/);
  assert.match(contractPage, /生成用印申请并进入用印中心/);
  assert.match(contractPage, /const \{ submit: enterSealCenter, \.\.\.sealValues \} = values/);
  assert.match(contractPage, /if \(enterSealCenter\)[\s\S]{0,180}onNavigate\?\.\("seal-my"\)/);
  assert.match(contractPage, /label="是否同步用印" name="sync_seal"/);
  assert.match(contractPage, /sync_seal: Boolean\(values\.sync_seal\)/);
  assert.match(contractPage, /if \(values\.sync_seal\)[\s\S]{0,180}setWizardStep\(3\)/);
  assert.match(contractPage, /CONTRACT_SEAL_READY_STATUSES = \["审批中", "已通过"/);
  assert.doesNotMatch(contractPage, /wizardDraft\.status === "审批中"\) \{\s*message\.warning\("合同仍在审批中/);
  assert.match(contractPage, /const load = async \(queryOverride\?\: Record<string, any>\)/);
  assert.match(contractPage, /void load\(normalized\)/);
  assert.match(contractPage, /可先提交用印申请；合同审批与用印审批将分别流转/);
  assert.doesNotMatch(contractPage, /合同审批中，请在详情查看进度/);
});

test("re-upload reopens the submit wizard and refreshes the persisted attachment list", () => {
  assert.match(contractPage, /onClick=\{\(\) => void openSubmitWizardFromList\(r\)\}>重新上传/);
  const submitStart = contractPage.indexOf("const submitWizard = async");
  const submitEnd = contractPage.indexOf("const refreshWizard", submitStart);
  const submitHandler = contractPage.slice(submitStart, submitEnd);
  assert.match(submitHandler, /api\.get\("\/attachments", \{ params: \{ record_id: wizardDraft\.id \} \}\)/);
  assert.match(submitHandler, /validateContractApprovalSubmission\(wizardDraft\.status, values\.approvers, currentAttachments\.length\)/);
});

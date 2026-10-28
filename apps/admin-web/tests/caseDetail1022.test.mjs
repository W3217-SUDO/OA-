// 10.22 批次任务 D：案件详情第 4、5、9（刑事 + 法律顾问）、10、12、13、14、15、16、18 行聚焦回归。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const loadModule = (path, stubs = {}) => {
  const compiled = ts.transpileModule(read(path), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  const fakeRequire = (name) => stubs[name] ?? new Proxy({}, { get: (_target, key) => (key === "__esModule" ? true : () => null) });
  new Function("exports", "require", "module", compiled)(module.exports, fakeRequire, module);
  return module.exports;
};

const page = read("../src/legal/CaseCenterPage.tsx");
const wizard = read("../src/legal/CaseCreateWizard.tsx");
const fees = read("../src/legal/CaseDetail/CaseFeesPanel.tsx");
const header = read("../src/legal/CaseDetail/CaseDetailHeader.tsx");
const workflow = read("../src/legal/services/workflowActions.tsx");
const css = read("../src/case-center.css");
const systemLogs = read("../src/legal/CaseDetail/CaseSystemLogsPanel.tsx");
const createPayload = read("../src/caseSecondBatchParity.ts");

test("第4行：内部结算不再显示“通知日期”列和底部“修改通知日期”按钮", () => {
  const internal = fees.slice(fees.indexOf("// internal"));
  assert.ok(!internal.includes("通知日期"), "内部结算分支不应再出现通知日期");
  assert.match(internal, /scroll=\{\{x:1000\}\}/);
  const external = fees.slice(0, fees.indexOf("// internal"));
  // BUG20261028015：律所、平台“其他操作”里的修改通知日期等八项也已按用户要求去掉。
  for (const label of ["新建费用通知", "费用通知解锁", "关联费用信息", "删除费用通知", "修改通知日期", "到账确认", "查看票据文件", "查看发票文件"]) {
    assert.ok(!external.includes(`label:"${label}"`), `律所、平台“其他操作”不应再有${label}`);
  }
  assert.equal((external.match(/label:"移到其他案子"/g) || []).length, 2, "其余功能保留");
});

test("第5行：标签栏固定、内容区滚动，律所费用与系统日志表头吸顶；手机端关闭吸顶", () => {
  assert.match(fees, /className="case-firm-fees-table" resizable=\{false\} sticky/);
  assert.match(systemLogs, /<Table rowKey="id" size="small" sticky/);
  assert.match(css, /case-detail-tab-area>\.ant-tabs>\.ant-tabs-body-holder\{min-height:0;flex:1 1 auto;overflow:auto/);
  const mobile = css.slice(css.lastIndexOf("/* 手机端关闭吸顶"));
  assert.match(mobile, /@media\(max-width:767px\)/);
  assert.match(mobile, /\.ant-table-sticky-holder\{position:static!important\}/);
  const resizable = read("../src/components/ResizableTable.tsx");
  assert.match(resizable, /props\.sticky \?\? \(scroll\?\.x !== undefined \? \{ offsetScroll: 0 \} : undefined\)/, "共享组件默认不变");
});

test("第9/10行：案由搜索控件按关键词联想，保留字典外历史值", () => {
  const { filterCauseOptions } = loadModule("../src/legal/CauseSearchInput.tsx");
  const options = [
    { value: "侵害商标权纠纷", label: "侵害商标权纠纷" },
    { value: "抢劫枪支、弹药、爆炸物、危险物质罪", label: "抢劫枪支、弹药、爆炸物、危险物质罪" },
    { value: "抢劫罪", label: "抢劫罪" },
    { value: "抢劫罪", label: "抢劫罪" },
  ];
  assert.deepEqual(filterCauseOptions(options, "抢劫").map((item) => item.value), ["抢劫枪支、弹药、爆炸物、危险物质罪", "抢劫罪"]);
  assert.equal(filterCauseOptions(options, "").length, 3);
  assert.equal(filterCauseOptions(options, "抢劫", 1).length, 1);
  const control = read("../src/legal/CauseSearchInput.tsx");
  assert.match(control, /<AutoComplete/, "输入框 + 联想，允许保存字典外文本（历史罪名可回显）");
  assert.match(wizard, /isCriminalCreate\?<CauseSearchInput placeholder="输入关键词搜索罪名" options=\{causeOptions\} \/>/);
  assert.match(page, /editingNormalCase\?\.data\.case_type === "刑事案件" \? <CauseSearchInput placeholder="输入关键词搜索罪名\/案由" options=\{causeOptions\} \/> : <Input\/>/);
});

test("第9行法律顾问：新建与修改基本信息新增选填案由，提交时不再清空", () => {
  assert.match(wizard, /isCounselCreate && <><Form\.Item label="顾问类型"[\s\S]*?<Form\.Item label="案由" name="cause_or_charge"><CauseSearchInput/);
  assert.ok(!/label="案由" name="cause_or_charge" rules/.test(wizard.slice(wizard.indexOf("isCounselCreate && <><Form.Item"), wizard.indexOf("顾问期限"))), "法律顾问案由选填");
  assert.match(createPayload, /\n  cause_or_charge: text\(draft\.cause_or_charge\),/);
  assert.match(page, /<Form\.Item label="案由" name="cause_or_charge"><CauseSearchInput placeholder="选填，输入关键词搜索案由"/);
  const saveCounsel = workflow.slice(workflow.indexOf("const saveCounselBasic"), workflow.indexOf("const openNormalCaseEdit"));
  assert.match(saveCounsel, /cause_or_charge: String\(values\.cause_or_charge \|\| ""\)\.trim\(\)/);
});

test("第12/13行：刑事操作菜单只剩一个修改法院信息，检察院按一审/二审/再审子菜单逐级维护", () => {
  const menu = page.slice(page.indexOf("const caseDetailPrimaryActionButtons"), page.indexOf("const companyScheduleCourtLevelLabel"));
  assert.ok(!menu.includes('openCriminalMaintenance(viewingCounselCase, "courts")'), "删除刑事专用法院入口");
  assert.equal((menu.match(/primaryOperationLabels\[5\]/g) || []).length, 1);
  assert.match(menu, /data-testid="case-detail-procuratorate-submenu"/);
  assert.match(menu, /openCriminalMaintenance\(viewingCounselCase, "procuratorates", level\)/);
  const { criminalProcuratorateFields, CRIMINAL_PROCURATORATE_LEVELS } = loadModule("../src/legal/services/workflowActions.tsx");
  assert.deepEqual(CRIMINAL_PROCURATORATE_LEVELS.map(([, label]) => label), ["一审", "二审", "再审"]);
  assert.deepEqual(criminalProcuratorateFields("second").map((item) => item.label), ["二审检察机关名称", "检察院案号", "地址", "经办人", "联系方式"]);
  assert.deepEqual(criminalProcuratorateFields("retrial").map((item) => item.name), ["retrial_procuratorate_name", "retrial_procuratorate_case_no", "retrial_procuratorate_address", "retrial_procuratorate_operator", "retrial_procuratorate_phone"]);
  assert.match(page, /title=\{criminalMaintenance\?\.kind==="procuratorates"\?"检察院信息"/);
  assert.match(page, /criminalMaintenance\?\.kind!=="procuratorates"&&<Form\.Item label="修改说明"/);
  const save = workflow.slice(workflow.indexOf("const saveCriminalMaintenance"), workflow.indexOf("const saveCaseParty"));
  assert.match(save, /criminalProcuratorateFields\(level\)\.map/, "只提交当前审级字段");
});

test("第15/18行：刑事详情按旧系统显示案件信息，并有公安机关/检察机关/法院信息三个窗口", () => {
  const { criminalVictimNames, criminalProcuratorateLevelValues } = loadModule("../src/legal/CaseDetail/CaseDetailHeader.tsx");
  const names = (value) => (Array.isArray(value) ? value.join("、") : String(value || ""));
  assert.equal(criminalVictimNames({ plaintiffs: ["张三", "李四"], customer: "客户甲" }, names), "张三、李四");
  assert.equal(criminalVictimNames({ plaintiffs: [], plaintiff: "" }, names), "—", "原告为空显示“—”，不回退客户");
  assert.equal(criminalProcuratorateLevelValues({ last_procuratorate_name: "旧再审院" }, "retrial").name, "旧再审院");
  const criminal = header.slice(header.indexOf("{isCriminal ? <table"), header.indexOf(": <table className=\"case-legacy-summary\""));
  for (const label of ["我方案号", "罪名", "受害人", "案件名称", "案件阶段", "受害人代理人", "客户", "经办律师", "被告/犯罪嫌疑人", "合同号", "律师助理", "被告代理人", "案源日期", "案件来源"]) {
    assert.ok(criminal.includes(`<th>${label}</th>`), `刑事案件信息缺少 ${label}`);
  }
  for (const label of ["起诉案由", "原告", "第三人", "开庭律师", "诉讼标的"]) assert.ok(!criminal.includes(`<th>${label}</th>`), `刑事案件信息不应显示 ${label}`);
  assert.match(header, /title="公安机关"/);
  assert.match(header, /title="检察机关"/);
  assert.ok(header.indexOf('title="公安机关"') < header.indexOf('title="检察机关"') && header.indexOf('title="检察机关"') < header.indexOf('aria-label="法院信息"'));
});

test("第16行：右侧栏与案件信息并列，案件提醒在案件日志上方，可新增/删除并在打开详情时加载", () => {
  const workbench = page.slice(page.indexOf('case-detail-split-workbench">'), page.indexOf("<CaseClueContextPanel"));
  assert.ok(workbench.indexOf("case-detail-main-column") < workbench.indexOf("<CaseDetailHeader"));
  const aside = workbench.slice(workbench.indexOf('<aside className="case-detail-side-panel"'));
  assert.ok(aside.indexOf("案件提醒") < aside.indexOf("案件日志"));
  assert.match(aside, /can_create_reminder[\s\S]*?setReminderOpen\(true\)/);
  assert.match(aside, /deleteCounselReminder\(item\)/);
  assert.match(page, /<Modal open=\{reminderOpen\} title=\{`新增案件提醒：/);
  assert.match(workflow, /api\.get\(`\/cases\/\$\{caseId\}\/reminders`\)/);
  assert.match(workflow, /void loadCounselSidePanel\(row\.id\)/);
  assert.match(workflow, /api\.delete\(`\/cases\/\$\{caseId\}\/reminders\/\$\{reminder\.id\}`\)/);
  assert.match(css, /\.case-detail-drawer \.case-detail-split-workbench\{display:grid;grid-template-columns:minmax\(0,1fr\) 260px/);
});

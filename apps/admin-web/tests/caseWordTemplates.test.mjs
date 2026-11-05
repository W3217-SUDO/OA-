// 按固定模板生成文书（陶国南 11-03）：说“生成撤诉申请书”打开模板，不让智能体改写；管理员在智能体设置维护模板。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const loadMatch = () => {
  const output = ts.transpileModule(read("../src/legal/caseWordTemplateMatch.ts"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(output, { module, exports: module.exports });
  return module.exports;
};

test("“生成撤诉申请书”这类话打开对应模板，普通问题仍交给智能体", () => {
  const { matchWordTemplate } = loadMatch();
  const templates = [
    { id: "w", name: "撤诉申请书", is_active: true }, { id: "s", name: "申请书", is_active: true }, { id: "off", name: "起诉状", is_active: false },
  ];
  assert.equal(matchWordTemplate("生成撤诉申请书", templates).id, "w", "名字长的优先");
  assert.equal(matchWordTemplate("帮我出一份撤诉申请书", templates).id, "w");
  assert.equal(matchWordTemplate("撤诉申请书一般要写什么？", templates), null, "没说生成的不拦截");
  assert.equal(matchWordTemplate("生成起诉状", templates), null, "停用的模板不打开");
});

test("案件智能体输入区有“按模板生成文书”按钮，发送前先判断是不是要生成文书", () => {
  const drawer = read("../src/legal/CaseAgentDrawer.tsx");
  assert.match(drawer, /title="按模板生成文书"/);
  assert.match(drawer, /void sendOrGenerate\(\);/);
  assert.match(drawer, /<CaseWordTemplateModal caseId=\{agentCase\?\.id \?\? null\}/);
  assert.match(read("../src/case-center.css"), /\.case-agent-composer\{position:relative;display:grid;grid-template-columns:36px 36px minmax\(0,1fr\) 40px;/);
});

test("生成弹窗：字段可改，缺字段不能保存，预览后确认才存进案件空间", () => {
  const modal = read("../src/legal/CaseWordTemplateModal.tsx");
  assert.match(modal, /documents\/word-templates\/\$\{selected\}/);
  assert.match(modal, /api\.post(<[^>]+>)?\(`\$\{base\}\/generate`, \{ values: edited \}\)/);
  assert.match(modal, /disabled=\{!preview \|\| !!missing\.length \|\| !!busy\}/);
  assert.match(modal, /正文不会被改写，只替换这些字段/);
});

test("智能体设置有“文书模板”标签：上传、替换文件、停用、常用选项、逻辑删除", () => {
  assert.match(read("../src/AgentAdminPage.tsx"), /\{ key: "word-templates", label: "文书模板"/);
  const admin = read("../src/capability-market/CaseWordTemplatesAdmin.tsx");
  for (const call of ['api.post<WordTemplate>("/case-word-templates", form)', "api.put<WordTemplate>(`/case-word-templates/${target.id}/file`, form)",
    "api.patch(`/case-word-templates/${item.id}`, { is_active: checked })", "api.delete(`/case-word-templates/${item.id}`)"]) assert.ok(admin.includes(call), call);
  assert.doesNotMatch(read("../src/case-center.css").split("按模板生成文书（陶国南 11-03）")[1], /color-mix\(|:has\(|@container|dvh/);
});

test("上传范本后核对“识别到的字段 → 案件里哪一项”，对不上的设成生成时手填", () => {
  const admin = read("../src/capability-market/CaseWordTemplatesAdmin.tsx");
  assert.match(admin, /api\.patch\(`\/case-word-templates\/\$\{mappingFor\.id\}`, \{ mapping \}\)/);
  assert.match(admin, /\{ value: MANUAL, label: "生成时手填" \}/);
  assert.match(admin, /if \(created\) openMapping\(created\);/, "上传后直接打开核对");
  assert.match(admin, /要替换的文字加下划线，紧跟着用括号写说明/);
});

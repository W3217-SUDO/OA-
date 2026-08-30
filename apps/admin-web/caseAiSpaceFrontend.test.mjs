import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("every case renders the fixed AI workspace folder", () => {
  assert.match(source, /label:"AI空间",category:"AI空间",type:"folder"/);
  assert.match(source, /item\.category==="AI空间"\?<RobotOutlined/);
});

test("AI workspace supports draft creation editing deletion and promotion", () => {
  assert.match(source, />新建 Word 文档</);
  assert.match(source, /openEditAiDraft/);
  assert.match(source, /deleteAiDraft/);
  assert.match(source, />转入正式系统</);
  assert.match(source, /AI空间是案件草稿箱/);
});

test("AI chat can generate a Word document directly into the case AI workspace", () => {
  assert.match(source, /isAiWordGenerationRequest/);
  assert.match(source, /aiWordDocumentName/);
  assert.match(source, /explicitTitle/);
  assert.match(source, /Word 文档已生成到 AI 空间/);
  assert.match(source, /AI文档-\$\{dayjs\(\)\.format\("YYYYMMDD-HHmm"\)\}\.docx/);
  assert.match(source, /新建 AI 空间 Word 文档/);
  assert.match(source, /isAiWordGenerationRequest\(content\) \? "legal-document-drafting" : agentSkillId/);
  assert.match(source, /encodeAgentSkillMessage\(effectiveSkillId, content\)/);
  assert.match(source, /起诉状/);
  assert.match(source, /模型本轮生成失败，请点击重新发送；案件材料和已发送问题不会丢失/);
});

test("AI drafts are excluded from the formal case document aggregate", () => {
  assert.match(source, /nonCaseDocumentCategories=\["AI空间","客户文档","合同文档"/);
  assert.match(source, /activeCounselDocCategory==="AI空间"/);
});

test("AI drafts can be promoted into every fixed formal case folder", () => {
  assert.match(source, /fixedFormalCaseDocumentOptions=AGENT_CASE_DOCUMENT_FOLDERS\.map/);
  assert.match(source, /api\.get\(`\/cases\/\$\{viewingCounselCase\.id\}\/document-folders`\)/);
  assert.match(source, /options=\{aiDraftPromoteOptions\}/);
  assert.match(source, /setAiDraftPromoteOptions\(options\)/);
  assert.match(source, /setCounselDocumentFolderTree/);
  assert.match(source, /counselDocumentFolderTree\.find\(option=>option\.value==="案件文档全部"\)/);
});

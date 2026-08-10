import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');
const styles = fs.readFileSync(new URL('./src/case-center.css', import.meta.url), 'utf8');

test('case detail exposes the LangGraph case agent panel', () => {
  assert.match(source, /<Button type="primary" icon=\{<RobotOutlined \/>\} onClick=\{\(\) => openCaseAgent\(viewingCounselCase\)\}>案件智能体<\/Button>/);
  assert.match(source, /data-testid="case-agent-panel"/);
  assert.match(source, /\/case-spaces\/\$\{row\.id\}\/agent\/status/);
  assert.match(source, /\/case-spaces\/\$\{row\.id\}\/agent\/state/);
  assert.match(source, /\/case-spaces\/\$\{agentCase\.id\}\/agent\/messages/);
});

test('agent messages persist in the case thread and can be sent from the panel', () => {
  assert.match(source, /agentState\?\.messages\?\.map/);
  assert.match(source, /onPressEnter=/);
  assert.match(source, /概括案件现状/);
  assert.match(source, /检查最近期限风险/);
  assert.match(source, /汇总合同与费用/);
  assert.match(styles, /\.case-agent-message-user/);
  assert.match(styles, /\.case-agent-message-assistant/);
});

test('agent write proposals remain behind explicit human approval', () => {
  assert.match(source, /\/agent\/actions\/\$\{action\.id\}\/decision/);
  assert.match(source, /批准只记录人工审批决定，当前不会自动改写案件业务数据/);
  assert.match(source, /decideCaseAgentAction\(action, "approved"\)/);
  assert.match(source, /decideCaseAgentAction\(action, "rejected"\)/);
  assert.match(source, /disabled=\{!counselDetailCapabilities\.can_write\}/);
});

test('case drawer uses the shared office skill router', () => {
  assert.match(source, /case-agent-skill-select/);
  assert.match(source, /encodeAgentSkillMessage\(agentSkillId, content\)/);
  assert.match(source, /agentStatus\?\.skills/);
  assert.match(styles, /\.case-agent-skill-select/);
});

test('case drawer can upload and analyze screenshot evidence', () => {
  assert.match(source, /uploadCaseAgentScreenshot/);
  assert.match(source, /attachment_ids: agentScreenshots\.map/);
  assert.match(source, /form\.append\("record_id", String\(agentCase\.id\)\)/);
  assert.match(source, /智能体截图证据/);
  assert.match(styles, /\.case-agent-screenshot-bar/);
  assert.match(source, /preview_url: previewUrl/);
  assert.match(source, /case-agent-composer-attachments/);
  assert.match(source, /clipboardData\.items[\s\S]*?getAsFile\(\)/);
  assert.match(source, /if \(agentSkillId !== "screenshot-evidence"\) setAgentSkillId\("screenshot-evidence"\)/);
  assert.match(source, /onPaste=\{pasteCaseAgentScreenshot\}/);
  assert.match(source, /可上传或直接粘贴截图/);
  assert.match(source, /case-agent-message-attachments[\s\S]*?<img src=\{attachment\.preview_url\}/);
  assert.match(styles, /\.case-agent-composer-attachments/);
});

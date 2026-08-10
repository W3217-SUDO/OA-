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

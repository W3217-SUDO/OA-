import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), 'utf8');

test('智能体设置有“DSH API 配置”标签，只给系统管理员（陶威 11-03）', () => {
  const page = read('../src/AgentAdminPage.tsx');
  assert.match(page, /\.\.\.\(isSystemAdmin \? \[\{ key: "dsh-api", label: "DSH API 配置"/);
  assert.match(page, /tab === "dsh-api" && isSystemAdmin && <DshModelProviders/);
});

test('服务商可新增、编辑、删除、切换、测试连接；Key 用密码框、留空不改、不回显', () => {
  const panel = read('../src/capability-market/DshModelProviders.tsx');
  for (const call of ['api.post<ProvidersState>(BASE, body)', 'api.put<ProvidersState>(`${BASE}/', 'api.delete<ProvidersState>(`${BASE}/',
    'api.post<ProvidersState>(`${BASE}/activate`', '`${BASE}/${item.id}/test`']) assert.ok(panel.includes(call), call);
  assert.match(panel, /<AutoComplete maxLength=\{120\}/);
  assert.match(panel, /<Input\.Password maxLength=\{500\} autoComplete="new-password" visibilityToggle=\{false\} \/>/);
  assert.match(panel, /已保存的 Key 不显示；留空表示不修改。/);
  assert.doesNotMatch(panel, /api_key\s*\}/, '列表不展示 Key 字段');
  assert.doesNotMatch(read('../src/capability-market/dsh-plugin-center.css').split('.dsh-provider-list { display')[1], /color-mix|:has\(|@container|dvh/, '新样式兼容钉钉 Chrome 100');
});

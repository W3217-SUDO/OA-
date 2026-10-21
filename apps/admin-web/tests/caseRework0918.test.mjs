import { test } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { create, act } from 'react-test-renderer';
import { load, courtPayloads } from './caseRework0918.helpers.mjs';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const clue = (id, serial_no) => ({ id, serial_no, title: '线索' });

test('真实法院保存动作仅提交当前审级', courtPayloads);

test('线索输入建议、重新打开刷新、过期请求取消、保留选中名称及错误提示', async () => {
  const calls = [];
  const { CaseClueSelect } = await load('../src/legal/CaseClueSelect.tsx', { get: (path, config) => new Promise((resolve, reject) => calls.push({path, config, resolve, reject})) });
  let root;
  await act(async () => { root = create(React.createElement(CaseClueSelect, { caseId: 10, value: [1] })); });
  await act(async () => { await wait(10); });
  const props = () => root.root.findByType('select-probe').props;
  await act(async () => { calls[0].resolve({data:{items:[clue(1,'已选'),clue(2,'M甲')]}}); });
  assert.equal(props().options.length,2);
  await act(async () => { props().onSearch('M'); });
  await act(async () => { await wait(280); });
  const old = calls.at(-1); assert.equal(old.config.params.keyword,'M');
  await act(async () => { props().onSearch('M乙'); });
  assert.equal(old.config.signal.aborted,true);
  await act(async () => { await wait(280); });
  await act(async () => { calls.at(-1).resolve({data:{items:[clue(3,'M乙')]}}); old.resolve({data:{items:[clue(2,'M甲')]}}); });
  assert.deepEqual(props().options.map(x=>x.value),[3,1]);
  assert.match(props().options.find(x=>x.value===1).label,/已选/);
  await act(async () => { props().onOpenChange(true); });
  await act(async () => { await wait(10); });
  assert.equal(calls.at(-1).config.params.keyword,'');
  await act(async () => { calls.at(-1).resolve({data:{items:[clue(1,'已选')]}}); });
  assert.match(props().notFoundContent,/暂无符合条件/);
  assert.match(props().popupRender(null).props.children.props.children,/同客户、已取证且未生成案件/);
  await act(async () => { props().onOpenChange(true); });
  await act(async () => { await wait(10); });
  await act(async () => { calls.at(-1).reject({response:{data:{detail:'无权访问'}}}); });
  assert.equal(props().notFoundContent,'无权访问');
  await act(async () => { root.update(React.createElement(CaseClueSelect, {caseId:11,value:[]})); });
  await act(async () => { await wait(10); });
  assert.equal(calls.at(-1).path,'/cases/11/clue-candidates');
  assert.equal(props().options.length,0);
  const pending=calls.at(-1);
  await act(async () => { root.unmount(); });
  assert(pending.config.signal.aborted);
});

test('新建当事人输入同步收录、去重、删除证件及切换创建流程清空输入', async () => {
  const { useCaseCreatePartyInputs } = await load('../src/legal/useCaseCreatePartyInputs.ts', {});
  const values = { defendants: ['已有被告'], defendant_identities: [{ name: '已有被告', identity_no: '旧证件' }] };
  const form = { getFieldValue: key => values[key], setFieldsValue: patch => Object.assign(values, patch) };
  let inputs, root;
  function Probe({ token }) { inputs = useCaseCreatePartyInputs(form, token); return null; }
  await act(async () => { root = create(React.createElement(Probe, { token: 'first' })); });
  try {
    await act(async () => {
      inputs.selectProps('defendants').onOpenChange(true);
      inputs.selectProps('defendants').onSearch(' 新被告，已有被告,第二名新被告 ');
      inputs.commitInputs();
      assert.deepEqual(values.defendants, ['已有被告', '新被告', '第二名新被告']);
    });
    assert.equal(inputs.selectProps('defendants').searchValue, '');
    assert.equal(inputs.selectProps('defendants').open, false);
    await act(async () => {
      inputs.selectProps('defendants').onSearch('离焦新增');
      inputs.selectProps('defendants').onBlur();
    });
    assert(values.defendants.includes('离焦新增'));
    await act(async () => {
      inputs.selectProps('defendants').onSearch('回车新增');
      inputs.selectProps('defendants').onChange([...values.defendants, '回车新增']);
      inputs.commitInputs();
    });
    assert.equal(values.defendants.filter(name => name === '回车新增').length, 1);
    await act(async () => { inputs.selectProps('defendants').onChange(['新被告']); });
    assert.deepEqual(values.defendant_identities, []);
    await act(async () => {
      inputs.selectProps('plaintiffs').onSearch('新增原告');
      inputs.selectProps('third_parties').onSearch('新增第三人');
      inputs.selectProps('defendant_agents').onSearch('新增代理人');
      inputs.commitInputs();
    });
    assert.deepEqual(values.plaintiffs, ['新增原告']);
    assert.deepEqual(values.third_parties, ['新增第三人']);
    assert.deepEqual(values.defendant_agents, ['新增代理人']);
    await act(async () => { inputs.selectProps('defendants').onSearch('不应带入下一案件'); });
    await act(async () => { root.update(React.createElement(Probe, { token: 'second' })); });
    await act(async () => { inputs.commitInputs(); });
    assert.deepEqual(values.defendants, ['新被告']);
    assert.equal(inputs.selectProps('defendants').searchValue, '');
  } finally { await act(async () => { root.unmount(); }); }
});

test('分类当事人进入下一步及最终保存，分类缺失和提交失败不前进', async () => {
  const requests = [], messages = [], steps = [], completed = [];
  const values = { case_parties: [] };
  const form = { getFieldValue: key => values[key], getFieldsValue: () => ({ ...values }) };
  let apiError;
  const { createCaseWorkflowActions } = await load('../src/legal/services/workflowActions.tsx', {
    put: async (path, body) => { if(apiError) throw {response:{data:{detail:apiError}}}; requests.push({path,body}); return {data:{}}; },
  }, messages);
  const actions = createCaseWorkflowActions({createForm:form,createdCaseId:42,createStep:1,isCounselCreate:false,
    setCreateSubmitting(){},setCreateStep:step=>steps.push(step),redirectAfterCreate:()=>completed.push(true)});
  await actions.saveLitigants(false);
  assert.equal(requests.length,0);
  assert.match(messages.at(-1),/分类/);
  values.case_parties = [
    {name:'委托客户',party_standpoint:'我方',party_type:'当事人',is_client_principal:true,related_client_id:10,subject_kind:'自然人',credit_code:'',litigation_status:'原告'},
    {name:'对方主体',party_standpoint:'对方',party_type:'当事人',is_client_principal:false,subject_kind:'自然人',credit_code:'',litigation_status:'被告'},
  ];
  await actions.advanceCreateStep();
  assert.deepEqual(steps,[2]);
  assert.deepEqual(requests.at(-1).body.defendants,['对方主体']);
  assert.equal(requests.at(-1).body.case_parties[0].related_client_id,10);
  assert.equal(requests.at(-1).body.case_parties[1].party_standpoint,'对方');
  await actions.saveLitigants(true);
  assert.deepEqual(requests.slice(-2).map(item=>item.path),['/cases/42/litigants','/cases/42/judicial']);
  assert.equal(completed.length,1);
  apiError='对方诉讼地位应与我方镜像一致';
  await actions.saveLitigants(false);
  assert.equal(messages.at(-1),apiError);
  assert.deepEqual(steps,[2]);
  assert.equal(completed.length,1);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { create, act } from 'react-test-renderer';
import { build } from 'esbuild';
import Module, { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import ts from 'typescript';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const noop = () => {};
async function load(entry, api = {}) {
  const result = await build({ entryPoints: [fileURLToPath(new URL(entry, import.meta.url))], bundle: true, write: false, platform: 'node', format: 'cjs', packages: 'external', loader: { '.css': 'empty' }, plugins: [{ name: 'isolated-detail-ui', setup(builder) {
    builder.onResolve({ filter: /\/api$/ }, () => ({ path: 'api', namespace: 'test' }));
    builder.onResolve({ filter: /^react$/ }, () => ({ path: 'react', external: true }));
    builder.onResolve({ filter: /^antd$/ }, () => ({ path: 'antd', namespace: 'test' }));
    builder.onResolve({ filter: /(?:^|\/)ResizableTable$/ }, () => ({ path: 'table', namespace: 'test' }));
    builder.onLoad({ filter: /^table$/, namespace: 'test' }, () => ({ contents: 'export default "Table";' }));
    builder.onLoad({ filter: /.*/, namespace: 'test' }, ({ path }) => ({ contents: path === 'api' ? 'export const api=globalThis.__detailApi;' : `import React from 'react'; export const Alert='Alert',Button='Button',Card='Card',Checkbox='Checkbox',Descriptions='Descriptions',Divider='Divider',Drawer='Drawer',Empty='Empty',Input=Object.assign('Input',{}),Modal='Modal',Pagination='Pagination',Popconfirm='Popconfirm',Select='Select',Space='Space',Spin='Spin',Table='Table',Tabs='Tabs',Tag='Tag',Timeline='Timeline',Upload='Upload'; export const Form=Object.assign((props)=>React.createElement('Form',props),{Item:'FormItem'}); export function Collapse(props){return React.createElement('Collapse',props,props.items.map(item=>React.createElement('Section',{key:item.key,label:item.label},item.children)));}` }));
  } }] });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL('.', import.meta.url)));
  target.require = createRequire(import.meta.url);
  globalThis.__detailApi = api;
  try { target._compile(result.outputFiles[0].text, fileURLToPath(import.meta.url)); return target.exports; }
  finally { delete globalThis.__detailApi; }
}
function walk(node, predicate) {
  if (!node || typeof node !== 'object') return [];
  return [...(predicate(node) ? [node] : []), ...React.Children.toArray(node.props?.children).flatMap(child => walk(child, predicate))];
}
const customerProps = () => new Proxy({ initialView: 'customer-mine', customer: { id: 1, title: 'CODEX-929-R04客户', serial_no: '客户001', owner: '本人', status: '签约', data: { contacts: [], contract_count: 2 } }, detailTab: 'contacts', directory: [], customerTypeOptions: [], events: [], customerEvents: [], attachments: [], sharedObjects: [], canManage: false, documentFileRef: { current: null } }, { get: (object, key) => key in object ? object[key] : key.startsWith('on') ? noop : undefined });

test('R4 客户整页和抽屉移除两个历史标签，保留真实联系人、合同、文档入口', async () => {
  for (const [path, name] of [['CustomerDetailView','CustomerDetailView'], ['CustomerDetailDrawer','CustomerDetailDrawer']]) {
    const module = await load(`../src/crm/${path}.tsx`);
    const element = module[name](customerProps());
    const tabs = walk(element, node => node.type === 'Tabs')[0].props.items;
    assert(!tabs.some(tab => ['legacy-contract-history', 'legacy-customer-history'].includes(tab.key)));
    for (const required of ['contacts', 'contracts', 'documents', 'events']) assert(tabs.some(tab => tab.key === required));
    assert.equal(tabs.find(tab => tab.key === 'contracts').label, '合同（2）');
  }
});

test('R5–7 合同仅四标签，六项基本信息和13项财务按组保留，三张财务表只属于合同标的', async () => {
  const { ContractDetailView } = await load('../src/contract/ContractDetailView.tsx');
  const data = Object.fromEntries(['official_paid','official_received','official_unreceived','official_loss','agency_total','agency_received','agency_due','other_total','other_paid','other_due','invoice_opened','invoice_should','invoice_excess'].map((key,index) => [key,index+1]));
  const props = new Proxy({ viewing: { id: 1, status: '草稿', serial_no: 'CODEX-929-R06', title: '合同', customer: '客户', owner: '本人', data }, isContractDetailView: true, detailActiveTab: 'objects', contractObjects: [], objectPage: 1, objectPageSize: 15, objectCases: [], viewingAttachments: [], selectedAttachmentKeys: [], contractEvents: [], contractWorkflowEvents: [], contractEventPage: 1, contractEventPageSize: 15, contractEventTotal: 0, detailApprovals: [], detailReceipts: [], detailInvoices: [], detailPayments: [], detailContractCapabilities: { canEdit: true }, personName: String, peopleNames: String }, { get: (object,key) => key in object ? object[key] : key.startsWith('on') ? noop : undefined });
  const tree = ContractDetailView(props);
  const changes=[];
  props.onTabChange=key=>changes.push(key);
  const wired=ContractDetailView(props);
  const tabNode=walk(wired,node=>node.props?.sections)[0];
  for(const key of ['objects','events','attachments','approvals']) tabNode.props.onChange(key);
  assert.deepEqual(changes,['objects','events','attachments','approvals']);
  const tabs = walk(tree, node => node.props?.sections)[0].props.sections;
  assert.deepEqual(tabs.map(item => item.key), ['objects','events','attachments','approvals']);
  const basic = walk(tree, node => node.props?.className === 'contract-detail-summary')[0];
  assert.equal(React.Children.count(basic.props.children),6);
  const groups = walk(tree, node => node.props?.className === 'contract-detail-finance-group');
  assert.deepEqual(groups.map(group => React.Children.count(group.props.children)), [4,3,3,3]);
  const amounts = groups.flatMap(group => walk(group, node => node.type === 'b').map(node => node.props.children));
  assert.deepEqual(amounts, Array.from({ length:13 },(_,index) => Number(index+1).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})));
  for (const tab of tabs) assert.equal(walk(tab.children, node => node.type?.name === 'ContractFinancialRecords').length, tab.key === 'objects' ? 1 : 0);
  const attachment={id:9,original_name:'保留附件.pdf'};
  const actions=[];
  props.viewingAttachments=[attachment];
  props.onPreviewAttachment=file=>actions.push(['preview',file.id]);
  props.onDownloadAttachment=file=>actions.push(['download',file.id]);
  const attachmentTab=walk(ContractDetailView(props),node=>node.props?.sections)[0].props.sections.find(tab=>tab.key==='attachments');
  const attachmentTable=walk(attachmentTab.children,node=>node.type==='Table')[0];
  const controls=attachmentTable.props.columns.find(column=>column.title==='操作').render(null,attachment);
  const buttons=walk(controls,node=>node.type==='Button');
  buttons.find(node=>node.props.children==='预览').props.onClick();
  buttons.find(node=>node.props.children==='下载').props.onClick();
  assert.deepEqual(actions,[['preview',9],['download',9]]);
  let rendered;
  await act(async()=>{rendered=create(tabs[0].children);});
  assert.deepEqual(rendered.root.findAllByType('h3').map(node=>node.props.children),['回款记录','开票记录','付款记录']);
  await act(async()=>rendered.unmount());
});

test('R18 本人子任务八列，发布列表原有状态/办理保留，日期使用本子任务而非父授权', () => {
  const source=fs.readFileSync(new URL('../src/investigation/InvestigationCenterPage.tsx',import.meta.url),'utf8');
  const ast=ts.createSourceFile('page.tsx',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
  let declaration;
  function find(node){if(ts.isVariableDeclaration(node)&&node.name.getText(ast)==='columns')declaration=node;ts.forEachChild(node,find);}
  find(ast);
  const body=declaration.initializer.arguments[0].getText(ast);
  const code=ts.transpileModule(`const result=${body};`,{compilerOptions:{target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.React}}).outputText;
  function columns(initialTab){return new Function('initialTab','React','Button','Tag','Space','personDisplayName','openInvestigationDetail','openLinkedCustomer','openLinkedInvestigation','isActualAdmin','profile','statusColors','openSubtaskAction',code+';return result();')(initialTab,React,'Button','Tag','Space',String,noop,noop,noop,false,{username:'本人'},{},noop);}
  const mine=columns('investigation-task-sub-mine');
  assert.deepEqual(mine.map(column=>column.title),['任务编号','权利人','权利类型','调查员','调查区域','开始时间','结束时间','案源人']);
  assert.equal(columns('investigation-task-sub-published').length,11);
  const row={data:{start_date:'2026-10-01',end_date:'2026-11-01',authorized_from:'2026-01-01',authorized_to:'2026-12-31'}};
  assert.equal(mine.find(column=>column.title==='开始时间').render(null,row),'2026-10-01');
  assert.equal(mine.find(column=>column.title==='结束时间').render(null,row),'2026-11-01');
});

test('R14/15/17/19 任务详情真实关联、分页、错误、重开刷新和取消请求', async () => {
  const parent={id:1,module:'investigation',serial_no:'CODEX-929-R14',title:'父任务',customer:'客户',data:{authorized_from:'2026-01-01',authorized_to:'2026-12-31'},owner:'主管'};
  const child={id:2,module:'task',serial_no:'CODEX-929-R17',title:'子任务',data:{start_date:'2026-10-01',end_date:'2026-11-01'},owner:'调查员'};
  const file={id:10,category:'调查授权书',original_name:'资料.docx',uploader:'发布人',created_at:'2026-09-29'};
  const calls=[]; let fail=false;
  const api={get:async(path,config)=>{calls.push({path,config});if(fail)throw {response:{data:{detail:'真实权限拒绝'}}};const isChild=path.includes('/2/');return {data:{record:isChild?child:parent,parent,materials:[file],items:isChild?[{id:3,module:'clue',serial_no:'CLUE',title:'真实店铺',data:{shop_name:'店铺名称',infringement_method:'销售'}}]:[child],total:isChild?18:1}};}};
  const {default:Component}=await load('../src/investigation/InvestigationTaskDetail.tsx',api);
  let view;
  const props={record:parent,personName:(_name,username)=>username,onOpenCustomer:noop,onOpenClue:noop};
  await act(async()=>{view=create(React.createElement(Component,props));});
  assert.deepEqual(view.root.findAllByType('Section').map(item=>item.props.label),['基本信息','调查资料','调查子任务']);
  const childrenTable=view.root.findAllByType('Table').find(item=>item.props.dataSource[0]?.id===2);
  const link=childrenTable.props.columns[0].render(child.serial_no,child);
  await act(async()=>link.props.onClick());
  assert.deepEqual(view.root.findAllByType('Section').map(item=>item.props.label),['任务信息：CODEX-929-R17','基本信息','调查资料']);
  const clueTable=view.root.findAllByType('Table').find(item=>item.props.pagination.total===18);
  assert.equal(clueTable.props.columns.find(column=>column.title==='店铺名称').render(null,clueTable.props.dataSource[0]),'店铺名称');
  await act(async()=>clueTable.props.pagination.onChange(2,15));
  assert.equal(calls.at(-1).config.params.page,2);
  fail=true;
  await act(async()=>view.root.findAllByType('Button').find(item=>item.props.children==='刷新').props.onClick());
  assert.equal(view.root.findByType('Alert').props.message,'真实权限拒绝');
  const lastSignal=calls.at(-1).config.signal;
  await act(async()=>view.unmount());
  assert.equal(lastSignal.aborted,true);
  fail=false;
  const before=calls.length;
  await act(async()=>{view=create(React.createElement(Component,props));});
  assert.equal(calls.length,before+1);
  await act(async()=>view.unmount());
});

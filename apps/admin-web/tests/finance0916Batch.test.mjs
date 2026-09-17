import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import ts from 'typescript';
const require = createRequire(import.meta.url);
function load(relative) {
  const filename = new URL(relative, import.meta.url);
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
  const module={exports:{}};
  new Function('require','module','exports',compiled)(name => {
    if(name==='../api') return {api:{}};
    if(name==='../moneyColumns') return load('../src/finance/moneyColumns.ts');
    return require(name);
  },module,module.exports);
  return module.exports;
}

test('catalog preserves duplicate labels by stable keys, nests all descendants, edits only active scoped leaves',()=>{
  const {buildFeeTypeTree}=load('../src/finance/FeeTypePicker.tsx');
  const rows=[
    {id:1,code:'A',name:'官费',parent_code:'',selectable:false,expense_scopes:['律所']},
    {id:2,code:'B',name:'官费',parent_code:'',selectable:false,expense_scopes:['律所']},
    {id:3,code:'A1',name:'一审诉讼费',parent_code:'A',selectable:true,expense_scopes:['律所']},
    {id:4,code:'B1',name:'二审诉讼费',parent_code:'B',selectable:true,expense_scopes:['律所']},
    {id:5,code:'-100',name:'请选择官费',parent_code:'',selectable:false,expense_scopes:['律所']},
  ];
  const tree=buildFeeTypeTree(rows);
  assert.deepEqual(tree.slice(0,2).map(row=>row.value),['A','B']);
  assert.equal(tree[0].children[0].title,'一审诉讼费');
  assert.equal(tree[2].disabled,true);
  assert.equal(buildFeeTypeTree(rows,true,'律所')[0].children[0].value,3);
  assert.equal(buildFeeTypeTree(rows,true,'内部')[0].children[0].disabled,true);
});

test('fee type filters expand parents, recognize initialization aliases, and retain name-only history',()=>{
  const {matchesFeeTypeSelection}=load('../src/finance/FeeTypePicker.tsx');
  const catalog={
    items:[
      {id:10,code:'OFFICIAL',name:'官费',base_fee_type:'官方费用',parent_code:'',selectable:false,expense_scopes:[],is_active:true},
      {id:11,code:'OFFICIAL-LITIGATION',name:'诉讼费',parent_code:'OFFICIAL',selectable:false,expense_scopes:[],is_active:true},
      {id:12,code:'OFFICIAL-LITIGATION-FIRST',name:'一审诉讼费',parent_code:'OFFICIAL-LITIGATION',selectable:true,expense_scopes:[],is_active:true},
    ],
    aliases:{'512':{id:12,code:'1101010'}},
  };
  assert.equal(matchesFeeTypeSelection(['OFFICIAL'],catalog,{fee_type_code:'OFFICIAL-LITIGATION-FIRST'}),true);
  assert.equal(matchesFeeTypeSelection(['OFFICIAL'],catalog,{fee_type:'官方费用'}),true);
  assert.equal(matchesFeeTypeSelection(['OFFICIAL'],{items:[],aliases:{}},{fee_type:'官方费用'}),false);
  assert.equal(matchesFeeTypeSelection(['OFFICIAL-LITIGATION-FIRST'],catalog,{fee_type_id:512,fee_type_code:'1101010'}),true);
  assert.equal(matchesFeeTypeSelection(['OFFICIAL-LITIGATION-FIRST'],catalog,{fee_type:'一审诉讼费'}),true);
  assert.equal(matchesFeeTypeSelection(['OFFICIAL-LITIGATION-FIRST'],catalog,{fee_type_id:999,fee_type:'一审诉讼费'}),false);
});

test('financial configured columns align money while preserving non-money text and selection indices',()=>{
  const {createConfiguredColumns}=load('../src/finance/columns/configuredColumns.tsx');
  for(const route of ['finance-settlement-pending','finance-settlement-audit','finance-settlement-payment','finance-settlement-paid','finance-settlement-refused','finance-archive-fee-pending','finance-internal-payment','finance-receipts-query']) {
    const headers=['客户名称','回款金额','已分金额','未分金额','已分官费','已分代理费','已分其他费用','实际结算金额'];
    const columns=createConfiguredColumns({activeRouteConfig:{headers,source:'generalSettlements'},initialView:route, isGeneralSettlementRoute:true,generalSettlementColumnWidths:headers.map(()=>120),cellValue:(row,header)=>row[header]});
    assert.equal(columns.length,headers.length);
    assert.equal(columns[0].align,undefined);
    for(const column of columns.slice(1)) {
      assert.equal(column.align,'right');
      assert.equal(column.className,'finance-money-column');
      assert.equal(column.render(null,{[headers[columns.indexOf(column)]]:'123.45'}),'123.45');
    }
  }
});

test('bank routing and historical labels remain isolated',()=>{
  const {receiptBankCode,matchesReceiptBank}=load('../src/finance/bankReceiptScope.ts');
  for(const bank of ['icbc','citic','boc','cmb']) assert.equal(receiptBankCode(`finance-receipts-${bank}`),bank);
  // The API and UI must both keep unknown-bank receipts out of named bank pages.
  for(const [bank,label] of [['icbc','工商银行'],['citic','中信银行'],['boc','中国银行'],['cmb','招商银行']]) {
    assert.equal(matchesReceiptBank(label,bank),true);
    assert.equal(matchesReceiptBank('',bank),false);
    for(const other of ['icbc','citic','boc','cmb'].filter(code=>code!==bank)) assert.equal(matchesReceiptBank(label,other),false);
  }
});

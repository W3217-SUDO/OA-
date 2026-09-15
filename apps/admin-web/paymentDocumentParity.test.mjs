import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire, Module } from "node:module";
import { fileURLToPath } from "node:url";
import { transformSync } from "esbuild";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
const filename=fileURLToPath(new URL("./src/finance/PaymentDocument.tsx",import.meta.url));
const module=new Module(filename); module.paths=createRequire(import.meta.url).resolve.paths("react");
module._compile(transformSync(readFileSync(filename,"utf8"),{loader:"tsx",jsx:"automatic",format:"cjs"}).code,filename);
const {PaymentDocument}=module.exports;
const group=(id,amount)=>({request_no:id,amount,contract_no:"CONTRACT",contract_name:"合同名称样例",applicant:"申请人样例",payer:"交款人样例",fee_type:"官方费用",items:[{id,case_no:"CASE",fee_type:"官方费用",expense_subtype:"一审诉讼费",amount,current_payment:amount}]});
const render=(row,printing)=>renderToStaticMarkup(React.createElement(PaymentDocument,{row,printing}));
test("print document keeps request groups and legacy voucher fields",()=>{
  const html=render({serial_no:"PK",data:{amount:300,document_groups:[group("REQ-A",100),group("REQ-B",200)]}},true);
  for(const text of ["打包流水号","打印日期","付款总金额","属性","银行账号","官费类型","其他费用类型","交款人","REQ-A","REQ-B","300.00","客户管理人签字","审批人签字","出纳签字"]) assert.ok(html.includes(text),text);
  assert.equal((html.match(/小计/g)||[]).length,2);
});
test("ordinary detail keeps received and current payment distinct",()=>{
  const g=group("REQ",80);g.items[0]={...g.items[0],fee_amount:200,received_amount:120};
  const html=render({data:{document_groups:[g]}},false);
  for(const text of ["审批意见","案源人","单据号","原告","被告","已收","本次支付","费用备注","付款备注","200.00","120.00","80.00"])assert.ok(html.includes(text),text);
});
test("internal details expose base reference actual and requested separately",()=>{
  const html=render({data:{application_items:[{id:1,data:{base_amount:200,reference_commission:20,actual_commission:18,payment_requested_amount:10}}]}},false);
  for(const text of ["基数","参考提成","实际提成","本次支付","200.00","20.00","18.00","10.00"])assert.ok(html.includes(text),text);
});

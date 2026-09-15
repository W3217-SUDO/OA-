import { Button } from "antd";
import { Fragment } from "react";

const show = (value: any) => value === undefined || value === null || value === "" ? "—" : String(value);
const amount = (value: any) => value === undefined || value === null || value === "" ? "—" : Number(value).toFixed(2);
const date = (value: any) => value ? String(value).slice(0, 10) : "—";

export function PaymentDocument({ row, printing, onCase, onContract }: {row:any; printing:boolean; onCase?:(no:string)=>void; onContract?:(no:string)=>void}) {
  const d = row.data || {};
  const internal = Boolean(d.application_items);
  const groups = d.document_groups || [{...d, request_no:row.serial_no, items:d.items || d.lines || [d]}];
  const items = internal ? d.application_items.map((entry:any) => ({...entry.data,id:entry.id})) : groups.flatMap((group:any) => group.items || []);
  const link = (no:any, handler?: (no:string)=>void) => no && handler ? <Button type="link" size="small" onClick={()=>handler(String(no))}>{no}</Button> : show(no);
  const meta = (fields: [string, any][]) => <div className="payment-meta">{fields.map(([label,value]) => <div key={label}><span>{label}：</span>{value ?? "—"}</div>)}</div>;
  if (printing) return <div className="payment-print-document">
    <h2>{show(d.company_name || "上海申浩律师事务所")}　付款申请单</h2>
    <table className="payment-paper"><tbody>
      <tr><th>打包流水号</th><td>{show(d.payment_package_no || "提交时生成")}</td><th>打印日期</th><td>{date(new Date().toISOString())}</td><td colSpan={4}></td></tr>
      <tr><th>收款单位</th><td colSpan={2}>{show(d.payee_display_name || d.payee)}</td><th>付款总金额</th><td>{amount(d.amount)}</td><th>属性</th><td colSpan={2}>{show(groups[0]?.fee_type)}</td></tr>
      <tr><th>银行账号</th><td colSpan={7}>{show(d.account || d.bank_account || d.payee_account)}</td></tr>
      {groups.map((g:any, index:number) => <Fragment key={g.request_no || index}>
        <tr className="payment-group"><th>请款单号</th><td>{show(g.request_no)}</td><th>合同编号</th><td>{show(g.contract_no)}</td><th>合同名称</th><td colSpan={3}>{show(g.contract_name)}</td></tr>
        <tr className="payment-group"><th>案号</th><th>付款金额</th><th>官费类型</th><th>其他费用类型</th><th>申请人</th><th colSpan={3}>交款人</th></tr>
        {(g.items || []).map((item:any,i:number)=><tr key={item.id || i}><td>{show(item.case_no)}</td><td>{amount(item.current_payment ?? item.amount)}</td><td>{["官方费用","官费"].includes(item.fee_type) ? show(item.expense_subtype || item.fee_type) : "—"}</td><td>{["官方费用","官费"].includes(item.fee_type) ? "—" : show(item.expense_subtype || item.fee_type)}</td><td>{show(item.applicant || g.applicant)}</td><td colSpan={3}>{show(item.payer || g.payer)}</td></tr>)}
        <tr><th>备注</th><td colSpan={7}>{show(g.remark || g.description)}</td></tr>
        <tr><th colSpan={3}>小计</th><td colSpan={5}>{amount(g.amount)}</td></tr>
      </Fragment>)}
    </tbody></table>
    <div className="payment-print-signatures"><span>客户管理人签字：</span><span>审批人签字：</span><span>出纳签字：</span></div>
  </div>;
  return <div className="payment-detail-document">
    <h3>{internal ? "申请付款" : "查看请款单"}</h3>
    <div className="payment-progress">{[internal ? "付款信息查看" : "付款信息填写","提交申请","财务审批","财务付款"].map((step,i)=><div key={step} className={i === (row.status === "待审批" ? 2 : 3) ? "active" : ""}>{step}</div>)}</div>
    {internal ? meta([
      ["案件编号",link(d.case_no,onCase)],["案件名称",show(d.case_name || d.case_title)],["合同编号",link(d.contract_no,onContract)],["合同名称",show(d.contract_name)],
      ["客户编号",show(d.customer_no)],["客户名称",show(row.customer)],["客户管理人",show(d.customer_manager)],
      ...["调查提成","案源提成","文书提成","开庭提成"].map(role => [`${role}(已付)`, d.paid_by_role ? amount(d.paid_by_role[role] || 0) : "—"] as [string,any]),
      ["申请编号",show(row.serial_no)],["申请日期",date(d.application_date || row.created_at)],["审批意见",show(d.approval_comment || d.review_comment)],
    ]) : meta([
      ["合同编号",link(d.contract_no,onContract)],["申请日期",date(d.application_date || row.created_at)],["合同名称",show(d.contract_name)],["交款人",show(d.payer_name || d.payer)],
      ["申请编号",show(row.serial_no)],["案源人",show(d.case_source || d.source_person)],["客户名称",show(row.customer)],["备注",show(d.remark || row.description)],
      ["收款单位",show(d.payee_display_name || d.payee)],["开户行",show(d.account_bank || d.bank_name || d.payee_bank || d.bank)],["账号信息",show(d.account || d.bank_account || d.payee_account)],
    ])}
    {!internal && meta([["审批意见",show(d.approval_comment || d.review_comment)],["付款日期",date(d.paid_date || d.payment_date)],["单据号",show(d.invoice_no || d.writeoff_voucher_no)],["付款金额",amount(d.paid_amount ?? d.amount)],["付款备注",show(d.payment_remark || d.writeoff_remark)]])}
    <div className="payment-info-tab">付款信息</div><div className="payment-table-scroll"><table className="payment-details"><thead><tr>{(internal ? ["序号","支付对象","提成类型","基数","参考提成","实际提成","本次支付","备注"] : ["序号","案件类型","原告","被告","案号","费用类型","费用金额","已收","本次支付","最后交款时间","费用备注","付款备注"]).map(t=><th key={t}>{t}</th>)}</tr></thead><tbody>
      {items.map((item:any,i:number)=><tr key={item.id || i}>{(internal ? [i+1,show(item.payee_display_name || item.payee),show(item.commission_type || item.internal_fee_type),amount(item.base_amount),amount(item.reference_commission),amount(item.actual_commission ?? item.amount),amount(item.payment_requested_amount ?? item.amount),show(item.remark)] : [i+1,show(item.case_type),show(item.plaintiff),show(item.defendant),link(item.case_no,onCase),show(item.expense_subtype || item.fee_type),amount(item.fee_amount ?? item.amount),amount(item.received_amount ?? item.cashed_amount),amount(item.current_payment ?? item.amount),date(item.deadline || item.due_date),show(item.fee_remark),show(item.payment_remark)]).map((v:any,j:number)=><td key={j}>{v}</td>)}</tr>)}
    </tbody></table></div>
  </div>;
}

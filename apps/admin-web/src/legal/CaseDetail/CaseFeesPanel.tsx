import { Button,Dropdown,Space,Table } from "antd";
import type { Key } from "react";
import { PLATFORM_AGENCY_FEE_SUBTYPE } from "../../caseRelationConsumption.mjs";
import type { CaseDetailCapabilities,CaseRow } from "../types";

type CaseFeeScope = "firm" | "platform" | "internal";

interface CaseFeesPanelProps {
  scope: CaseFeeScope;
  feeRows: CaseRow[];
  selectedFeeKeys: Key[];
  setSelectedFeeKeys: (keys: Key[]) => void;
  selectedFee?: CaseRow;
  counselDetailCapabilities: CaseDetailCapabilities;
  externalCaseFeeColumns?: any[];
  casePersonDisplayName?: (source: unknown, displayName?: unknown) => React.ReactNode;
  renderCaseFeeEmptyState?: (scope: "律所" | "平台") => React.ReactNode;
  openCaseFeeBySubtype?: (scope: "律所" | "平台", subtype: string) => void;
  openCourtRefund?: (fee: CaseRow) => void;
  requireSingleFee?: (keys: Key[], row: CaseRow | undefined, action: string) => boolean;
  handleExternalFeeOperation?: (keys: Key[], row: CaseRow | undefined, key: string) => Promise<unknown>;
  openCaseCommission?: () => Promise<unknown>;
  canMarkCaseFeeRefundNotRequired?: (row: CaseRow | undefined) => boolean;
  editCaseFee?: (row: CaseRow) => void;
  deleteCaseFee?: (row: CaseRow) => void;
  handleInternalFeeAction?: (action: string) => void;
  openInformDateBatchUpdate?: (keys: Key[]) => void;
}

export const CaseFeesPanel = ({
  scope,
  feeRows,
  selectedFeeKeys,
  setSelectedFeeKeys,
  selectedFee,
  counselDetailCapabilities,
  externalCaseFeeColumns = [],
  casePersonDisplayName,
  renderCaseFeeEmptyState,
  openCaseFeeBySubtype,
  openCourtRefund,
  requireSingleFee,
  handleExternalFeeOperation,
  openCaseCommission,
  canMarkCaseFeeRefundNotRequired,
  editCaseFee,
  deleteCaseFee,
  handleInternalFeeAction,
  openInformDateBatchUpdate,
}: CaseFeesPanelProps) => {
  if (scope === "firm") {
    return (
      <div className="case-legacy-tab-panel">
        <Table rowKey="id" size="small" pagination={{pageSize:10,showSizeChanger:true,showTotal:total=>`共有${total}条`}} scroll={{x:1250}} dataSource={feeRows} locale={{emptyText:renderCaseFeeEmptyState?.("律所")}} rowSelection={{selectedRowKeys:selectedFeeKeys,onChange:setSelectedFeeKeys}} columns={externalCaseFeeColumns}/>
        {feeRows.length>0&&<Space className="case-legacy-bottom-actions">
          {counselDetailCapabilities.can_create_finance&&<Dropdown trigger={["click"]} menu={{items:[{key:"官费",label:"新增官费"},{key:"第三方费用",label:"新增第三方费用"},{key:"代理费",label:"新增代理费"},{key:"其他费用",label:"新增其他费用"},{key:"commission",label:"新建提成(选择代理费)"}],onClick:({key})=>key === "commission" ? void openCaseCommission?.() : openCaseFeeBySubtype?.("律所",key)}}><Button>新增案件费用</Button></Dropdown>}
          {counselDetailCapabilities.can_create_finance&&<Dropdown trigger={["click"]} menu={{items:[{key:"refund",label:"法院退费"},{key:"payment",label:"申请付款"},{key:"invoice",label:"申请开票"},{type:"divider"},{key:"inform",label:"新建费用通知"},{key:"arrival",label:"到账确认"},{key:"bill",label:"上传票据文件"},{key:"download-bill",label:"查看票据文件"},{key:"unlock-inform",label:"费用通知解锁"},{key:"link-inform",label:"关联费用信息"},{key:"delete-inform",label:"删除费用通知"},{type:"divider"},{key:"inform-date",label:"修改通知日期"},{key:"edit",label:"修改"},{key:"delete",label:"删除"},{key:"no-payment",label:"标记不缴费"},...(canMarkCaseFeeRefundNotRequired?.(selectedFee)?[{key:"refund-not-required",label:"标记不再办理退费"}]:[])],onClick:({key})=>key === "refund" ? (selectedFee ? openCourtRefund?.(selectedFee) : requireSingleFee?.(selectedFeeKeys,selectedFee,"办理法院退费")) : void handleExternalFeeOperation?.(selectedFeeKeys,selectedFee,key)}}><Button>其他操作</Button></Dropdown>}
        </Space>}
      </div>
    );
  }

  if (scope === "platform") {
    return (
      <div className="case-legacy-tab-panel">
        <Table rowKey="id" size="small" pagination={{pageSize:10,showSizeChanger:true,showTotal:total=>`共有${total}条`}} scroll={{x:1250}} dataSource={feeRows} locale={{emptyText:renderCaseFeeEmptyState?.("平台")}} rowSelection={{selectedRowKeys:selectedFeeKeys,onChange:setSelectedFeeKeys}} columns={externalCaseFeeColumns}/>
        {feeRows.length>0&&<Space className="case-legacy-bottom-actions">
          {counselDetailCapabilities.can_create_finance&&<Button title="传统模式：新增平台代理费" onClick={()=>openCaseFeeBySubtype?.("平台",PLATFORM_AGENCY_FEE_SUBTYPE)}>传统模式</Button>}
          {counselDetailCapabilities.can_create_finance&&<Dropdown trigger={["click"]} menu={{items:[{key:"官费",label:"新增官费"},{key:"第三方费用",label:"新增第三方费用"},{key:"代理费",label:"新增代理费"},{key:"其他费用",label:"新增其他费用"}],onClick:({key})=>openCaseFeeBySubtype?.("平台",key)}}><Button>新增案件费用</Button></Dropdown>}
          {counselDetailCapabilities.can_create_finance&&<Dropdown trigger={["click"]} menu={{items:[{key:"refund",label:"法院退费"},{key:"payment",label:"申请付款"},{key:"invoice",label:"申请开票"},{type:"divider"},{key:"inform",label:"新建费用通知"},{key:"arrival",label:"到账确认"},{key:"bill",label:"上传票据文件"},{key:"download-bill",label:"查看票据文件"},{key:"unlock-inform",label:"费用通知解锁"},{key:"link-inform",label:"关联费用信息"},{key:"delete-inform",label:"删除费用通知"},{type:"divider"},{key:"inform-date",label:"修改通知日期"},{key:"edit",label:"修改"},{key:"delete",label:"删除"},{key:"no-payment",label:"标记不缴费"},...(canMarkCaseFeeRefundNotRequired?.(selectedFee)?[{key:"refund-not-required",label:"标记不再办理退费"}]:[])],onClick:({key})=>key === "refund" ? (selectedFee ? openCourtRefund?.(selectedFee) : requireSingleFee?.(selectedFeeKeys,selectedFee,"办理法院退费")) : void handleExternalFeeOperation?.(selectedFeeKeys,selectedFee,key)}}><Button>其他操作</Button></Dropdown>}
        </Space>}
      </div>
    );
  }

  // internal
  return (
    <div className="case-legacy-tab-panel">
      <Table rowKey="id" size="small" pagination={{pageSize:10,showSizeChanger:true,showTotal:total=>`共有${total}条`}} scroll={{x:1120}} dataSource={feeRows} rowSelection={{selectedRowKeys:selectedFeeKeys,onChange:setSelectedFeeKeys}} columns={[
        {title:"收款人",width:130,render:(_:unknown,row:CaseRow)=>casePersonDisplayName?.(row.data.payee||row.data.handler||row.owner,row.data.payee_display_name||row.data.handler_display_name||row.owner_display_name)},
        {title:"提成类型",width:170,render:(_:unknown,row:CaseRow)=>row.data.commission_type||row.data.expense_subtype||row.data.fee_type||"内部费用"},
        {title:"金额",width:100,align:"right",render:(_:unknown,row:CaseRow)=>row.data.amount??0},
        {title:"已申请付款金额",width:150,align:"right",render:(_:unknown,row:CaseRow)=>row.data.payment_requested_amount??row.data.applied_amount??0},
        {title:"已付款金额",width:130,align:"right",render:(_:unknown,row:CaseRow)=>row.data.paid_amount??0},
        {title:"状态",dataIndex:"status",width:100},
        {title:"提交时间",width:120,render:(_:unknown,row:CaseRow)=>String(row.data.submitted_at||row.created_at||row.data.created_at||"").slice(0,10)||"—"},
        {title:"通知日期",width:120,render:(_:unknown,row:CaseRow)=>String(row.data.inform_date||row.data.notice_date||"").slice(0,10)||"—"},
        {title:"付款时间",width:120,render:(_:unknown,row:CaseRow)=>String(row.data.paid_at||row.data.payment_date||"").slice(0,10)||"—"},
        {title:"提交人",width:120,render:(_:unknown,row:CaseRow)=>row.data.submitter_display_name||row.data.submitted_by_display_name||row.data.handler_display_name||row.owner_display_name||casePersonDisplayName?.(row.owner)},
        {title:"备注",width:220,render:(_:unknown,row:CaseRow)=>row.description||row.data.remark||"—"},
        {title:"操作",width:130,fixed:"right" as const,render:(_:unknown,row:CaseRow)=><Space size={0}>{counselDetailCapabilities.can_create_finance&&<Button type="link" disabled={row.status!=="草稿"} onClick={()=>editCaseFee?.(row)}>编辑</Button>}{counselDetailCapabilities.can_create_finance&&<Button type="link" danger disabled={row.status!=="草稿"} onClick={()=>deleteCaseFee?.(row)}>删除</Button>}</Space>},
      ]}/>
      <Space className="case-legacy-bottom-actions">
        {counselDetailCapabilities.can_create_finance&&<Button onClick={()=>handleInternalFeeAction?.("create")}>新增内部费用</Button>}
        <Button onClick={()=>handleInternalFeeAction?.("payment")}>申请付款</Button>
        {counselDetailCapabilities.can_create_finance&&<Button disabled={selectedFee?.status!=="草稿"} onClick={()=>handleInternalFeeAction?.("edit")}>编辑</Button>}
        <Button onClick={()=>openInformDateBatchUpdate?.(selectedFeeKeys)}>修改通知日期</Button>
        {counselDetailCapabilities.can_create_finance&&<Button danger disabled={selectedFee?.status!=="草稿"} onClick={()=>handleInternalFeeAction?.("delete")}>删除</Button>}
      </Space>
    </div>
  );
};

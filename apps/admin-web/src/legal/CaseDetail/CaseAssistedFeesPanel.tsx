import { Button,Space,Table,Tag } from "antd";
import type { CaseAssistedFee,CaseDetailCapabilities } from "../types";

interface CaseAssistedFeesPanelProps {
  assistedFees: CaseAssistedFee[];
  assistedFeePage: number;
  assistedFeePageSize: number;
  assistedFeeTotal: number;
  capabilities: CaseDetailCapabilities;
  caseId?: number | null;
  onRefresh: (caseId: number, page: number, pageSize: number) => void;
  onPageChange: (caseId: number, page: number, pageSize: number) => void;
  casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
  onCreateClick: () => void;
  onEditClick: (row: CaseAssistedFee) => void;
  onConfirmClick: (row: CaseAssistedFee) => void;
  onDeleteClick: (row: CaseAssistedFee) => void;
}

export const CaseAssistedFeesPanel = ({
  assistedFees,
  assistedFeePage,
  assistedFeePageSize,
  assistedFeeTotal,
  capabilities,
  caseId,
  onRefresh,
  onPageChange,
  casePersonDisplayName,
  onCreateClick,
  onEditClick,
  onConfirmClick,
  onDeleteClick,
}: CaseAssistedFeesPanelProps) => {
  return (<div className="case-legacy-tab-panel">
    <Space className="case-legacy-bottom-actions">
      <Button onClick={() => caseId && void onRefresh(caseId, assistedFeePage, assistedFeePageSize)}>刷新</Button>
      {capabilities.can_manage_assisted_fees && <Button type="primary" onClick={onCreateClick}>新建资助费用</Button>}
    </Space>
    <Table
      rowKey="id"
      size="small"
      scroll={{x:1370}}
      dataSource={assistedFees}
      pagination={{
        current: assistedFeePage,
        pageSize: assistedFeePageSize,
        total: assistedFeeTotal,
        showSizeChanger: true,
        showTotal: (total) => `共有${total}条`,
        onChange: (page, pageSize) => caseId && void onPageChange(caseId, page, pageSize),
      }}
      locale={{emptyText:<span>没有查询到资助费用信息。</span>}}
      columns={[
        {title:"资助类别",dataIndex:"assisted_type",width:180},
        {title:"金额",dataIndex:"amount",width:110,align:"right",render:(value:number|null|undefined)=>value === null || value === undefined ? "—" : Number(value).toFixed(2)},
        {title:"提交日期",dataIndex:"request_date",width:120,render:(value:string)=>value||"—"},
        {title:"提交人",dataIndex:"request_user",width:120,render:(value:string)=>casePersonDisplayName(value)},
        {title:"办理日期",dataIndex:"confirmed_date",width:120,render:(value:string|undefined)=>value||"待办理"},
        {title:"办理人",dataIndex:"confirmed_user",width:120,render:(value:string|undefined)=>value?casePersonDisplayName(value):"—"},
        {title:"状态",dataIndex:"status",width:100,render:(value:string)=><Tag color={value === "已办理" ? "green" : "gold"}>{value}</Tag>},
        {title:"说明",dataIndex:"remark",width:220,ellipsis:true,render:(value:string)=>value||"—"},
        {title:"操作",key:"actions",fixed:"right",width:180,render:(_:unknown,row:CaseAssistedFee)=><Space size={0}>
          {row.status === "待办理" && capabilities.can_manage_assisted_fees && <Button type="link" onClick={()=>onEditClick(row)}>修改</Button>}
          {row.status === "待办理" && capabilities.can_manage_assisted_fees && <Button type="link" onClick={()=>onConfirmClick(row)}>办理确认</Button>}
          {row.status === "待办理" && capabilities.can_manage_assisted_fees && <Button type="link" danger onClick={()=>onDeleteClick(row)}>删除</Button>}
        </Space>},
      ]}
    />
  </div>);
};

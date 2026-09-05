import type { TablePaginationConfig } from "antd";
import { Button,message,Select,Space,Table,Tag } from "antd";
import { CASE_TASK_DEFAULT_PAGE,caseTaskTypeLabel } from "../constants";
import type { CaseDetailCapabilities,CaseRow,TaskRow } from "../types";

interface CaseCaseTasksPanelProps {
  tasks: TaskRow[];
  pagination: TablePaginationConfig;
  vipFilter: "all" | "vip" | "normal";
  setVipFilter: (value: "all" | "vip" | "normal") => void;
  capabilities: CaseDetailCapabilities;
  viewingCase: CaseRow | null | undefined;
  casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
  onVipFilterChange: (caseRow: CaseRow, page: number, pageSize: number, vipFilter: "all" | "vip" | "normal") => Promise<unknown>;
  taskPageSize: number;
  onOpenTask: (row: TaskRow) => void;
  onCreateTask: (caseRow: CaseRow) => void;
}

export const CaseCaseTasksPanel = ({
  tasks,
  pagination,
  vipFilter,
  setVipFilter,
  capabilities,
  viewingCase,
  casePersonDisplayName,
  onVipFilterChange,
  taskPageSize,
  onOpenTask,
  onCreateTask,
}: CaseCaseTasksPanelProps) => {
  return (<div className="case-legacy-tab-panel">
    <Space style={{ marginBottom: 12 }}>
      <span>VIP筛选</span>
      <Select
        value={vipFilter}
        style={{ width: 130 }}
        options={[{ value: "all", label: "全部任务" }, { value: "vip", label: "仅VIP任务" }, { value: "normal", label: "非VIP任务" }]}
        onChange={(value: "all" | "vip" | "normal") => {
          setVipFilter(value);
          if (viewingCase) void onVipFilterChange(viewingCase, CASE_TASK_DEFAULT_PAGE, taskPageSize, value).catch((error: any) => message.error(error?.response?.data?.detail || "VIP任务筛选失败"));
        }}
      />
    </Space>
    <Table rowKey="id" size="small" pagination={pagination} tableLayout="fixed" scroll={{x:1180}} dataSource={tasks} columns={[
      {title:"序号",width:65,render:(_:unknown,_row:TaskRow,index:number)=>index+1},
      {title:"任务编号",dataIndex:"serial_no",width:155,ellipsis:true,render:(value:string,row:TaskRow)=><Button type="link" className="case-cell-link" onClick={()=>onOpenTask(row)}>{value||"—"}</Button>},
      {title:"类型",width:90,ellipsis:true,render:(_:unknown,row:TaskRow)=>caseTaskTypeLabel(row)},
      {title:"标题",dataIndex:"title",width:280,ellipsis:true,render:(value:string,row:TaskRow)=><Button type="link" className="case-cell-link" onClick={()=>onOpenTask(row)}>{value||"—"}</Button>},
      {title:"提交时间",width:120,render:(_:unknown,row:TaskRow)=>String((row as any).created_at||(row as any).submitted_at||"").slice(0,10)||"—"},
      {title:"截止日期",dataIndex:"deadline",width:120,ellipsis:true},
      {title:"优先级",dataIndex:"priority",width:90,ellipsis:true},
      {title:"VIP",width:80,render:(_:unknown,row:TaskRow)=>row.is_vip?<Tag color="gold">VIP</Tag>:"—"},
      {title:"剩余时间",width:100,render:(_:unknown,row:TaskRow)=>row.days_remaining===null||row.days_remaining===undefined?"—":`${row.days_remaining} 天`},
      {title:"发起人",width:110,ellipsis:true,render:(_:unknown,row:TaskRow)=>casePersonDisplayName(row.initiator,row.initiator_display_name)},
      {title:"负责人",width:110,ellipsis:true,render:(_:unknown,row:TaskRow)=>casePersonDisplayName(row.owner,row.owner_display_name)},
      {title:"状态",dataIndex:"status",width:110,render:(value:string)=><Tag color={value==="已完成"||value==="已验收"?"green":value==="处理中"?"blue":"default"}>{value||"—"}</Tag>},
    ]}/>
    {capabilities.can_create_case_task&&<div className="case-legacy-bottom-actions"><Button onClick={()=>viewingCase && onCreateTask(viewingCase)}>发布任务</Button></div>}
  </div>);
};

interface CaseCustomerTasksPanelProps {
  tasks: TaskRow[];
  pagination: TablePaginationConfig;
  vipFilter: "all" | "vip" | "normal";
  setVipFilter: (value: "all" | "vip" | "normal") => void;
  viewingCase: CaseRow | null | undefined;
  casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
  onVipFilterChange: (caseRow: CaseRow, page: number, pageSize: number, vipFilter: "all" | "vip" | "normal") => Promise<unknown>;
  taskPageSize: number;
  onOpenTask: (row: TaskRow) => void;
}

export const CaseCustomerTasksPanel = ({
  tasks,
  pagination,
  vipFilter,
  setVipFilter,
  viewingCase,
  casePersonDisplayName,
  onVipFilterChange,
  taskPageSize,
  onOpenTask,
}: CaseCustomerTasksPanelProps) => {
  return (<div className="case-legacy-tab-panel">
    <Space style={{ marginBottom: 12 }}>
      <span>VIP筛选</span>
      <Select
        value={vipFilter}
        style={{ width: 130 }}
        options={[{ value: "all", label: "全部任务" }, { value: "vip", label: "仅VIP任务" }, { value: "normal", label: "非VIP任务" }]}
        onChange={(value: "all" | "vip" | "normal") => {
          setVipFilter(value);
          if (viewingCase) void onVipFilterChange(viewingCase, CASE_TASK_DEFAULT_PAGE, taskPageSize, value).catch((error: any) => message.error(error?.response?.data?.detail || "VIP任务筛选失败"));
        }}
      />
    </Space>
    <Table rowKey="id" size="small" pagination={pagination} tableLayout="fixed" scroll={{x:1130}} dataSource={tasks} columns={[{title:"任务编号",dataIndex:"serial_no",width:175,ellipsis:true,render:(value:string,row:TaskRow)=><Button type="link" className="case-cell-link" onClick={()=>onOpenTask(row)}>{value||"—"}</Button>},{title:"类型",width:100,ellipsis:true,render:(_:unknown,row:TaskRow)=>caseTaskTypeLabel(row)},{title:"任务名称",dataIndex:"title",width:230,ellipsis:true,render:(value:string,row:TaskRow)=><Button type="link" className="case-cell-link" onClick={()=>onOpenTask(row)}>{value||"—"}</Button>},{title:"截止日",dataIndex:"deadline",width:120,ellipsis:true},{title:"优先级",dataIndex:"priority",width:90,ellipsis:true},{title:"VIP",width:80,render:(_:unknown,row:TaskRow)=>row.is_vip?<Tag color="gold">VIP</Tag>:"—"},{title:"剩余时间",width:100,render:(_:unknown,row:TaskRow)=>row.days_remaining===null||row.days_remaining===undefined?"—":`${row.days_remaining} 天`},{title:"发起人",width:110,ellipsis:true,render:(_:unknown,row:TaskRow)=>casePersonDisplayName(row.initiator,row.initiator_display_name)},{title:"负责人",width:110,ellipsis:true,render:(_:unknown,row:TaskRow)=>casePersonDisplayName(row.owner,row.owner_display_name)},{title:"状态",dataIndex:"status",width:100,ellipsis:true}]}/>
  </div>);
};

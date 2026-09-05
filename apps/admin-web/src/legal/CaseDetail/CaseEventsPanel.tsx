import { PlusOutlined } from "@ant-design/icons";
import { Alert,Button,Space,Table,Tag } from "antd";
import dayjs from "dayjs";
import type { CaseEventCapabilities,CaseEventRow } from "../types";

interface CaseEventsPanelProps {
  casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
  events: CaseEventRow[];
  selectedKeys: import("react").Key[];
  setSelectedKeys: (keys: import("react").Key[]) => void;
  capabilities: CaseEventCapabilities;
  submitting: boolean;
  error: string;
  onRefresh: () => void;
  onCreate: () => void;
  onEdit: (row: CaseEventRow) => void;
  onDelete: (row: CaseEventRow) => void;
  onBatchDelete: () => void;
}

export const CaseEventsPanel = ({
  casePersonDisplayName,
  events,
  selectedKeys,
  setSelectedKeys,
  capabilities,
  submitting,
  error,
  onRefresh,
  onCreate,
  onEdit,
  onDelete,
  onBatchDelete,
}: CaseEventsPanelProps) => {
  return (<div className="case-legacy-tab-panel" data-testid="case-events-tab">
    <Space wrap style={{marginBottom:10}}>
      {capabilities.can_create && <Button type="primary" icon={<PlusOutlined/>} disabled={submitting} onClick={onCreate}>新增事件</Button>}
      {capabilities.can_delete && <Button danger loading={submitting} disabled={!selectedKeys.length} onClick={onBatchDelete}>批量删除</Button>}
    </Space>
    {error && <Alert type="error" showIcon style={{marginBottom:10}} message={error} action={<Button size="small" onClick={() => onRefresh()}>重试</Button>}/>}
    <Table rowKey="id" size="small" tableLayout="fixed" pagination={false} scroll={{x:1320}} dataSource={events} rowSelection={capabilities.can_delete ? {selectedRowKeys:selectedKeys,onChange:setSelectedKeys,getCheckboxProps:(row:CaseEventRow)=>({disabled:!row.can_delete})} : undefined} columns={[
      {title:"事件类型",dataIndex:"event_type",width:150,ellipsis:true},
      {title:"事件时间",dataIndex:"event_time",width:160,render:(value:string)=>value?dayjs(value).format("YYYY-MM-DD HH:mm"):"—"},
      {title:"截止日期",dataIndex:"deadline",width:130,render:(value:string)=>value?dayjs(value).format("YYYY-MM-DD"):"—"},
      {title:"事件内容",dataIndex:"content",width:300,ellipsis:true},
      {title:"提醒",width:180,render:(_:unknown,row:CaseEventRow)=>row.reminder_enabled ? `已启用${row.remind_at ? `：${dayjs(row.remind_at).format("YYYY-MM-DD HH:mm")}` : ""}` : "未启用"},
      {title:"状态",dataIndex:"status",width:100,render:(value:CaseEventRow["status"])=><Tag color={value==="已完成"?"green":value==="已逾期"?"red":"blue"}>{value}</Tag>},
      {title:"创建人",width:110,ellipsis:true,render:(_:unknown,row:CaseEventRow)=>casePersonDisplayName(row.creator, row.creator_display_name)},
      {title:"创建/修改时间",width:180,render:(_:unknown,row:CaseEventRow)=>row.updated_at||row.created_at||"—"},
      {title:"操作",key:"actions",width:140,fixed:"right" as const,render:(_:unknown,row:CaseEventRow)=><Space size={0}>{row.can_edit && <Button type="link" disabled={submitting} onClick={()=>onEdit(row)}>编辑</Button>}{row.can_delete && <Button type="link" danger loading={submitting} onClick={()=>onDelete(row)}>删除</Button>}</Space>},
    ]}/>
  </div>);
};

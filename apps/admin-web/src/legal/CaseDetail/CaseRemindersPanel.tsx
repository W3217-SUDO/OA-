import { Button,Table } from "antd";
import type { CaseDetailCapabilities,CaseReminderRow } from "../types";

interface CaseRemindersPanelProps {
  reminders: CaseReminderRow[];
  capabilities: CaseDetailCapabilities;
  casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
  onCreate: () => void;
  onDelete: (row: CaseReminderRow) => void;
}

export const CaseRemindersPanel = ({
  reminders,
  capabilities,
  casePersonDisplayName,
  onCreate,
  onDelete,
}: CaseRemindersPanelProps) => {
  return (<>{capabilities.can_create_reminder && <Button type="primary" style={{marginBottom:10}} onClick={onCreate}>新增提醒</Button>}<Table rowKey="id" size="small" pagination={false} dataSource={reminders} columns={[{title:"提醒日期",render:(_:unknown,row:CaseReminderRow)=>row.data.reminder_date,width:120},{title:"截止日期",render:(_:unknown,row:CaseReminderRow)=>row.data.deadline,width:120},{title:"提醒内容",dataIndex:"description"},{title:"创建人",width:110,render:(_:unknown,row:CaseReminderRow)=>casePersonDisplayName(row.owner)},{title:"操作",width:80,render:(_:unknown,row:CaseReminderRow)=>capabilities.can_delete_reminder?<Button type="link" danger onClick={()=>onDelete(row)}>删除</Button>:null}]}/></>);
};

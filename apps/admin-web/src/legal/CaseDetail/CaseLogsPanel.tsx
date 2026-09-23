import { Button,Space,Table } from "antd";
import type { CaseDetailCapabilities,CaseLogKind,CaseLogRow } from "../types";

interface CaseCaseLogsPanelProps {
  logs: CaseLogRow[];
  capabilities: CaseDetailCapabilities;
  casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
  onCreateLog: (kind: CaseLogKind) => void;
  onViewLog: (log: CaseLogRow) => void;
}

export const CaseCaseLogsPanel = ({
  logs,
  capabilities,
  casePersonDisplayName,
  onCreateLog,
  onViewLog,
}: CaseCaseLogsPanelProps) => {
  return (<>{capabilities.can_create_log && <Space style={{marginBottom:10}}><Button type="primary" onClick={()=>onCreateLog("case")}>新增日志</Button><Button onClick={()=>onCreateLog("refund")}>新增退费日志</Button></Space>}<Table rowKey="id" size="small" pagination={false} dataSource={logs} columns={[{title:"时间",dataIndex:"created_at",width:170},{title:"日志内容",dataIndex:"content",render:(content:string)=><span style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{content}</span>},{title:"记录人",width:110,render:(_:unknown,row:CaseLogRow)=>casePersonDisplayName(row.operator,row.operator_display_name)},{title:"操作",width:70,render:(_:unknown,row:CaseLogRow)=><Button type="link" size="small" onClick={()=>onViewLog(row)}>查看</Button>}]}/></>);
};

interface CaseSystemLogsPanelProps {
  logs: Array<{ id: number; created_at: string; action: string; operator: string; operator_display_name?: string; comment: string }>;
  capabilities: CaseDetailCapabilities;
  casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
  onCreateLog: (kind: CaseLogKind) => void;
}

export const CaseSystemLogsPanel = ({
  logs,
  casePersonDisplayName,
}: CaseSystemLogsPanelProps) => {
  return (<Table rowKey="id" size="small" pagination={false} dataSource={logs} columns={[{title:"时间",dataIndex:"created_at",width:170},{title:"操作",dataIndex:"action",width:210},{title:"操作人",width:110,render:(_:unknown,row:any)=>casePersonDisplayName(row.operator,row.operator_display_name)},{title:"说明",dataIndex:"comment"}]}/>);
};

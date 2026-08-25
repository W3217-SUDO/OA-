import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Descriptions, Empty, Input, Spin, Table, Tabs, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useState } from "react";

import { api } from "./api";

export type LegacyContractParent = {
  history_parent_key: string;
  legacy_contract_ids: string[];
  legacy_contract_guids: string[];
  legacy_contract_nos: string[];
  legacy_customer_nos: string[];
  relationship_state: string;
  source_parent_target_states: Record<string, number>;
  source_relation_counts: Record<string, number>;
};

type Approval = { legacy_audit_id: number; legacy_contract_no: string; relationship_state: string; audit_status: number | null; auditor: string; audit_date?: string | null; audit_content: string };
type Attachment = { legacy_file_id: number; file_name: string; file_size?: number | null; upload_user: string; upload_time?: string | null; metadata_state: string; download_available: false; download_reason: string };
type Log = { legacy_event_id: number; content: string; operator: string; operate_time?: string | null };
type LegacyCaseRelation = { legacy_case_source: string; legacy_case_id: number; legacy_case_no: string; legacy_contract_no: string; legacy_customer_no: string; case_record_id?: number | null; relationship_state: string; case_name: string; case_phase_id?: number | null; business_owner: string };
type Detail = { parent: LegacyContractParent; approvals: Approval[]; attachments: Attachment[]; logs: Log[]; cases: LegacyCaseRelation[] };
type ListResponse = { items: LegacyContractParent[]; total: number };

export const legacyContractHistoryEndpoints = {
  list: "/legacy-contract-history/parents",
  detail: (key: string) => `/legacy-contract-history/parents/${encodeURIComponent(key)}`,
  contract: (contractNo: string) => `/legacy-contract-history/contracts/${encodeURIComponent(contractNo)}`,
  customer: (customerNo: string) => `/legacy-contract-history/customers/${encodeURIComponent(customerNo)}/contracts`,
  caseContract: (source: string, caseId: number) => `/legacy-contract-history/cases/${encodeURIComponent(source)}/${caseId}/contract`,
};

const time = (value?: string | null) => value ? value.replace("T", " ").slice(0, 19) : "-";

const columns: ColumnsType<LegacyContractParent> = [
  { title: "历史合同编号", dataIndex: "legacy_contract_nos", render: (value: string[]) => value.join(", ") || "-", ellipsis: true },
  { title: "历史合同主键", dataIndex: "legacy_contract_ids", width: 160, render: (value: string[]) => value.join(", ") || "-", ellipsis: true },
  { title: "关系状态", dataIndex: "relationship_state", width: 220, render: (value) => <Tag>{value}</Tag> },
  { title: "审批/附件/日志", dataIndex: "source_relation_counts", width: 160, render: (value: Record<string, number>) => `${value.audit || 0} / ${value.attachment || 0} / ${value.event || 0}` },
];

export function LegacyContractHistoryPanel({
  initialHistoryParentKey,
  contractNo,
  customerNo,
}: {
  initialHistoryParentKey?: string;
  contractNo?: string;
  customerNo?: string;
}) {
  const [keyword, setKeyword] = useState("");
  const [rows, setRows] = useState<LegacyContractParent[]>([]);
  const [selected, setSelected] = useState<string | undefined>(initialHistoryParentKey);
  const [detail, setDetail] = useState<Detail>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadList = useCallback(async (nextKeyword = keyword) => {
    setLoading(true); setError("");
    try {
      const endpoint = contractNo ? legacyContractHistoryEndpoints.contract(contractNo) : customerNo ? legacyContractHistoryEndpoints.customer(customerNo) : legacyContractHistoryEndpoints.list;
      const response = await api.get<ListResponse>(endpoint, contractNo || customerNo ? undefined : { params: { keyword: nextKeyword, page: 1, page_size: 100 } });
      setRows(response.data.items);
      setSelected((current) => current && response.data.items.some((item) => item.history_parent_key === current) ? current : response.data.items[0]?.history_parent_key);
    } catch (requestError: any) {
      setRows([]); setDetail(undefined); setError(requestError?.response?.data?.detail || "无法读取历史合同数据");
    } finally { setLoading(false); }
  }, [contractNo, customerNo, keyword]);

  const loadDetail = useCallback(async (key: string) => {
    setLoading(true); setError("");
    try { setDetail((await api.get<Detail>(legacyContractHistoryEndpoints.detail(key))).data); }
    catch (requestError: any) { setDetail(undefined); setError(requestError?.response?.data?.detail || "无法读取历史合同详情"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void loadList(); }, [loadList]);
  useEffect(() => { if (selected) void loadDetail(selected); }, [loadDetail, selected]);

  return <section aria-label="历史合同" style={{ display: "grid", gap: 12 }}>
    {error && <Alert type="error" showIcon message={error} />}
    <div style={{ display: "flex", gap: 8 }}>
      <Input.Search value={keyword} onChange={(event) => setKeyword(event.target.value)} onSearch={(value) => { setKeyword(value); void loadList(value); }} placeholder="合同编号或旧主键" allowClear />
      <Button aria-label="刷新历史合同" icon={<ReloadOutlined />} onClick={() => void loadList()} />
    </div>
    <Table rowKey="history_parent_key" columns={columns} dataSource={rows} loading={loading} pagination={false} size="small" scroll={{ x: 760 }} onRow={(record) => ({ onClick: () => setSelected(record.history_parent_key) })} rowSelection={{ type: "radio", selectedRowKeys: selected ? [selected] : [], onChange: (keys) => setSelected(String(keys[0] || "")) }} />
    <Spin spinning={loading}>{detail ? <>
      <Descriptions title={detail.parent.legacy_contract_nos.join(", ") || detail.parent.history_parent_key} bordered size="small" column={{ xs: 1, md: 3 }}>
        <Descriptions.Item label="历史父引用" span={3}>{detail.parent.history_parent_key}</Descriptions.Item>
        <Descriptions.Item label="旧主键">{detail.parent.legacy_contract_ids.join(", ") || "-"}</Descriptions.Item>
        <Descriptions.Item label="关系状态">{detail.parent.relationship_state}</Descriptions.Item>
        <Descriptions.Item label="旧 GUID">{detail.parent.legacy_contract_guids.join(", ") || "-"}</Descriptions.Item>
      </Descriptions>
      <Tabs items={[
        { key: "approvals", label: `审批 (${detail.approvals.length})`, children: <Table rowKey="legacy_audit_id" size="small" pagination={false} dataSource={detail.approvals} columns={[{ title: "旧审批主键", dataIndex: "legacy_audit_id" }, { title: "审批人", dataIndex: "auditor" }, { title: "状态", dataIndex: "audit_status" }, { title: "时间", dataIndex: "audit_date", render: time }, { title: "意见", dataIndex: "audit_content", ellipsis: true }]} /> },
        { key: "attachments", label: `附件元数据 (${detail.attachments.length})`, children: <Table rowKey="legacy_file_id" size="small" pagination={false} dataSource={detail.attachments} columns={[{ title: "文件", dataIndex: "file_name", ellipsis: true }, { title: "大小", dataIndex: "file_size", render: (value) => value ?? "-" }, { title: "上传人", dataIndex: "upload_user" }, { title: "上传时间", dataIndex: "upload_time", render: time }, { title: "下载", render: () => <Tag color="default">不可下载</Tag> }, { title: "原因", dataIndex: "download_reason", ellipsis: true }]} /> },
        { key: "logs", label: `日志 (${detail.logs.length})`, children: <Table rowKey="legacy_event_id" size="small" pagination={false} dataSource={detail.logs} columns={[{ title: "旧日志主键", dataIndex: "legacy_event_id" }, { title: "时间", dataIndex: "operate_time", render: time }, { title: "操作人", dataIndex: "operator" }, { title: "内容", dataIndex: "content", ellipsis: true }]} /> },
        { key: "cases", label: `关联案件 (${detail.cases.length})`, children: <Table rowKey={(row) => `${row.legacy_case_source}:${row.legacy_case_id}`} size="small" pagination={false} dataSource={detail.cases} columns={[{ title: "案件编号", dataIndex: "legacy_case_no", ellipsis: true }, { title: "案件名称", dataIndex: "case_name", ellipsis: true }, { title: "来源", dataIndex: "legacy_case_source" }, { title: "阶段", dataIndex: "case_phase_id", render: (value) => value ?? "-" }, { title: "负责人", dataIndex: "business_owner" }, { title: "案件记录", dataIndex: "case_record_id", render: (value) => value ?? "未迁入" }]} /> },
      ]} />
    </> : !loading && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}</Spin>
  </section>;
}

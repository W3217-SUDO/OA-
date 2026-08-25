import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Collapse, Descriptions, Empty, Input, List, Spin, Table, Timeline, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "./api";

export type LegacyLsCase = {
  legacy_case_id: number; case_no: string; case_phase_id?: number | null; case_officer: string;
  contract_no: string; case_submit_date?: string | null; deadline?: string | null; reminder_date?: string | null;
  case_submitter: string; case_origin_people: string; phase_history_row_count: number;
};
export type LegacyLsPhase = { legacy_phase_id: number; current_phase_id?: number | null; content: string; create_user: string; create_time?: string | null; change_time?: string | null };
export type LegacyLsRelation = { relation_key: string; source_table: string; source_primary_key: string; entity_type: string; legacy_case_id: number; relationship_status: string; source: Record<string, unknown> };
type ListResponse = { items: LegacyLsCase[]; total: number };
type DetailResponse = { case: LegacyLsCase; relations: Record<string, LegacyLsRelation[]> };
type TimelineResponse = { items: LegacyLsPhase[] };

export const legacyLsHistoryEndpoints = {
  list: "/legacy-ls-history/cases",
  detail: (id: number) => `/legacy-ls-history/cases/${id}`,
  timeline: (id: number) => `/legacy-ls-history/cases/${id}/timeline`,
  byCurrentRecord: (id: number) => `/legacy-ls-history/current-records/${id}`,
};

const labels: Record<string, string> = {
  party: "\u5f53\u4e8b\u4eba\u4fe1\u606f", plaintiff_customer: "\u539f\u544a\u5ba2\u6237", defendant_customer: "\u88ab\u544a\u5ba2\u6237",
  first_instance: "\u4e00\u5ba1\u4fe1\u606f", second_instance: "\u4e8c\u5ba1\u4fe1\u606f", last_instance: "\u518d\u5ba1\u4fe1\u606f", execution: "\u6267\u884c\u4fe1\u606f",
  investigation: "\u8c03\u67e5\u4fe1\u606f", reminder: "\u6848\u4ef6\u63d0\u9192", log: "\u6848\u4ef6\u65e5\u5fd7", attachment: "\u9644\u4ef6", task: "\u4efb\u52a1",
};
const formatTime = (value?: string | null) => value ? value.replace("T", " ").slice(0, 19) : "-";
const summary = (relation: LegacyLsRelation) => {
  const source = relation.source;
  return String(source.FileName || source.EventContent || source.Content || source.TaskTitle || source.CaseProsecutor || source.CaseIndicter || source.CaseNo || relation.source_primary_key);
};

export function LegacyLsHistoryPanel({ initialCaseId, currentCaseRecordId }: { initialCaseId?: number; currentCaseRecordId?: number }) {
  const [keyword, setKeyword] = useState(""); const [rows, setRows] = useState<LegacyLsCase[]>([]); const [selected, setSelected] = useState<number | undefined>(initialCaseId);
  const [detail, setDetail] = useState<DetailResponse>(); const [timeline, setTimeline] = useState<LegacyLsPhase[]>([]); const [loading, setLoading] = useState(false); const [error, setError] = useState(""); const [unmapped, setUnmapped] = useState(false);
  const loadList = useCallback(async (next = keyword) => { setLoading(true); setError(""); try { const response = await api.get<ListResponse>(legacyLsHistoryEndpoints.list, { params: { keyword: next, page: 1, page_size: 100 } }); setRows(response.data.items); setSelected((current) => current && response.data.items.some((row) => row.legacy_case_id === current) ? current : response.data.items[0]?.legacy_case_id); } catch (err: any) { setError(err?.response?.data?.detail || "\u65e0\u6cd5\u8bfb\u53d6\u8bc9\u8bbc\u5386\u53f2\u6848\u4ef6"); } finally { setLoading(false); } }, [keyword]);
  const loadDetail = useCallback(async (id: number) => { setLoading(true); setError(""); try { const [caseResponse, phaseResponse] = await Promise.all([api.get<DetailResponse>(legacyLsHistoryEndpoints.detail(id)), api.get<TimelineResponse>(legacyLsHistoryEndpoints.timeline(id))]); setDetail(caseResponse.data); setTimeline(phaseResponse.data.items); } catch (err: any) { setError(err?.response?.data?.detail || "\u65e0\u6cd5\u8bfb\u53d6\u5386\u53f2\u5173\u8054"); } finally { setLoading(false); } }, []);
  useEffect(() => { if (!currentCaseRecordId) void loadList(); }, [currentCaseRecordId, loadList]); useEffect(() => { if (selected) void loadDetail(selected); }, [selected, loadDetail]);
  useEffect(() => {
    if (!currentCaseRecordId) return;
    setLoading(true);
    setError("");
    setUnmapped(false);
    setDetail(undefined);
    setTimeline([]);
    void api.get<{ legacy_case_id: number }>(legacyLsHistoryEndpoints.byCurrentRecord(currentCaseRecordId))
      .then((response) => { setSelected(response.data.legacy_case_id); setUnmapped(false); })
      .catch((err: any) => {
        if (err?.response?.status === 404) setUnmapped(true);
        else setError(err?.response?.data?.detail || "\u65e0\u6cd5\u8bfb\u53d6\u5f53\u524d\u6848\u4ef6\u7684\u8bc9\u8bbc\u5386\u53f2");
      })
      .finally(() => setLoading(false));
  }, [currentCaseRecordId]);
  const columns: ColumnsType<LegacyLsCase> = useMemo(() => [{ title: "\u6848\u53f7", dataIndex: "case_no", width: 180 }, { title: "\u5f53\u524d\u9636\u6bb5", dataIndex: "case_phase_id", width: 90 }, { title: "\u7ecf\u529e\u4eba\u5458", dataIndex: "case_officer", width: 120 }, { title: "\u63d0\u4ea4\u65f6\u95f4", dataIndex: "case_submit_date", render: formatTime }, { title: "\u9636\u6bb5\u5386\u53f2", dataIndex: "phase_history_row_count", width: 100 }], []);
  const relationPanels = detail ? Object.entries(detail.relations).map(([type, items]) => ({ key: type, label: `${labels[type] || type} (${items.length})`, children: <List size="small" dataSource={items} renderItem={(item) => <List.Item><Typography.Text>{summary(item)}</Typography.Text><Typography.Text type="secondary">{item.source_table}#{item.source_primary_key}</Typography.Text></List.Item>} /> })) : [];
  return <section aria-label="legacy-ls-history" style={{ display: "grid", gap: 12 }}>{error && <Alert type="error" showIcon message={error} />}{unmapped && <Alert type="info" showIcon message="当前案件没有可核实的旧诉讼案件关联" />}{!currentCaseRecordId && <><div style={{ display: "flex", gap: 8 }}><Input.Search value={keyword} onChange={(event) => setKeyword(event.target.value)} onSearch={(value) => { setKeyword(value); void loadList(value); }} placeholder="\u6848\u53f7\u3001\u4eba\u5458\u6216\u5408\u540c\u53f7" allowClear /><Button aria-label="refresh" icon={<ReloadOutlined />} onClick={() => void loadList()} /></div><Table rowKey="legacy_case_id" columns={columns} dataSource={rows} loading={loading} pagination={false} size="small" scroll={{ x: 720 }} onRow={(row) => ({ onClick: () => setSelected(row.legacy_case_id) })} rowSelection={{ type: "radio", selectedRowKeys: selected ? [selected] : [], onChange: (keys) => setSelected(Number(keys[0]) || undefined) }} /></>}{detail ? <Spin spinning={loading}><Descriptions title={detail.case.case_no || `LS-${detail.case.legacy_case_id}`} column={{ xs: 1, md: 2, lg: 4 }} size="small" bordered><Descriptions.Item label="\u6848\u53f7">{detail.case.case_no || "-"}</Descriptions.Item><Descriptions.Item label="\u5408\u540c\u53f7">{detail.case.contract_no || "\u6e90\u5e93\u65e0\u5408\u540c\u5173\u8054"}</Descriptions.Item><Descriptions.Item label="\u5f53\u524d\u9636\u6bb5">{detail.case.case_phase_id ?? "-"}</Descriptions.Item><Descriptions.Item label="\u622a\u6b62\u65e5\u671f">{formatTime(detail.case.deadline)}</Descriptions.Item></Descriptions><Typography.Title level={5}>\u9636\u6bb5\u5386\u53f2</Typography.Title>{timeline.length ? <Timeline items={timeline.map((phase) => ({ children: <span>{`\u9636\u6bb5 ${phase.current_phase_id ?? "-"}: ${phase.content || "-"} (${formatTime(phase.create_time || phase.change_time)})`}</span> }))} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}<Collapse items={relationPanels} /></Spin> : !loading && !unmapped && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}</section>;
}

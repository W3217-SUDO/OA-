import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Button, Modal, Select, Space, Table, Tag } from "antd";
import { BarChartOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "../personal-agent/types";
import "./dsh-plugin-center.css";

// 陶威 11-03：智能体中心要看到每个人调用云端智能体的情况和收费。费用是按公开单价的估算，以火山账单为准。
type Person = {
  username: string; display_name: string; turns: number; failed: number; personal_turns: number; case_turns: number;
  input_tokens: number; cache_tokens: number; output_tokens: number; active_seconds: number; oa_tools: number; datapro: number;
  searches: number; harness_afp: number; model_yuan: number; runtime_yuan: number; harness_yuan: number; total_yuan: number; last_time: string;
};
type UsageState = { month: string; people: Person[]; total: Record<string, number>; days: { date: string; turns: number; yuan: number }[]; note: string };
type UsageRecord = {
  time: string; workspace: string; model: string; ok: boolean; requests: number; input_tokens: number; cache_tokens: number;
  output_tokens: number; active_seconds: number; oa_tools: number; datapro: Record<string, number>; searches: number;
  model_yuan: number | null; runtime_yuan: number; harness_yuan: number;
};

const BASE = "/agent-admin/cloud-runtime/usage";
const yuan = (value: number | null | undefined) => (value == null ? "—" : `¥${value < 0.01 && value > 0 ? value.toFixed(4) : value.toFixed(2)}`);
const tokens = (value: number) => (value >= 10000 ? `${(value / 10000).toFixed(1)} 万` : String(value));
const DATASET: Record<string, string> = { legal_case: "司法案例", legal_hallucination: "幻觉校验", other: "其他" };

function months() {
  const result: string[] = [];
  const now = new Date();
  for (let index = 0; index < 6; index += 1) {
    const date = new Date(now.getFullYear(), now.getMonth() - index, 1);
    result.push(`${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`);
  }
  return result;
}

export function CloudUsage({ active }: { active: boolean }) {
  const monthOptions = useMemo(months, []);
  const [month, setMonth] = useState(monthOptions[0]);
  const [state, setState] = useState<UsageState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [person, setPerson] = useState<Person | null>(null);
  const [records, setRecords] = useState<UsageRecord[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setState((await api.get<UsageState>(BASE, { params: { month } })).data); }
    catch (failure) { setError(errorText(failure, "调用统计加载失败")); }
    finally { setLoading(false); }
  }, [month]);
  useEffect(() => { if (active) void load(); }, [active, load]);

  const open = async (item: Person) => {
    setPerson(item); setRecords([]); setRecordsLoading(true);
    try { setRecords((await api.get<{ records: UsageRecord[] }>(`${BASE}/records`, { params: { month, username: item.username } })).data.records); }
    catch (failure) { setError(errorText(failure, "调用明细加载失败")); setPerson(null); }
    finally { setRecordsLoading(false); }
  };

  const total = state?.total;
  return <section className="dsh-plugin-center" aria-label="调用与费用">
    <header className="dsh-plugin-heading">
      <div><span className="dsh-plugin-eyebrow">CLOUD AGENT USAGE</span><h2><BarChartOutlined />调用与费用</h2>
        <p>云端智能体每个人的调用次数、用量和估算费用。点某个人可以看每一轮的明细。</p></div>
      <Space wrap>
        <Select value={month} onChange={setMonth} options={monthOptions.map(value => ({ value, label: value }))} style={{ width: 120 }} aria-label="月份" />
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>刷新</Button>
      </Space>
    </header>
    {error && <Alert type="error" showIcon title={error} />}
    {total && <div className="dsh-provider-list"><article>
      <div className="dsh-plugin-info">
        <div className="dsh-plugin-title"><strong>{state?.month} 合计</strong><Tag color="blue">估算 {yuan(total.total_yuan)}</Tag></div>
        <p>对话 {total.turns} 轮　OA 工具 {total.oa_tools} 次　专业数据集 {total.datapro} 次　豆包搜索 {total.searches} 次</p>
        <small>模型 {yuan(total.model_yuan)}　运行时 {yuan(total.runtime_yuan)}　数据集与搜索 {yuan(total.harness_yuan)}（{total.harness_afp} AFP，从 Agent Plan 套餐抵扣）　输入 {tokens(total.input_tokens)}，命中缓存 {tokens(total.cache_tokens)}，输出 {tokens(total.output_tokens)} token</small>
        {state?.note && <p>{state.note}</p>}
      </div>
    </article></div>}
    <Table<Person> rowKey="username" size="small" loading={loading} dataSource={state?.people || []} pagination={false} scroll={{ x: 900 }}
      locale={{ emptyText: "本月还没有云端智能体调用记录" }}
      onRow={item => ({ onClick: () => void open(item), style: { cursor: "pointer" } })}
      columns={[
        { title: "人员", dataIndex: "display_name", fixed: "left", render: (value, item) => <span>{value}{item.failed ? <Tag color="error" style={{ marginLeft: 6 }}>失败 {item.failed}</Tag> : null}</span> },
        { title: "对话轮数", dataIndex: "turns", render: (value, item) => `${value}（个人 ${item.personal_turns} / 案件 ${item.case_turns}）` },
        { title: "OA 工具", dataIndex: "oa_tools" },
        { title: "数据集", dataIndex: "datapro" },
        { title: "搜索", dataIndex: "searches" },
        { title: "输入 / 缓存 / 输出", render: (_, item) => `${tokens(item.input_tokens)} / ${tokens(item.cache_tokens)} / ${tokens(item.output_tokens)}` },
        { title: "模型", dataIndex: "model_yuan", render: yuan },
        { title: "运行时", dataIndex: "runtime_yuan", render: yuan },
        { title: "数据集与搜索", dataIndex: "harness_yuan", render: yuan },
        { title: "合计", dataIndex: "total_yuan", render: value => <strong>{yuan(value)}</strong>, defaultSortOrder: "descend", sorter: (a, b) => a.total_yuan - b.total_yuan },
        { title: "最近使用", dataIndex: "last_time", render: value => String(value || "").slice(5, 16).replace("T", " ") },
      ]} />
    <Modal title={person ? `${person.display_name} · ${month} 调用明细` : ""} open={!!person} footer={null} width={960} onCancel={() => setPerson(null)} destroyOnHidden>
      <Table<UsageRecord> rowKey="time" size="small" loading={recordsLoading} dataSource={records} pagination={{ pageSize: 20 }} scroll={{ x: 820 }}
        columns={[
          { title: "时间", dataIndex: "time", render: value => String(value).slice(5, 19).replace("T", " ") },
          { title: "位置", dataIndex: "workspace", render: value => (String(value).startsWith("case:") ? `案件 ${String(value).slice(5)}` : "个人空间") },
          { title: "结果", dataIndex: "ok", render: value => (value ? <Tag color="success">完成</Tag> : <Tag color="error">失败</Tag>) },
          { title: "工具", render: (_, item) => [item.oa_tools ? `OA ${item.oa_tools}` : "",
            ...Object.entries(item.datapro || {}).map(([kind, count]) => `${DATASET[kind] || kind} ${count}`),
            item.searches ? `搜索 ${item.searches}` : ""].filter(Boolean).join("，") || "—" },
          { title: "输入 / 缓存 / 输出", render: (_, item) => `${tokens(item.input_tokens)} / ${tokens(item.cache_tokens)} / ${tokens(item.output_tokens)}` },
          { title: "用时", dataIndex: "active_seconds", render: value => `${Number(value).toFixed(1)} 秒` },
          { title: "费用", render: (_, item) => yuan((item.model_yuan || 0) + item.runtime_yuan + item.harness_yuan) },
        ]} />
    </Modal>
  </section>;
}

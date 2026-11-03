import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Descriptions, Modal, Select, Space, Tag } from "antd";
import { api } from "../api";
import Table from "../components/ResizableTable";
import { POPUP_WIDTH } from "../components/common/popupSize";
import { errorText } from "./types";

// 陶国南 11-03：每个人都能看到自己的智能体用量和花费。后端只返回登录人自己的数据；金额与管理员页同一套估算。
type Summary = {
  turns: number; failed: number; personal_turns: number; case_turns: number; oa_tools: number; datapro: number; searches: number;
  input_tokens: number; cache_tokens: number; output_tokens: number; model_yuan: number; runtime_yuan: number; harness_yuan: number; total_yuan: number;
};
type UsageRecord = {
  time: string; workspace: string; ok: boolean; oa_tools: number; datapro: Record<string, number>; searches: number;
  input_tokens: number; cache_tokens: number; output_tokens: number; active_seconds: number;
  model_yuan: number | null; runtime_yuan: number; harness_yuan: number;
};
type MyUsage = { month: string; summary: Summary | null; records: UsageRecord[]; total_records: number; note: string };

const yuan = (value: number | null | undefined) => (value == null ? "—" : `¥${value > 0 && value < 0.01 ? value.toFixed(4) : value.toFixed(2)}`);
const tokens = (value: number) => (value >= 10000 ? `${(value / 10000).toFixed(1)} 万` : String(value));
const DATASET: Record<string, string> = { legal_case: "司法案例", legal_hallucination: "幻觉校验", other: "其他" };

function recentMonths() {
  const now = new Date();
  return Array.from({ length: 6 }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth() - index, 1);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  });
}

export function MyAgentUsage({ open, onClose }: { open: boolean; onClose: () => void }) {
  const months = useMemo(recentMonths, []);
  const [month, setMonth] = useState(months[0]);
  const [data, setData] = useState<MyUsage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setData((await api.get<MyUsage>("/personal-agent/cloud-usage", { params: { month } })).data); }
    catch (failure) { setError(errorText(failure, "用量加载失败")); }
    finally { setLoading(false); }
  }, [month]);
  useEffect(() => { if (open) void load(); }, [open, load]);

  const summary = data?.summary;
  return <Modal title="我的智能体用量" open={open} onCancel={onClose} footer={null} width={POPUP_WIDTH.lg} destroyOnHidden>
    <Space direction="vertical" style={{ width: "100%" }}>
      <Space wrap>
        <Select value={month} onChange={setMonth} options={months.map(value => ({ value, label: value }))} style={{ width: 120 }} aria-label="月份" />
        <Tag color="blue">估算</Tag>
      </Space>
      {error && <Alert type="error" showIcon title={error} />}
      {!loading && !error && data && !summary && <Alert type="info" showIcon title={`${month} 还没有云端智能体调用记录。`} />}
      {summary && <Descriptions size="small" bordered column={{ xs: 1, sm: 2, md: 3 }} items={[
        { key: "turns", label: "对话轮数", children: `${summary.turns}（个人 ${summary.personal_turns} / 案件 ${summary.case_turns}）` },
        { key: "tools", label: "OA 工具调用", children: `${summary.oa_tools} 次` },
        { key: "data", label: "专业数据集 / 搜索", children: `${summary.datapro} 次 / ${summary.searches} 次` },
        { key: "tokens", label: "输入 / 缓存 / 输出", children: `${tokens(summary.input_tokens)} / ${tokens(summary.cache_tokens)} / ${tokens(summary.output_tokens)} token` },
        { key: "parts", label: "模型 / 运行时 / 数据集与搜索", children: `${yuan(summary.model_yuan)} / ${yuan(summary.runtime_yuan)} / ${yuan(summary.harness_yuan)}` },
        { key: "total", label: "估算花费", children: <strong>{yuan(summary.total_yuan)}</strong> },
      ]} />}
      {!!data?.records.length && <Table<UsageRecord> rowKey="time" size="small" loading={loading} dataSource={data.records}
        pagination={{ pageSize: 10 }} scroll={{ x: 720 }}
        columns={[
          { title: "时间", dataIndex: "time", render: value => String(value).slice(5, 16).replace("T", " ") },
          { title: "位置", dataIndex: "workspace", render: value => (String(value).startsWith("case:") ? "案件" : "个人空间") },
          { title: "结果", dataIndex: "ok", render: value => (value ? <Tag color="success">完成</Tag> : <Tag color="error">失败</Tag>) },
          { title: "工具", render: (_, item) => [item.oa_tools ? `OA ${item.oa_tools}` : "",
            ...Object.entries(item.datapro || {}).map(([kind, count]) => `${DATASET[kind] || kind} ${count}`),
            item.searches ? `搜索 ${item.searches}` : ""].filter(Boolean).join("，") || "—" },
          { title: "用时", dataIndex: "active_seconds", render: value => `${Number(value).toFixed(1)} 秒` },
          { title: "估算花费", render: (_, item) => yuan((item.model_yuan || 0) + item.runtime_yuan + item.harness_yuan) },
        ]} />}
      {data?.note && <small>{data.note}</small>}
    </Space>
  </Modal>;
}

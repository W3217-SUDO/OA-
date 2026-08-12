import { useEffect, useState } from "react";
import { Button, Card, Input, Select, Space, Table, Tag } from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { rememberTaskDetailTarget } from "./taskDetailNavigation";
import { rememberInvestigationDetailTarget } from "./investigationDetailNavigation";
import { rememberBusinessRecordDetailTarget } from "./businessRecordDetailNavigation";

type Log = {
  id: number;
  record_id: number;
  module: string;
  serial_no: string;
  title: string;
  action: string;
  from_status: string;
  to_status: string;
  operator: string;
  operator_display_name?: string;
  comment: string;
  created_at: string;
};

const personDisplayName = (value?: unknown) => String(value || "").trim() || "姓名待维护";

const labels: Record<string, string> = {
  customer: "客户",
  contract: "合同",
  case: "案件",
  task: "任务",
  clue: "线索",
  notary: "公证",
  evidence: "证据",
  seal: "用印",
  finance: "财务",
  document: "收发文",
  hr: "人事",
  warehouse: "仓库",
  report: "报表",
};

export default function AuditLogPage({ onNavigate }: { onNavigate?: (route: string) => void }) {
  const [rows, setRows] = useState<Log[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [module, setModule] = useState("");

  const load = async (p = page) => {
    setLoading(true);
    try {
      const { data } = await api.get("/audit/events", { params: { module, keyword, page: p, page_size: 50 } });
      setRows(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(1); }, []);

  const openBusiness = (row: Log) => {
    if (!row.record_id || !row.serial_no) return;
    if (row.module === "case") {
      rememberCaseDetailTarget({ id: row.record_id, serial_no: row.serial_no });
      onNavigate?.("case-company");
    } else if (row.module === "contract") {
      rememberContractDetailTarget({ id: row.record_id, serial_no: row.serial_no });
      onNavigate?.("contract-company");
    } else if (row.module === "customer") {
      rememberCustomerDetailTarget({ id: row.record_id, serial_no: row.serial_no, title: row.title });
      onNavigate?.("customer-company");
    } else if (row.module === "task") {
      rememberTaskDetailTarget({ id: row.record_id, serial_no: row.serial_no });
      onNavigate?.("task-company-accepted");
    } else if (["clue", "notary", "evidence"].includes(row.module)) {
      rememberInvestigationDetailTarget({ id: row.record_id, serial_no: row.serial_no, module: row.module });
      onNavigate?.(row.module);
    } else if (["finance", "seal", "document", "warehouse", "hr"].includes(row.module)) {
      if (rememberBusinessRecordDetailTarget({ id: row.record_id, module: row.module as "finance" | "seal" | "document" | "warehouse" | "hr" })) {
        const routes: Record<string, string> = { finance: "finance-fee-query", seal: "seal-my", document: "documents-register", warehouse: "warehouse", hr: "hr-all" };
        onNavigate?.(routes[row.module]);
      }
    }
  };
  const canOpenBusiness = (row: Log) => Boolean(row.record_id && row.serial_no && ["case", "contract", "customer", "task", "clue", "notary", "evidence", "finance", "seal", "document", "warehouse", "hr"].includes(row.module));

  const columns = [
    { title: "时间", dataIndex: "created_at", width: 165, render: (v: string) => new Date(v).toLocaleString("zh-CN") },
    { title: "模块", dataIndex: "module", width: 80, render: (v: string) => <Tag>{labels[v] || v}</Tag> },
    {
      title: "业务编号",
      dataIndex: "serial_no",
      width: 175,
      render: (value: string, row: Log) => value ? (canOpenBusiness(row) ? <Button type="link" onClick={() => openBusiness(row)}>{value}</Button> : value) : "—",
    },
    { title: "业务标题", dataIndex: "title", width: 220, ellipsis: true },
    { title: "操作", dataIndex: "action", width: 130, render: (v: string) => <b>{v}</b> },
    {
      title: "状态变化",
      key: "status",
      width: 180,
      render: (_: unknown, row: Log) => row.from_status && row.from_status !== row.to_status ? <><Tag>{row.from_status}</Tag> → <Tag color="green">{row.to_status}</Tag></> : row.to_status || "—",
    },
    { title: "操作人", dataIndex: "operator_display_name", width: 100, render: personDisplayName },
    { title: "意见/说明", dataIndex: "comment", ellipsis: true },
  ];

  return (
    <Card className="panel" title="操作日志" extra={<Button icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>}>
      <div className="filter-bar">
        <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} onPressEnter={() => { setPage(1); void load(1); }} allowClear prefix={<SearchOutlined />} placeholder="编号、标题、操作人或意见" />
        <Select value={module || undefined} allowClear placeholder="全部模块" onChange={(value) => setModule(value || "")} options={Object.entries(labels).map(([value, label]) => ({ value, label }))} />
        <Button type="primary" onClick={() => { setPage(1); void load(1); }}>查询</Button>
        <Button onClick={() => { setKeyword(""); setModule(""); setPage(1); void load(1); }}>重置</Button>
      </div>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={rows}
        scroll={{ x: 1350 }}
        pagination={{ current: page, total, pageSize: 50, showTotal: (n) => `共 ${n} 条`, onChange: (p) => { setPage(p); void load(p); } }}
      />
    </Card>
  );
}

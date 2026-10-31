import { useCallback, useEffect, useState } from "react";
import { Button, Input, Select, Space } from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import Table from "../components/ResizableTable";
import { StatusTag } from "../components/common/StatusTag";
import { api } from "../api";

type LegacySealRecord = {
  id: number;
  serial_no: string;
  status: string;
  applicant: string;
  customer: string;
  contract_no: string;
  case_no: string;
  document_name: string;
  seal_type: string;
  print_quantity: string | number;
  application_date: string;
  auditor: string;
  audit_time: string;
  audit_remark: string;
};

const STATUS_OPTIONS = ["已用印", "已拒绝", "已撤回"].map((value) => ({ value, label: value }));

const dateOnly = (value: string) => (value ? value.slice(0, 10) : "");

// 旧系统用印申请（迁移在公文发文里）只读查看，不能修改。
export function LegacySealRecords() {
  const [filters, setFilters] = useState({ official_no: "", applicant: "", customer: "", status: "" });
  const [query, setQuery] = useState(filters);
  const [page, setPage] = useState({ current: 1, pageSize: 20 });
  const [rows, setRows] = useState<LegacySealRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/legacy-seal-records", {
        params: { ...query, page: page.current, page_size: page.pageSize },
      });
      setRows(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setRows([]);
      setTotal(0);
      setError(err?.response?.data?.detail || "旧系统用印记录加载失败");
    } finally {
      setLoading(false);
    }
  }, [query, page]);

  useEffect(() => {
    void load();
  }, [load]);

  const search = () => {
    setPage((current) => ({ ...current, current: 1 }));
    setQuery(filters);
  };

  const columns = [
    { title: "申请编号", dataIndex: "serial_no", width: 170 },
    { title: "状态", dataIndex: "status", width: 90, render: (value: string) => <StatusTag status={value} /> },
    { title: "申请人", dataIndex: "applicant", width: 90 },
    { title: "客户", dataIndex: "customer", width: 200 },
    { title: "合同号", dataIndex: "contract_no", width: 130 },
    { title: "案号", dataIndex: "case_no", width: 130 },
    { title: "文件名称", dataIndex: "document_name", width: 180 },
    { title: "用印类型", dataIndex: "seal_type", width: 100 },
    { title: "份数", dataIndex: "print_quantity", width: 70 },
    { title: "申请日期", dataIndex: "application_date", width: 110, render: dateOnly },
    { title: "审核人", dataIndex: "auditor", width: 90 },
    { title: "审核日期", dataIndex: "audit_time", width: 110, render: dateOnly },
    { title: "审核意见", dataIndex: "audit_remark", width: 200 },
  ];

  return (
    <div className="seal-legacy-records">
      <div className="seal-asset-toolbar">
        <span>旧系统用印记录（只读）</span>
        <Space wrap>
          <Input allowClear placeholder="申请编号" value={filters.official_no} onChange={(event) => setFilters({ ...filters, official_no: event.target.value })} onPressEnter={search} />
          <Input allowClear placeholder="申请人" value={filters.applicant} onChange={(event) => setFilters({ ...filters, applicant: event.target.value })} onPressEnter={search} />
          <Input allowClear placeholder="客户名称或编号" value={filters.customer} onChange={(event) => setFilters({ ...filters, customer: event.target.value })} onPressEnter={search} />
          <Select allowClear placeholder="状态" style={{ width: 110 }} options={STATUS_OPTIONS} value={filters.status || undefined} onChange={(value) => setFilters({ ...filters, status: value || "" })} />
          <Button type="primary" icon={<SearchOutlined />} onClick={search}>查询</Button>
          <Button icon={<ReloadOutlined />} onClick={() => void load()}>刷新</Button>
        </Space>
      </div>
      {error && <div className="dashboard-section-status" role="alert">{error}</div>}
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={rows}
        scroll={{ x: 1670 }}
        pagination={{
          current: page.current,
          pageSize: page.pageSize,
          total,
          showSizeChanger: true,
          showTotal: (count: number) => `共 ${count} 条`,
          onChange: (current: number, pageSize: number) => setPage({ current, pageSize }),
        }}
        locale={{ emptyText: "没有查询到旧系统用印记录。" }}
      />
    </div>
  );
}

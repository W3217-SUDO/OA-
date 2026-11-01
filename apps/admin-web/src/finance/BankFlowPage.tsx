import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Checkbox, DatePicker, Form, Input, Modal, Select, Space, Tabs, message } from "antd";
import type { TableColumnsType } from "antd";
import type { Dayjs } from "dayjs";
import Table from "../components/ResizableTable";
import { api } from "../api";

// 财务中心 › 回款管理 › 银行原始流水：按旧系统 回款(工行/招行/中行/国定工行) 的流水列表，只读镜像表。
// 回款(国定工行) 菜单在旧系统就是国定工行的流水列表，这里固定显示国定工行（fixedBank）。
// 新上传的流水（陶国南 11-01 定两步）：在 回款(工行/中信/中行/招商) 上传后先进“新上传流水”，勾选后“生成到账单”。
type FinanceScope = "firm" | "platform";
type BankKey = "icbc" | "cmb" | "boc" | "gdicbc";
type BankFlowRow = Record<string, string | number> & { id: number };
type BankFlowResponse = {
  columns: { key: string; label: string }[];
  items: BankFlowRow[];
  total: number;
  amount: number;
  page: number;
  page_size: number;
};
type Filters = {
  payer_name?: string;
  payer_account?: string;
  dates?: [Dayjs | null, Dayjs | null] | null;
  status?: string;
  include_deleted?: boolean;
};

const banks: { key: BankKey; label: string }[] = [
  { key: "icbc", label: "工行" },
  { key: "cmb", label: "招行" },
  { key: "boc", label: "中行" },
  { key: "gdicbc", label: "国定工行" },
];
const payerLabels: Record<BankKey, [string, string]> = {
  icbc: ["对方户名", "对方账号"],
  cmb: ["付款人名称", "付款人账号"],
  boc: ["付款人名称", "付款人账号"],
  gdicbc: ["对方户名", "对方账号"],
};
const amountKeys = new Set(["CashedAmount", "TradeAmount"]);

type FlowLine = {
  id: number; bank_label: string; group: string; received_date: string; amount: number; payer_name: string; payer_account: string;
  bank_reference: string; remark: string; status: string; receipt_no: string; file_name: string; row_no: number;
  operator: string; created_at: string; imported_by: string; imported_at: string;
};
type LineFilters = { bank?: string; payer_name?: string; payer_account?: string; dates?: [Dayjs | null, Dayjs | null] | null; status?: string };
const lineBanks = [
  { value: "icbc", label: "工行" }, { value: "citic", label: "中信" }, { value: "boc", label: "中行" }, { value: "cmb", label: "招商" },
];
const money = (value: number) => value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function NewFlowLines({ financeScope }: { financeScope: FinanceScope }) {
  const [form] = Form.useForm<LineFilters>();
  const [filters, setFilters] = useState<LineFilters>({ status: "未导入" });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [data, setData] = useState<{ items: FlowLine[]; total: number; amount: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [working, setWorking] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [from, to] = filters.dates || [];
      const { data: result } = await api.get("/finance/bank-flows/lines", {
        params: {
          finance_scope: financeScope, page, page_size: pageSize, status: filters.status || "",
          ...(filters.bank ? { bank: filters.bank } : {}),
          ...(filters.payer_name?.trim() ? { payer_name: filters.payer_name.trim() } : {}),
          ...(filters.payer_account?.trim() ? { payer_account: filters.payer_account.trim() } : {}),
          ...(from ? { date_from: from.format("YYYY-MM-DD") } : {}),
          ...(to ? { date_to: to.format("YYYY-MM-DD") } : {}),
        },
      });
      setData(result);
      setSelected([]);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "银行流水查询失败");
    } finally {
      setLoading(false);
    }
  }, [financeScope, filters, page, pageSize]);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedRows = (data?.items || []).filter((item) => selected.includes(item.id));
  const selectedAmount = selectedRows.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const act = (kind: "generate" | "delete") => {
    if (!selected.length) {
      message.warning("请先勾选流水");
      return;
    }
    Modal.confirm({
      title: kind === "generate" ? "生成到账单" : "删除流水",
      content: kind === "generate"
        ? `将勾选的 ${selected.length} 条流水（合计 ${money(selectedAmount)} 元）生成到账单，生成后在“回款管理”里认领。确认生成？`
        : `删除勾选的 ${selected.length} 条未导入流水？删除后可在状态“已删除”里查到。`,
      okText: kind === "generate" ? "生成" : "删除",
      okButtonProps: kind === "delete" ? { danger: true } : undefined,
      cancelText: "取消",
      onOk: async () => {
        setWorking(true);
        try {
          const { data: result } = await api.post(`/finance/bank-flows/${kind}`, { ids: selected }, { params: { finance_scope: financeScope } });
          message.success(kind === "generate" ? `已生成 ${result.created} 张到账单` : `已删除 ${result.deleted} 条流水`);
          await load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || (kind === "generate" ? "生成到账单失败" : "删除失败"));
        } finally {
          setWorking(false);
        }
      },
    });
  };

  const columns: TableColumnsType<FlowLine> = [
    { title: "银行", dataIndex: "bank_label", width: 70 },
    { title: "到账日期", dataIndex: "received_date", width: 110 },
    { title: "对方户名", dataIndex: "payer_name", width: 200 },
    { title: "对方账号", dataIndex: "payer_account", width: 180, render: (value: string) => value || "—" },
    { title: "金额", dataIndex: "amount", width: 120, align: "right", render: (value: number) => money(Number(value || 0)) },
    { title: "银行流水号", dataIndex: "bank_reference", width: 200, render: (value: string) => value || "—" },
    { title: "摘要/备注", dataIndex: "remark", width: 200, render: (value: string) => value || "—" },
    { title: "状态", dataIndex: "status", width: 80 },
    { title: "到账单号", dataIndex: "receipt_no", width: 190, render: (value: string) => value || "—" },
    { title: "所属", dataIndex: "group", width: 70, render: (value: string) => value || "—" },
    { title: "来源文件", dataIndex: "file_name", width: 180, render: (value: string, row) => value ? `${value}（第${row.row_no}行）` : "—" },
    { title: "上传人", dataIndex: "operator", width: 100 },
    { title: "上传时间", dataIndex: "created_at", width: 160 },
  ];
  const pending = (filters.status || "") === "未导入";

  return (
    <>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message="在“回款(工行/中信/中行/招商)”上传的银行流水先到这里；勾选“未导入”的流水点“生成到账单”，生成后到“回款管理”认领。"
      />
      <Form
        form={form}
        layout="inline"
        initialValues={{ status: "未导入" }}
        style={{ rowGap: 8, marginBottom: 12 }}
        onFinish={(values) => {
          setFilters(values);
          setPage(1);
        }}
      >
        <Form.Item name="bank" label="银行">
          <Select allowClear placeholder="全部" style={{ width: 100 }} options={lineBanks} />
        </Form.Item>
        <Form.Item name="payer_name" label="对方户名">
          <Input allowClear style={{ width: 180 }} />
        </Form.Item>
        <Form.Item name="payer_account" label="对方账号">
          <Input allowClear style={{ width: 180 }} />
        </Form.Item>
        <Form.Item name="dates" label="到账日期">
          <DatePicker.RangePicker />
        </Form.Item>
        <Form.Item name="status" label="状态">
          <Select
            style={{ width: 110 }}
            options={[
              { value: "未导入", label: "未导入" },
              { value: "已导入", label: "已导入" },
              { value: "已删除", label: "已删除" },
              { value: "", label: "全部（未删除）" },
            ]}
          />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">查询</Button>
            <Button
              onClick={() => {
                form.resetFields();
                setFilters({ status: "未导入" });
                setPage(1);
              }}
            >
              清空
            </Button>
          </Space>
        </Form.Item>
      </Form>
      <Space style={{ marginBottom: 8 }} wrap>
        <Button type="primary" disabled={!pending || !selected.length} loading={working} onClick={() => act("generate")}>
          生成到账单
        </Button>
        <Button danger disabled={!pending || !selected.length} loading={working} onClick={() => act("delete")}>
          删除
        </Button>
        {selected.length > 0 && <span>已选 {selected.length} 条，合计 {money(selectedAmount)} 元</span>}
      </Space>
      <Table<FlowLine>
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={data?.items || []}
        scroll={{ x: "max-content" }}
        rowSelection={pending ? { selectedRowKeys: selected, onChange: (keys) => setSelected(keys.map(Number)) } : undefined}
        pagination={{
          current: page,
          pageSize,
          total: data?.total || 0,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100, 200],
          showTotal: (total) => `共 ${total} 条，金额合计 ${money(data?.amount || 0)}`,
          onChange: (nextPage, nextSize) => {
            setPage(nextSize !== pageSize ? 1 : nextPage);
            setPageSize(nextSize);
          },
        }}
      />
    </>
  );
}

export default function BankFlowPage({ fixedBank, financeScope }: { fixedBank?: BankKey; financeScope?: FinanceScope }) {
  const [view, setView] = useState<"new" | "legacy">(fixedBank ? "legacy" : "new");
  if (!fixedBank && financeScope && view === "new") {
    return (
      <Card title="银行原始流水">
        <Tabs activeKey={view} onChange={(key) => setView(key as "new" | "legacy")}
          items={[{ key: "new", label: "新上传流水" }, { key: "legacy", label: "历史流水（旧系统）" }]} />
        <NewFlowLines financeScope={financeScope} />
      </Card>
    );
  }
  return <LegacyBankFlows fixedBank={fixedBank} onNewView={!fixedBank && financeScope ? () => setView("new") : undefined} />;
}

function LegacyBankFlows({ fixedBank, onNewView }: { fixedBank?: BankKey; onNewView?: () => void }) {
  const [form] = Form.useForm<Filters>();
  const [bank, setBank] = useState<BankKey>(fixedBank || "gdicbc");
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [data, setData] = useState<BankFlowResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [from, to] = filters.dates || [];
      const { data: result } = await api.get<BankFlowResponse>("/finance/bank-flows", {
        params: {
          bank,
          page,
          page_size: pageSize,
          ...(filters.payer_name?.trim() ? { payer_name: filters.payer_name.trim() } : {}),
          ...(filters.payer_account?.trim() ? { payer_account: filters.payer_account.trim() } : {}),
          ...(from ? { date_from: from.format("YYYY-MM-DD") } : {}),
          ...(to ? { date_to: to.format("YYYY-MM-DD") } : {}),
          ...(filters.status ? { status: filters.status } : {}),
          ...(filters.include_deleted ? { include_deleted: true } : {}),
        },
      });
      setData(result);
    } catch {
      message.error("银行流水查询失败");
    } finally {
      setLoading(false);
    }
  }, [bank, filters, page, pageSize]);

  useEffect(() => {
    void load();
  }, [load]);

  const columns: TableColumnsType<BankFlowRow> = [
    ...(data?.columns || []).map((column) => ({
      title: column.label,
      dataIndex: column.key,
      key: column.key,
      width: amountKeys.has(column.key) ? 120 : 150,
      align: amountKeys.has(column.key) ? ("right" as const) : undefined,
      render: (value: string | number) =>
        value === "" || value == null
          ? "—"
          : typeof value === "number" && amountKeys.has(column.key)
            ? value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
            : value,
    })),
    { title: "所属", dataIndex: "group", key: "group", width: 70, render: (value: string) => value || "—" },
    { title: "状态", dataIndex: "status", key: "status", width: 80 },
    { title: "来源文件", dataIndex: "file_name", key: "file_name", width: 180, render: (value: string) => value || "—" },
  ];
  const [nameLabel, accountLabel] = payerLabels[bank];

  return (
    <Card title={fixedBank ? `${banks.find((item) => item.key === fixedBank)?.label}银行到账列表` : "银行原始流水"}>
      {onNewView && <Tabs activeKey="legacy" onChange={(key) => key === "new" && onNewView()}
        items={[{ key: "new", label: "新上传流水" }, { key: "legacy", label: "历史流水（旧系统）" }]} />}
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message="旧系统上传的银行流水（只读）。默认只显示未删除的流水，与旧系统一致；勾选“包含已删除”可查看全部历史流水。"
      />
      {!fixedBank && <Tabs
        activeKey={bank}
        onChange={(key) => {
          setBank(key as BankKey);
          setPage(1);
        }}
        items={banks.map((item) => ({ key: item.key, label: item.label }))}
      />}
      <Form
        form={form}
        layout="inline"
        style={{ rowGap: 8, marginBottom: 12 }}
        onFinish={(values) => {
          setFilters(values);
          setPage(1);
        }}
      >
        <Form.Item name="payer_name" label={nameLabel}>
          <Input allowClear style={{ width: 180 }} />
        </Form.Item>
        <Form.Item name="payer_account" label={accountLabel}>
          <Input allowClear style={{ width: 180 }} />
        </Form.Item>
        <Form.Item name="dates" label="回款日期">
          <DatePicker.RangePicker />
        </Form.Item>
        <Form.Item name="status" label="状态">
          <Select
            allowClear
            placeholder="请选择"
            style={{ width: 110 }}
            options={[
              { value: "1", label: "未导入" },
              { value: "2", label: "已导入" },
            ]}
          />
        </Form.Item>
        <Form.Item name="include_deleted" valuePropName="checked">
          <Checkbox>包含已删除</Checkbox>
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">
              查询
            </Button>
            <Button
              onClick={() => {
                form.resetFields();
                setFilters({});
                setPage(1);
              }}
            >
              清空
            </Button>
          </Space>
        </Form.Item>
      </Form>
      <Table<BankFlowRow>
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={data?.items || []}
        scroll={{ x: "max-content" }}
        pagination={{
          current: page,
          pageSize,
          total: data?.total || 0,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100, 200],
          showTotal: (total) =>
            `共 ${total} 条，金额合计 ${(data?.amount || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          onChange: (nextPage, nextSize) => {
            setPage(nextSize !== pageSize ? 1 : nextPage);
            setPageSize(nextSize);
          },
        }}
      />
    </Card>
  );
}

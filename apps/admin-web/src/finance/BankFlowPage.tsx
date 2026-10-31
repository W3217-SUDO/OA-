import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Checkbox, DatePicker, Form, Input, Select, Space, Tabs, message } from "antd";
import type { TableColumnsType } from "antd";
import type { Dayjs } from "dayjs";
import Table from "../components/ResizableTable";
import { api } from "../api";

// 财务中心 › 回款管理 › 银行原始流水：按旧系统 回款(工行/招行/中行/国定工行) 的流水列表，只读镜像表。
// 回款(国定工行) 菜单在旧系统就是国定工行的流水列表，这里固定显示国定工行（fixedBank）。
// 上传银行文件、从流水生成到账单暂不做。
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

export default function BankFlowPage({ fixedBank }: { fixedBank?: BankKey }) {
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

import { ReloadOutlined } from "@ant-design/icons";
import {
Alert,
Button,
Card,
Checkbox,
Descriptions,
Drawer,
Input,
Select,
Space,
Statistic,
Table,
Tabs,
Tag,
} from "antd";
import dayjs from "dayjs";
import { money } from "./constants";
import type { LegacyFinanceRecord,LegacyFinanceSummary } from "./types";

interface LegacyHistoryPanelProps {
  rows: LegacyFinanceRecord[];
  loading: boolean;
  meta: { total: number; page: number; pageSize: number };
  summary: LegacyFinanceSummary;
  detail: LegacyFinanceRecord | null;
  detailLoading: boolean;
  keyword: string;
  kind: string;
  statusCode: string;
  includeInactive: boolean;
  onKeywordChange: (value: string) => void;
  onKindChange: (value: string) => void;
  onStatusCodeChange: (value: string) => void;
  onIncludeInactiveChange: (checked: boolean) => void;
  onLoad: (page?: number, pageSize?: number) => void;
  onOpenDetail: (recordId: number) => void;
  onCloseDetail: () => void;
}

const KIND_LABELS: Record<LegacyFinanceRecord["record_kind"], string> = {
  ap_payment: "历史请款",
  ar_payment: "历史回款",
  invoice: "历史开票",
  ap_packing: "历史付款打包",
  case_fee: "历史案件应收费用",
};

const mappingLabel = (value?: string) => {
  const normalized = String(value || "").trim();
  if (!normalized || ["matched", "exact"].includes(normalized)) return "已精确关联";
  if (/parent_not_present|orphan|missing_parent/i.test(normalized)) return "孤儿 / 父级缺失";
  if (normalized === "missing") return "缺少业务关联";
  if (/unmapped|not_mapped|unlinked/i.test(normalized)) return "未关联实时业务";
  return normalized;
};

const mappingColor = (value?: string) => {
  const normalized = String(value || "");
  if (/parent_not_present|orphan|missing_parent/i.test(normalized)) return "orange";
  if (/unmapped|not_mapped|unlinked/i.test(normalized)) return "default";
  return "green";
};

const statusLabel = (value?: string) => {
  const normalized = String(value || "").trim();
  const legacyCode = normalized.match(/^legacy_status_(.+)$/i);
  return legacyCode ? `旧状态码 ${legacyCode[1]}` : (normalized || "未标注");
};

export function LegacyHistoryPanel({
  rows,
  loading,
  meta,
  summary,
  detail,
  detailLoading,
  keyword,
  kind,
  statusCode,
  includeInactive,
  onKeywordChange,
  onKindChange,
  onStatusCodeChange,
  onIncludeInactiveChange,
  onLoad,
  onOpenDetail,
  onCloseDetail,
}: LegacyHistoryPanelProps) {
  const amountVisible = summary.amount_visible;

  const formatAmount = (value: number | null | undefined) =>
    amountVisible ? money(Number(value || 0)) : "无权限";

  const summaryByKind = (kindKey: LegacyFinanceRecord["record_kind"]) =>
    summary.records
      .filter((row) => row.record_kind === kindKey && (includeInactive || row.is_active))
      .reduce(
        (total, row) => ({
          count: total.count + Number(row.count || 0),
          amount: total.amount + Number(row.primary_amount || 0),
        }),
        { count: 0, amount: 0 },
      );

  const columns = [
    {
      title: "历史编号",
      dataIndex: "legacy_id",
      width: 148,
      render: (value: string, row: LegacyFinanceRecord) => (
        <Button type="link" onClick={() => onOpenDetail(row.id)}>
          {value || `#${row.id}`}
        </Button>
      ),
    },
    {
      title: "账本类型",
      dataIndex: "record_kind",
      width: 112,
      render: (value: LegacyFinanceRecord["record_kind"]) =>
        KIND_LABELS[value] || value,
    },
    {
      title: "状态",
      dataIndex: "status_label",
      width: 108,
      render: (value: string, row: LegacyFinanceRecord) => (
        <Tag color={row.is_active ? "blue" : "default"}>{statusLabel(value)}</Tag>
      ),
    },
    {
      title: "合同编号",
      dataIndex: "legacy_contract_no",
      width: 150,
      render: (value: string) => value || "—",
    },
    {
      title: "案件编号",
      dataIndex: "legacy_case_no",
      width: 150,
      render: (value: string) => value || "—",
    },
    {
      title: "客户编号",
      dataIndex: "legacy_customer_no",
      width: 140,
      render: (value: string) => value || "—",
    },
    {
      title: "金额",
      dataIndex: "primary_amount",
      align: "right" as const,
      width: 126,
      render: formatAmount,
    },
    {
      title: "分配",
      dataIndex: "allocation_count",
      align: "right" as const,
      width: 70,
    },
    {
      title: "发票文件",
      dataIndex: "file_count",
      align: "right" as const,
      width: 88,
    },
    {
      title: "关联状态",
      dataIndex: "mapping_status",
      width: 142,
      render: (value: string) => (
        <Tag color={mappingColor(value)}>{mappingLabel(value)}</Tag>
      ),
    },
    { title: "来源表", dataIndex: "source_table", width: 150 },
    {
      title: "导入时间",
      dataIndex: "imported_at",
      width: 170,
      render: (value: string) =>
        value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—",
    },
    {
      title: "审批记录",
      dataIndex: "audit_count",
      align: "right" as const,
      width: 82,
    },
  ];

  const orphanCount =
    summary.orphan_allocations.reduce(
      (sum, item) => sum + Number(item.count || 0),
      0,
    ) +
    summary.orphan_files.reduce(
      (sum, item) => sum + Number(item.count || 0),
      0,
    ) +
    summary.orphan_audits.reduce(
      (sum, item) => sum + Number(item.count || 0),
      0,
    );

  return (
    <>
      <Alert
        className="finance-rule"
        type="info"
        showIcon
        title="历史财务账本"
        description="历史请款、回款、开票及付款打包与实时财务口径完全分离；仅可检索和查看原始迁移信息。"
      />
      <div className="finance-stats">
        {(
          [
            "ap_payment",
            "ar_payment",
            "invoice",
            "ap_packing",
            "case_fee",
          ] as LegacyFinanceRecord["record_kind"][]
        ).map((kindKey) => {
          const item = summaryByKind(kindKey);
          return (
            <Card key={kindKey} size="small">
              <Statistic
                title={KIND_LABELS[kindKey]}
                value={amountVisible ? item.amount : item.count}
                suffix={amountVisible ? "元" : "条"}
                formatter={(value) =>
                  amountVisible ? money(Number(value || 0)) : String(value)
                }
              />
              <div className="finance-stat-caption">
                {item.count.toLocaleString("zh-CN")} 条记录
              </div>
            </Card>
          );
        })}
        {orphanCount > 0 ? (
          <Card size="small">
            <Statistic title="孤儿历史引用" value={orphanCount} suffix="条" />
            <div className="finance-stat-caption">
              父记录在旧库快照中缺失，已保留来源信息
            </div>
          </Card>
        ) : null}
      </div>
      <Space wrap style={{ margin: "8px 0 12px" }}>
        <Input.Search
          aria-label="历史财务账本检索"
          placeholder="历史编号、合同、案件或客户编号"
          value={keyword}
          onChange={(event) => onKeywordChange(event.target.value)}
          onSearch={() => onLoad(1, meta.pageSize)}
          style={{ width: 250 }}
        />
        <Input
          aria-label="旧库状态码"
          placeholder="旧库状态码"
          value={statusCode}
          onChange={(event) => onStatusCodeChange(event.target.value)}
          onPressEnter={() => onLoad(1, meta.pageSize)}
          style={{ width: 118 }}
        />
        <Select
          aria-label="历史财务账本类型"
          value={kind || undefined}
          placeholder="全部账本类型"
          allowClear
          options={(
            [
              "ap_payment",
              "ar_payment",
              "invoice",
              "ap_packing",
              "case_fee",
            ] as LegacyFinanceRecord["record_kind"][]
          ).map((kindKey) => ({
            value: kindKey,
            label: KIND_LABELS[kindKey],
          }))}
          onChange={(value) => onKindChange(value || "")}
          style={{ width: 150 }}
        />
        <Checkbox
          checked={includeInactive}
          onChange={(event) => onIncludeInactiveChange(event.target.checked)}
        >
          显示已停用
        </Checkbox>
        <Button icon={<ReloadOutlined />} onClick={() => onLoad()}>
          刷新
        </Button>
        <Tag color="default">只读</Tag>
        {amountVisible === false && (
          <Tag color="orange">金额无查看权限</Tag>
        )}
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        size="small"
        columns={columns}
        dataSource={rows}
        pagination={{
          current: meta.page,
          pageSize: meta.pageSize,
          total: meta.total,
          showSizeChanger: true,
          pageSizeOptions: [30, 50, 100, 200],
          onChange: (page, pageSize) => onLoad(page, pageSize),
        }}
        scroll={{ x: 1550 }}
      />
      <Drawer
        open={detailLoading || Boolean(detail)}
        title="历史财务账本明细"
        width={760}
        placement="right"
        onClose={onCloseDetail}
        footer={<Tag color="default">只读历史镜像</Tag>}
      >
        {detailLoading ? (
          <div className="finance-empty">正在加载历史财务明细...</div>
        ) : detail ? (
          <>
            <Alert
              type={
                /parent_not_present|orphan|missing_parent/i.test(
                  String(detail.mapping_status || ""),
                )
                  ? "warning"
                  : "info"
              }
              showIcon
              title={mappingLabel(detail.mapping_status)}
              description="此记录来自旧 FAM 数据迁移，仅用于审计追溯，不参与实时财务汇总或业务操作。"
            />
            <Descriptions
              column={2}
              size="small"
              bordered
              style={{ marginTop: 12 }}
            >
              <Descriptions.Item label="历史编号">
                {detail.legacy_id || `#${detail.id}`}
              </Descriptions.Item>
              <Descriptions.Item label="账本类型">
                {KIND_LABELS[detail.record_kind]}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {statusLabel(detail.status_label)}
              </Descriptions.Item>
              <Descriptions.Item label="金额">
                {formatAmount(detail.primary_amount)}
              </Descriptions.Item>
              <Descriptions.Item label="合同编号">
                {detail.legacy_contract_no || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="案件编号">
                {detail.legacy_case_no || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="客户编号">
                {detail.legacy_customer_no || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="来源表">
                {detail.source_table || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="关联状态">
                {mappingLabel(detail.mapping_status)}
              </Descriptions.Item>
              <Descriptions.Item label="导入时间">
                {detail.imported_at
                  ? dayjs(detail.imported_at).format("YYYY-MM-DD HH:mm")
                  : "—"}
              </Descriptions.Item>
              <Descriptions.Item label="币种来源">
                {detail.currency === "UNRECORDED_IN_LEGACY_SCHEMA"
                  ? "旧库未记录"
                  : detail.currency || "旧库未记录"}
              </Descriptions.Item>
              <Descriptions.Item label="审批记录数">
                {detail.audit_count || 0}
              </Descriptions.Item>
            </Descriptions>
            <Tabs
              style={{ marginTop: 14 }}
              items={[
                {
                  key: "allocations",
                  label: `分配行（${detail.allocations?.length || 0}）`,
                  children: (
                    <Table
                      size="small"
                      rowKey="id"
                      pagination={false}
                      dataSource={detail.allocations || []}
                      columns={[
                        { title: "来源键", dataIndex: "legacy_key", width: 120 },
                        {
                          title: "类型",
                          dataIndex: "allocation_kind",
                          width: 100,
                        },
                        {
                          title: "案件编号",
                          dataIndex: "legacy_case_no",
                          width: 140,
                          render: (value: string) => value || "—",
                        },
                        {
                          title: "金额",
                          dataIndex: "amount",
                          align: "right" as const,
                          width: 110,
                          render: formatAmount,
                        },
                        {
                          title: "关联状态",
                          dataIndex: "mapping_status",
                          width: 130,
                          render: (value: string) => mappingLabel(value),
                        },
                      ]}
                      scroll={{ x: 620 }}
                    />
                  ),
                },
                {
                  key: "files",
                  label: `发票文件（${detail.files?.length || 0}）`,
                  children: (
                    <Table
                      size="small"
                      rowKey="id"
                      pagination={false}
                      dataSource={detail.files || []}
                      columns={[
                        {
                          title: "文件名",
                          dataIndex: "filename",
                          render: (value: string) =>
                            value || "未保留文件名",
                        },
                        {
                          title: "大小",
                          dataIndex: "size_bytes",
                          width: 100,
                          render: (value: number) =>
                            value
                              ? `${Math.ceil(Number(value) / 1024)} KB`
                              : "—",
                        },
                        {
                          title: "物理文件",
                          dataIndex: "physical_file_verified",
                          width: 100,
                          render: (value: boolean) => (
                            <Tag color={value ? "green" : "orange"}>
                              {value ? "已验证" : "仅元数据"}
                            </Tag>
                          ),
                        },
                        {
                          title: "开票日期",
                          dataIndex: "invoice_date",
                          width: 110,
                          render: (value: string) => value || "—",
                        },
                      ]}
                      scroll={{ x: 620 }}
                    />
                  ),
                },
                {
                  key: "legacy-fields",
                  label: "旧库原始金额与状态",
                  children: (
                    <Descriptions column={2} size="small" bordered>
                      {Object.entries(detail.legacy_statuses || {}).map(
                        ([key, value]) => (
                          <Descriptions.Item key={`status-${key}`} label={key}>
                            {String(value ?? "")}
                          </Descriptions.Item>
                        ),
                      )}
                      {Object.entries(detail.legacy_amounts || {}).map(
                        ([key, value]) => (
                          <Descriptions.Item key={`amount-${key}`} label={key}>
                            {String(value ?? "")}
                          </Descriptions.Item>
                        ),
                      )}
                    </Descriptions>
                  ),
                },
                {
                  key: "audits",
                  label: `审批历史（${detail.audits?.length || 0}）`,
                  children: (
                    <Table
                      size="small"
                      rowKey="id"
                      pagination={false}
                      dataSource={detail.audits || []}
                      columns={[
                        { title: "审批编号", dataIndex: "legacy_id", width: 92 },
                        {
                          title: "状态码",
                          dataIndex: "audit_status_code",
                          width: 70,
                        },
                        { title: "流程", dataIndex: "audit_flow_id", width: 70 },
                        {
                          title: "节点",
                          dataIndex: "audit_flow_node_id",
                          width: 70,
                        },
                        { title: "轮次", dataIndex: "audit_round_id", width: 70 },
                        {
                          title: "审批人",
                          dataIndex: "auditor_display_name",
                          width: 100,
                          render: (value: string) => value || "—",
                        },
                        {
                          title: "审批时间",
                          dataIndex: "audit_date",
                          width: 160,
                          render: (value: string) =>
                            value
                              ? dayjs(value).format("YYYY-MM-DD HH:mm")
                              : "-",
                        },
                        {
                          title: "审批意见",
                          dataIndex: "audit_content",
                          width: 220,
                          render: (value: string) => value || "-",
                        },
                      ]}
                      scroll={{ x: 900 }}
                    />
                  ),
                },
                {
                  key: "payload",
                  label: "源数据",
                  children: (
                    <pre className="finance-source-payload">
                      {JSON.stringify(detail.source_payload || {}, null, 2)}
                    </pre>
                  ),
                },
              ]}
            />
          </>
        ) : null}
      </Drawer>
    </>
  );
}

export default LegacyHistoryPanel;

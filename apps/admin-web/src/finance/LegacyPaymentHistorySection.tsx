import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Collapse, Descriptions, Drawer, Input, Select, Space, Tag } from "antd";
import { useState } from "react";
import Table from "../components/ResizableTable";
import { money } from "./constants";
import {
  paymentHistoryViews,
  paymentStatusLabels,
  useLegacyPaymentHistory,
  type LegacyPaymentRow,
  type LegacyPaymentView,
} from "./useLegacyPaymentHistory";

const displayValue = (value: string | number | null | undefined) =>
  value == null || value === "" ? "—" : value;
const displayDate = (value: string | null) => value ? value.slice(0, 10) : "—";

export function LegacyPaymentHistorySection({ view }: { view: LegacyPaymentView }) {
  const config = paymentHistoryViews[view];
  const [draftKeyword, setDraftKeyword] = useState("");
  const {
    result, loading, error, statusCode, page, pageSize,
    selected, detail, detailLoading, detailError,
    setKeyword, setStatusCode, setPage, setPageSize, setRevision,
    openDetail, closeDetail,
  } = useLegacyPaymentHistory(view);

  const amount = (value: number | null) =>
    result?.amount_visible === false ? "无权限" : value == null ? "—" : money(value);

  const columns = [
    {
      title: "申请单号",
      dataIndex: "application_no",
      width: 160,
      render: (value: string | null, row: LegacyPaymentRow) => (
        <Button type="link" onClick={() => void openDetail(row)}>
          {value || row.legacy_id}
        </Button>
      ),
    },
    {
      title: "历史状态",
      dataIndex: "status_label",
      width: 110,
      render: (value: string, row: LegacyPaymentRow) => (
        <Tag color={row.status_code === "7" ? "green" : "blue"}>
          {value || paymentStatusLabels[row.status_code] || `状态 ${row.status_code}`}
        </Tag>
      ),
    },
    { title: "申请日期", dataIndex: "application_date", width: 120, render: displayDate },
    { title: "申请人", dataIndex: "applicant", width: 120, render: displayValue },
    { title: "付款截止日", dataIndex: "deadline", width: 120, render: displayDate },
    { title: "付款日期", dataIndex: "payment_date", width: 120, render: displayDate },
    { title: "付款包号码", dataIndex: "package_no", width: 160, render: displayValue },
    { title: "合同编号", dataIndex: "legacy_contract_no", width: 150, render: displayValue },
    {
      title: "案件编号",
      dataIndex: "case_numbers",
      width: 180,
      render: (value: string[]) => value?.length ? value.join("、") : "—",
    },
    { title: "客户编号", dataIndex: "legacy_customer_no", width: 140, render: displayValue },
    { title: "交款人", dataIndex: "payer_name", width: 130, render: displayValue },
    { title: "金额", dataIndex: "primary_amount", align: "right" as const, width: 130, render: amount },
  ];

  return (
    <>
      <Collapse
        style={{ marginTop: 12 }}
        defaultActiveKey={["history"]}
        items={[{
          key: "history",
          label: `${config.title}（只读，共 ${result?.total ?? "—"} 条）`,
          children: <>
            <Alert
              type="info"
              showIcon
              title={config.title}
              description={`${config.description} 历史记录仅供查询，不进入现行审批、付款、打印或核销操作。`}
            />
            {error && <Alert style={{ marginTop: 12 }} type="error" showIcon title="历史请款加载失败" description={error} />}
            <Space wrap style={{ margin: "12px 0" }}>
              {(result ? config.statusCodes : []).map((code) => (
                <Tag key={code} color={statusCode === code ? "blue" : "default"}>
                  {paymentStatusLabels[code]}（{result?.status_counts[code] ?? 0}）
                </Tag>
              ))}
            </Space>
            <Space wrap style={{ marginBottom: 12 }}>
              <Input.Search
                aria-label="历史请款检索"
                placeholder="申请单号、合同、案件或客户编号"
                value={draftKeyword}
                onChange={(event) => setDraftKeyword(event.target.value)}
                onSearch={() => { setKeyword(draftKeyword.trim()); setPage(1); }}
                style={{ width: 310 }}
              />
              {config.statusCodes.length > 1 && (
                <Select
                  aria-label="历史请款状态"
                  placeholder="全部历史状态"
                  value={statusCode || undefined}
                  allowClear
                  options={config.statusCodes.map((code) => ({ value: code, label: `${paymentStatusLabels[code]}（${result?.status_counts[code] ?? 0}）` }))}
                  onChange={(value) => { setStatusCode(value || ""); setPage(1); }}
                  style={{ width: 190 }}
                />
              )}
              <Button icon={<ReloadOutlined />} onClick={() => setRevision((value) => value + 1)}>刷新</Button>
              <Tag>只读</Tag>
              {result?.amount_visible === false && <Tag color="orange">金额无查看权限</Tag>}
            </Space>
            <Table
              rowKey="id"
              loading={loading}
              size="small"
              columns={columns}
              dataSource={result?.items || []}
              locale={{ emptyText: error || config.emptyText }}
              pagination={{
                current: page,
                pageSize,
                total: result?.total || 0,
                showSizeChanger: true,
                pageSizeOptions: [30, 50, 100, 200],
                onChange: (nextPage, nextPageSize) => { setPage(nextPage); setPageSize(nextPageSize); },
              }}
              scroll={{ x: 1680 }}
            />
          </>,
        }]}
      />
      <Drawer
        open={Boolean(selected)}
        title={`历史请款单 ${selected?.application_no || selected?.legacy_id || ""}`}
        placement="right"
        width={760}
        onClose={closeDetail}
        footer={<Tag>只读历史记录</Tag>}
      >
        {selected && <>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="申请单号">{displayValue(selected.application_no)}</Descriptions.Item>
            <Descriptions.Item label="历史状态">{displayValue(selected.status_label)}（状态 {selected.status_code}）</Descriptions.Item>
            <Descriptions.Item label="申请日期">{displayDate(selected.application_date)}</Descriptions.Item>
            <Descriptions.Item label="申请人">{displayValue(selected.applicant)}</Descriptions.Item>
            <Descriptions.Item label="付款截止日">{displayDate(selected.deadline)}</Descriptions.Item>
            <Descriptions.Item label="付款日期">{displayDate(selected.payment_date)}</Descriptions.Item>
            <Descriptions.Item label="付款包号码">{displayValue(selected.package_no)}</Descriptions.Item>
            <Descriptions.Item label="金额">{amount(selected.primary_amount)}</Descriptions.Item>
            <Descriptions.Item label="合同编号">{displayValue(selected.legacy_contract_no)}</Descriptions.Item>
            <Descriptions.Item label="案件编号">{selected.case_numbers.join("、") || "—"}</Descriptions.Item>
            <Descriptions.Item label="客户编号">{displayValue(selected.legacy_customer_no)}</Descriptions.Item>
            <Descriptions.Item label="交款人">{displayValue(selected.payer_name)}</Descriptions.Item>
          </Descriptions>
          {detailLoading && <div style={{ marginTop: 12 }}>正在加载历史审批记录...</div>}
          {detailError && <Alert style={{ marginTop: 12 }} type="error" showIcon title={detailError} />}
          {detail && <>
            <h4 style={{ marginTop: 20 }}>旧系统审批记录</h4>
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={detail.audits || []}
              columns={[
                { title: "状态码", dataIndex: "audit_status_code", width: 85 },
                { title: "审批人", dataIndex: "auditor_display_name", width: 130, render: displayValue },
                { title: "审批时间", dataIndex: "audit_date", width: 165, render: displayValue },
                { title: "审批意见", dataIndex: "audit_content", render: displayValue },
              ]}
              scroll={{ x: 620 }}
            />
          </>}
        </>}
      </Drawer>
    </>
  );
}

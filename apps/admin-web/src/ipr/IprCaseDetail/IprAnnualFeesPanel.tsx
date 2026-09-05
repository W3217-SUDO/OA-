import { Alert,Button,Card,DatePicker,Form,Input,InputNumber,Modal,Select,Space,Table,Tag } from "antd";
import type { AnnualFee,IprDetailPageState,IprRecord } from "../types";

interface IprAnnualFeesPanelProps {
  detail: IprRecord;
  iprSectionErrors: { annualFees: string };
  annualFees: AnnualFee[];
  annualFeesPageState: IprDetailPageState;
  annualFeeYearFilter: number | undefined;
  annualFeesCanManage: boolean;
  annualFeeOpen: boolean;
  editingAnnualFee: AnnualFee | null;
  annualFeeForm: any;
  onRefresh: () => void;
  onYearFilterChange: (year: number | undefined) => void;
  onOpenEditor: (row?: AnnualFee) => void;
  onCloseEditor: () => void;
  onSave: () => void;
  onDelete: (row: AnnualFee) => Promise<void>;
  confirmIprDeletion: (kind: string, label: string, operation: () => Promise<void>) => void;
}

export function IprAnnualFeesPanel({
  detail,
  iprSectionErrors,
  annualFees,
  annualFeesPageState,
  annualFeeYearFilter,
  annualFeesCanManage,
  annualFeeOpen,
  editingAnnualFee,
  annualFeeForm,
  onRefresh,
  onYearFilterChange,
  onOpenEditor,
  onCloseEditor,
  onSave,
  onDelete,
  confirmIprDeletion,
}: IprAnnualFeesPanelProps) {
  const annualFeesPagination = {
    current: annualFeesPageState.page,
    pageSize: annualFeesPageState.pageSize,
    total: annualFeesPageState.total,
    showSizeChanger: true,
    pageSizeOptions: ["15", "20", "50"],
    onChange: () => {},
  };

  return (
    <>
      <Card
        size="small"
        title="年费明细"
        style={{ marginTop: 16 }}
        extra={
          <Space size={8} wrap>
            <InputNumber
              min={2000}
              max={2100}
              placeholder="按缴费年度筛选"
              style={{ width: 150 }}
              value={annualFeeYearFilter}
              onChange={(value) => {
                const feeYear =
                  typeof value === "number" ? value : undefined;
                onYearFilterChange(feeYear);
              }}
            />
            <Button size="small" onClick={onRefresh}>
              刷新
            </Button>
            {annualFeesCanManage ? (
              <Button
                type="primary"
                size="small"
                onClick={() => onOpenEditor()}
              >
                新增年费
              </Button>
            ) : null}
          </Space>
        }
      >
        {iprSectionErrors.annualFees ? (
          <Alert
            type="error"
            showIcon
            message={iprSectionErrors.annualFees}
            style={{ marginBottom: 12 }}
          />
        ) : null}
        <Table
          rowKey="id"
          size="small"
          pagination={annualFeesPagination}
          dataSource={annualFees}
          scroll={{ x: 1050 }}
          locale={{ emptyText: "暂无年费明细" }}
          columns={[
            {
              title: "缴费年度",
              dataIndex: "fee_year",
              width: 100,
              render: (value) => (value ? `${value} 年` : "—"),
            },
            {
              title: "费用名称",
              dataIndex: "fee_name",
              width: 150,
              ellipsis: true,
            },
            {
              title: "金额",
              dataIndex: "amount",
              width: 120,
              render: (value, row: AnnualFee) =>
                value == null
                  ? "—"
                  : `${row.currency || "CNY"} ${Number(value).toFixed(2)}`,
            },
            {
              title: "缴费期限",
              dataIndex: "due_date",
              width: 112,
              render: (value) => value || "—",
            },
            {
              title: "缴费日期",
              dataIndex: "paid_date",
              width: 112,
              render: (value) => value || "—",
            },
            {
              title: "提醒",
              width: 142,
              render: (_, row: AnnualFee) =>
                row.reminder_date ? (
                  <Space size={4}>
                    <Tag color={row.reminder_id ? "blue" : "gold"}>
                      {row.reminder_id ? "已建提醒" : "待同步"}
                    </Tag>
                    <span>{row.reminder_date}</span>
                  </Space>
                ) : (
                  "未设提醒"
                ),
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 92,
              render: (value) => (
                <Tag
                  color={
                    value === "已缴"
                      ? "green"
                      : value === "未缴"
                        ? "red"
                        : "gold"
                  }
                >
                  {value}
                </Tag>
              ),
            },
            {
              title: "说明",
              dataIndex: "notes",
              ellipsis: true,
              render: (value) => value || "—",
            },
            {
              title: "操作",
              fixed: "right",
              width: 122,
              render: (_, row: AnnualFee) =>
                annualFeesCanManage ? (
                  <Space size={0}>
                    <Button type="link" onClick={() => onOpenEditor(row)}>
                      编辑
                    </Button>
                    <Button
                      type="link"
                      danger
                      onClick={() =>
                        confirmIprDeletion(
                          "annual-fee",
                          `${row.fee_year}年${row.fee_name}`,
                          () => onDelete(row)
                        )
                      }
                    >
                      删除
                    </Button>
                  </Space>
                ) : (
                  "—"
                ),
            },
          ]}
        />
      </Card>

      <Modal
        open={annualFeeOpen}
        title={editingAnnualFee ? "编辑年费明细" : "新增年费明细"}
        onCancel={onCloseEditor}
        onOk={onSave}
        okText={editingAnnualFee ? "保存修改" : "新增"}
      >
        <Form form={annualFeeForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              name="fee_year"
              label="缴费年度"
              rules={[{ required: true, message: "请填写缴费年度" }]}
            >
              <InputNumber min={2000} max={2100} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              name="fee_name"
              label="费用名称"
              rules={[
                { required: true, whitespace: true, message: "请填写费用名称" },
              ]}
            >
              <Input maxLength={255} />
            </Form.Item>
            <Form.Item
              name="amount"
              label="金额"
              rules={[{ required: true, message: "请填写金额" }]}
            >
              <InputNumber
                min={0}
                precision={2}
                style={{ width: "100%" }}
              />
            </Form.Item>
            <Form.Item name="currency" label="币种">
              <Select
                options={[
                  { value: "CNY", label: "CNY（人民币）" },
                  { value: "USD", label: "USD（美元）" },
                  { value: "EUR", label: "EUR（欧元）" },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="due_date"
              label="缴费期限"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              name="status"
              label="缴费状态"
              rules={[{ required: true }]}
            >
              <Select
                options={["待缴", "已缴", "未缴"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item name="paid_date" label="缴费日期">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="reminder_date" label="提醒日期">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item name="notes" label="说明">
            <Input.TextArea rows={3} maxLength={1000} />
          </Form.Item>
          <div style={{ color: "#666" }}>
            填写提醒日期后，系统会为这笔年费同步“缴纳年费”提醒；提醒日期不得晚于缴费期限。
          </div>
        </Form>
      </Modal>
    </>
  );
}

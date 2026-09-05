import { Button, Card, DatePicker, Dropdown, Form, Input, Popconfirm, Select, Space, Table, Tag } from "antd";
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  SearchOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import type { FormInstance } from "antd";
import type { Key } from "react";
import type { ReceiptRow, Attachment } from "./types";
import { personDisplayName } from "./constants";

interface DocumentReceiptPanelProps {
  tab: string;
  loading: boolean;
  receiptForm: FormInstance;
  searchedReceipts: ReceiptRow[];
  selectedReceiptKeys: Key[];
  selectedFormalReceipts: ReceiptRow[];
  receiptAttachment: (r: ReceiptRow) => Attachment | undefined;
  onSelectionChange: (keys: Key[]) => void;
  onSearch: () => void;
  onClearSearch: () => void;
  onShowReceipt: (r: ReceiptRow) => void;
  onPreviewReceiptFile: (r: ReceiptRow) => void;
  onOpenCaseDetail: (caseNo: string) => void;
  onOpenUpload: (target?: any, category?: string) => void;
  onDeleteSelected: () => void;
  onOpenReceiptDateEditor: () => void;
  onOpenCaseLinker: () => void;
  onUpdateProcessStatus: (processed: boolean) => void;
  onExport: () => void;
  onMoreAction: (key: string) => void;
}

const receiptMoreActionItems = [
  { key: "upload-case-files", label: "上传案件文档" },
  {
    key: "case-fees",
    label: "新增案件费用",
    children: [
      { key: "case-fee-office", label: "新增官费" },
      { key: "case-fee-agent", label: "新增代理费" },
      { key: "case-fee-other", label: "新增其他费用" },
    ],
  },
  { key: "internal-fee", label: "新增内部费用" },
  {
    key: "batch-update",
    label: "批量修改",
    children: [
      { key: "hearing-lawyer", label: "修改开庭律师" },
      { key: "handling-lawyer", label: "修改经办律师" },
      { key: "assistant", label: "修改律师助理" },
      { key: "case-phase", label: "修改案件阶段" },
    ],
  },
  { key: "authorization-letter", label: "生成授权委托书" },
  { key: "law-firm-letter", label: "生成律所函" },
  { key: "identity-certificate", label: "生成身份证明" },
  { key: "settlement-list", label: "生成结算提成表" },
  { key: "case-tasks", label: "案件任务" },
  { key: "case-logs", label: "案件日志" },
];

export function DocumentReceiptPanel({
  tab,
  loading,
  receiptForm,
  searchedReceipts,
  selectedReceiptKeys,
  selectedFormalReceipts,
  receiptAttachment,
  onSelectionChange,
  onSearch,
  onClearSearch,
  onShowReceipt,
  onPreviewReceiptFile,
  onOpenCaseDetail,
  onOpenUpload,
  onDeleteSelected,
  onOpenReceiptDateEditor,
  onOpenCaseLinker,
  onUpdateProcessStatus,
  onExport,
  onMoreAction,
}: DocumentReceiptPanelProps) {
  const isOfficial = tab === "official";

  const officialColumns = [
    {
      title: "案号",
      key: "case_no",
      width: 145,
      render: (_: unknown, r: ReceiptRow) =>
        r.data.case_no ? (
          <Button type="link" onClick={() => onOpenCaseDetail(r.data.case_no!)}>
            {r.data.case_no}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "原告",
      key: "plaintiff",
      width: 210,
      render: (_: unknown, r: ReceiptRow) => r.data.plaintiff || "—",
    },
    {
      title: "被告",
      key: "defendant",
      width: 245,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.defendant || "—",
    },
    {
      title: "文件名称",
      dataIndex: "title",
      width: 430,
      ellipsis: true,
      render: (v: string, r: ReceiptRow) => (
        <Space size={0}>
          <a onClick={() => onShowReceipt(r)}>{v}</a>
          {receiptAttachment(r) && (
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => onPreviewReceiptFile(r)}
            >
              查看
            </Button>
          )}
        </Space>
      ),
    },
    {
      title: "文件日期",
      key: "document_date",
      width: 105,
      render: (_: unknown, r: ReceiptRow) => r.data.document_date || "—",
    },
    {
      title: "上传日期",
      key: "uploaded_at",
      width: 105,
      render: (_: unknown, r: ReceiptRow) => r.data.uploaded_at || "—",
    },
    {
      title: "上传人",
      key: "uploader",
      width: 90,
      render: (_: unknown, r: ReceiptRow) =>
        personDisplayName(r.data.uploader_display_name || r.owner_display_name),
    },
    {
      title: "状态",
      key: "import_status",
      width: 80,
      render: (_: unknown, r: ReceiptRow) => (
        <span className="receipt-imported">
          {r.data.import_status || "已导入"}
        </span>
      ),
    },
    {
      title: "业务处理",
      key: "business_process_status",
      width: 96,
      render: (_: unknown, r: ReceiptRow) => {
        const processed = (r.data.business_process_status || "未处理") === "已处理";
        return <Tag color={processed ? "green" : "orange"}>{processed ? "已处理" : "未处理"}</Tag>;
      },
    },
  ];

  const receivedColumns = [
    {
      title: "收文日",
      key: "document_date",
      width: 100,
      render: (_: unknown, r: ReceiptRow) => r.data.document_date || "—",
    },
    {
      title: "案号",
      key: "case_no",
      width: 145,
      render: (_: unknown, r: ReceiptRow) =>
        r.data.case_no ? (
          <Button type="link" onClick={() => onOpenCaseDetail(r.data.case_no!)}>
            {r.data.case_no}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "法院案号",
      key: "court_no",
      width: 180,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.court_no || "—",
    },
    {
      title: "原告",
      key: "plaintiff",
      width: 200,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.plaintiff || "—",
    },
    {
      title: "被告",
      key: "defendant",
      width: 220,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.defendant || "—",
    },
    {
      title: "文件名称",
      dataIndex: "title",
      width: 350,
      ellipsis: true,
      render: (v: string, r: ReceiptRow) => (
        <Space size={0}>
          <a onClick={() => onShowReceipt(r)}>{v}</a>
          {receiptAttachment(r) && (
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => onPreviewReceiptFile(r)}
            >
              查看
            </Button>
          )}
        </Space>
      ),
    },
    {
      title: "上传日期",
      key: "uploaded_at",
      width: 100,
      render: (_: unknown, r: ReceiptRow) => r.data.uploaded_at || "—",
    },
    {
      title: "开庭律师",
      key: "hearing_lawyer",
      width: 90,
      render: (_: unknown, r: ReceiptRow) =>
        personDisplayName(r.data.hearing_lawyer_display_name),
    },
    {
      title: "律师助理",
      key: "assistant",
      width: 90,
      render: (_: unknown, r: ReceiptRow) =>
        personDisplayName(r.data.assistant_display_name),
    },
    {
      title: "品牌管理人",
      key: "brand_manager",
      width: 100,
      render: (_: unknown, r: ReceiptRow) =>
        personDisplayName(r.data.brand_manager_display_name),
    },
  ];

  const title = isOfficial ? "官文收文" : tab === "my-receipts" ? "我的收文" : "公司收文";
  const columns = isOfficial ? officialColumns : receivedColumns;

  return (
    <Card className="panel receipt-original-panel" title={title}>
      <Form form={receiptForm} className="receipt-query-form" onFinish={onSearch}>
        {isOfficial ? (
          <div className="receipt-filter-grid official">
            <Form.Item label="案件编号" name="case_no">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="文件名称" name="file_name">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="导入状态" name="import_status">
              <Select
                allowClear
                placeholder="请选择"
                options={["未导入", "已导入"].map((value) => ({ value, label: value }))}
              />
            </Form.Item>
            <Form.Item label="业务处理状态" name="business_process_status">
              <Select
                allowClear
                placeholder="请选择"
                options={["未处理", "已处理"].map((value) => ({ value, label: value }))}
              />
            </Form.Item>
            <Form.Item label="上传日期" name="upload_range">
              <DatePicker.RangePicker />
            </Form.Item>
          </div>
        ) : (
          <div className="receipt-filter-grid">
            <Form.Item label="案件编号" name="case_no">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="法院案号" name="court_no">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="法院名称" name="court_name">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="收文日期" name="receipt_range">
              <DatePicker.RangePicker />
            </Form.Item>
            <Form.Item label="原告" name="plaintiff">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="被告" name="defendant">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="开庭律师" name="hearing_lawyer">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="上传日期" name="upload_range">
              <DatePicker.RangePicker />
            </Form.Item>
            <Form.Item label="客户管理人" name="case_manager">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="经办律师" name="handling_lawyer">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="律师助理" name="assistant">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="文件名称" name="document_name">
              <Input allowClear />
            </Form.Item>
          </div>
        )}
        <div className="receipt-query-actions">
          <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>
            查询
          </Button>
          {isOfficial && (
            <Button icon={<UploadOutlined />} onClick={() => onOpenUpload(undefined, "收文附件")}>
              上传
            </Button>
          )}
        </div>
      </Form>
      <Table
        rowKey="id"
        loading={loading}
        size="small"
        className="receipt-table"
        rowSelection={{
          selectedRowKeys: selectedReceiptKeys,
          onChange: onSelectionChange,
        }}
        columns={columns}
        dataSource={searchedReceipts}
        scroll={{ x: isOfficial ? 1450 : 1800 }}
        pagination={{
          pageSize: 15,
          showTotal: (total) => `共 ${total} 条记录`,
          showSizeChanger: false,
        }}
      />
      <div className="receipt-footer-actions">
        {isOfficial ? (
          <>
            <Popconfirm
              title="确定删除选中的收文记录？"
              description={
                selectedFormalReceipts.length
                  ? `将永久删除 ${selectedFormalReceipts.length} 条正式记录及其附件。`
                  : "请先选择需要删除的正式收文记录。"
              }
              onConfirm={onDeleteSelected}
            >
              <Button
                danger
                size="small"
                icon={<DeleteOutlined />}
                disabled={!selectedReceiptKeys.length}
              >
                删除
              </Button>
            </Popconfirm>
            <Button
              size="small"
              icon={<EditOutlined />}
              disabled={!selectedReceiptKeys.length}
              onClick={onOpenReceiptDateEditor}
            >
              修改收文日期
            </Button>
            <Button
              size="small"
              disabled={!selectedFormalReceipts.length}
              onClick={onOpenCaseLinker}
            >
              批量关联案件
            </Button>
            <Button
              size="small"
              disabled={!selectedFormalReceipts.length}
              onClick={() => onUpdateProcessStatus(true)}
            >
              标记已处理
            </Button>
            <Button
              size="small"
              disabled={!selectedFormalReceipts.length}
              onClick={() => onUpdateProcessStatus(false)}
            >
              标记未处理
            </Button>
            <Button
              size="small"
              icon={<DownloadOutlined />}
              disabled={!searchedReceipts.length}
              onClick={onExport}
            >
              {selectedFormalReceipts.length ? "导出选中" : "导出查询结果"}
            </Button>
          </>
        ) : (
          <>
            <Button
              size="small"
              icon={<EditOutlined />}
              disabled={!selectedReceiptKeys.length}
              onClick={onOpenReceiptDateEditor}
            >
              修改收文日期
            </Button>
            <Dropdown
              menu={{ items: receiptMoreActionItems, onClick: ({ key }) => onMoreAction(key) }}
            >
              <Button size="small" disabled={selectedReceiptKeys.length !== 1}>
                更多操作
              </Button>
            </Dropdown>
          </>
        )}
      </div>
    </Card>
  );
}


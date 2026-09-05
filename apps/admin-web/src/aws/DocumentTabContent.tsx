import {
  Alert,
  Button,
  DatePicker,
  Form,
  Input,
  Popconfirm,
  Progress,
  Select,
  Space,
  Table,
  Tag,
} from "antd";
import {
  CheckCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FolderOutlined,
  SearchOutlined,
  StopOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { FormInstance } from "antd";
import type { Key } from "react";
import dayjs from "dayjs";
import type {
  Attachment,
  HistoryEvent,
  LegacyHistoricalAttachment,
  RecordRow,
  Template,
} from "./types";
import {
  archiveCategories,
  fileSize,
  outgoingStatusOptions,
  personDisplayName,
} from "./constants";
import {
  legacyAttachmentQuarantineLabel,
  legacyAttachmentRecoveryLabel,
  legacyAttachmentSourceLabel,
} from "../legacyHistoricalAttachmentPresentation";

// ===== 收发文登记表 =====
interface DocumentListProps {
  documents: RecordRow[];
  attachments: Attachment[];
  loading: boolean;
  onOpenDetail: (row: RecordRow) => void;
  onOpenUpload: (target: RecordRow, category: string) => void;
  onOpenCustomerDetail: (customer: string) => void;
  onOpenCaseDetail: (caseNo: string) => void;
  onStartAction: (row: RecordRow, toStatus: string) => void;
}

function documentActionButton(
  r: RecordRow,
  onStartAction: (row: RecordRow, toStatus: string) => void,
) {
  if (r.status === "待登记") {
    return (
      <Button type="link" onClick={() => onStartAction(r, "待签收")}>
        完成登记
      </Button>
    );
  }
  if (r.status === "待签收") {
    return (
      <Button
        type="link"
        icon={<CheckCircleOutlined />}
        onClick={() => onStartAction(r, "已签收")}
      >
        {r.data.direction === "发文" ? "确认送达" : "确认签收"}
      </Button>
    );
  }
  if (r.status === "已签收") {
    return (
      <Button
        type="link"
        icon={<FolderOutlined />}
        onClick={() => onStartAction(r, "已归档")}
      >
        归档
      </Button>
    );
  }
  return null;
}

export function DocumentList({
  documents,
  attachments,
  loading,
  onOpenDetail,
  onOpenUpload,
  onOpenCustomerDetail,
  onOpenCaseDetail,
  onStartAction,
}: DocumentListProps) {
  const columns = [
    {
      title: "文号",
      dataIndex: "serial_no",
      width: 160,
      render: (v: string, r: RecordRow) => (
        <a onClick={() => onOpenDetail(r)}>{v}</a>
      ),
    },
    { title: "文件名称", dataIndex: "title", width: 240, ellipsis: true },
    {
      title: "收发类型",
      key: "direction",
      width: 90,
      render: (_: unknown, r: RecordRow) => (
        <Tag color={r.data.direction === "发文" ? "blue" : "green"}>
          {r.data.direction || "收文"}
        </Tag>
      ),
    },
    {
      title: "客户",
      dataIndex: "customer",
      width: 170,
      render: (value: string) =>
        value ? (
          <Button type="link" onClick={() => onOpenCustomerDetail(value)}>
            {value}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "关联案号",
      key: "case",
      width: 145,
      render: (_: unknown, r: RecordRow) =>
        r.data.case_no ? (
          <Button type="link" onClick={() => onOpenCaseDetail(r.data.case_no)}>
            {r.data.case_no}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "来文/送达单位",
      key: "sender",
      width: 160,
      render: (_: unknown, r: RecordRow) => r.data.sender || "—",
    },
    {
      title: "负责人",
      dataIndex: "owner_display_name",
      width: 90,
      render: personDisplayName,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (v: string) => (
        <Tag color={v === "已归档" ? "green" : v === "已签收" ? "blue" : "orange"}>
          {v}
        </Tag>
      ),
    },
    {
      title: "附件",
      key: "files",
      width: 65,
      render: (_: unknown, r: RecordRow) =>
        attachments.filter((a) => a.record_id === r.id).length,
    },
    {
      title: "操作",
      key: "actions",
      fixed: "right" as const,
      width: 260,
      render: (_: unknown, r: RecordRow) => (
        <Space size={0}>
          <Button type="link" icon={<EyeOutlined />} onClick={() => onOpenDetail(r)}>
            详情
          </Button>
          <Button
            type="link"
            icon={<UploadOutlined />}
            onClick={() =>
              onOpenUpload(r, r.data.direction === "发文" ? "发文附件" : "收文附件")
            }
          >
            附件
          </Button>
          {documentActionButton(r, onStartAction)}
        </Space>
      ),
    },
  ];

  return (
    <Table
      rowKey="id"
      loading={loading}
      size="small"
      columns={columns}
      dataSource={documents}
      scroll={{ x: 1700 }}
      pagination={{
        pageSize: 15,
        showTotal: (total) => `共 ${total} 条记录`,
        showSizeChanger: true,
      }}
    />
  );
}

// ===== 文件附件列表 =====
interface FileListProps {
  attachments: Attachment[];
  loading: boolean;
  onPreview: (row: Attachment) => void;
  onDownload: (row: Attachment) => void;
  onDelete: (id: number) => void;
  onOpenRecord: (attachment: Attachment) => void;
}

export function FileList({
  attachments,
  loading,
  onPreview,
  onDownload,
  onDelete,
  onOpenRecord,
}: FileListProps) {
  const columns = [
    { title: "文件名", dataIndex: "original_name", width: 260 },
    {
      title: "分类",
      dataIndex: "category",
      width: 110,
      render: (v: string) => (
        <Tag color={archiveCategories.includes(v) ? "green" : "blue"}>{v}</Tag>
      ),
    },
    {
      title: "关联编号",
      dataIndex: "record_no",
      width: 160,
      render: (v: string, r: Attachment) =>
        r.record_id ? (
          <Button type="link" onClick={() => onOpenRecord(r)}>
            {v || "查看关联业务"}
          </Button>
        ) : (
          "公共文件"
        ),
    },
    {
      title: "关联业务",
      dataIndex: "record_title",
      width: 220,
      ellipsis: true,
      render: (v: string, r: Attachment) =>
        r.record_id ? (
          <Button type="link" onClick={() => onOpenRecord(r)}>
            {v || r.record_no || "查看关联业务"}
          </Button>
        ) : (
          "—"
        ),
    },
    { title: "大小", dataIndex: "size", width: 90, render: fileSize },
    {
      title: "上传人",
      dataIndex: "uploader_display_name",
      width: 90,
      render: personDisplayName,
    },
    {
      title: "上传时间",
      dataIndex: "created_at",
      width: 165,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    { title: "备注", dataIndex: "remark", width: 160 },
    {
      title: "操作",
      key: "actions",
      fixed: "right" as const,
      width: 130,
      render: (_: unknown, r: Attachment) => (
        <Space>
          <Button type="link" icon={<EyeOutlined />} onClick={() => onPreview(r)}>
            查看
          </Button>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => onDownload(r)}
          >
            下载
          </Button>
          <Popconfirm title="确定删除此附件？" onConfirm={() => onDelete(r.id)}>
            <Button danger type="link" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Table
      rowKey="id"
      loading={loading}
      size="small"
      columns={columns}
      dataSource={attachments}
      pagination={{
        pageSize: 15,
        showTotal: (total) => `共 ${total} 条记录`,
        showSizeChanger: true,
      }}
      scroll={{ x: 1450 }}
    />
  );
}

// ===== 模板列表 =====
interface TemplateListProps {
  templates: Template[];
  loading: boolean;
  onViewDetail: (row: Template) => void;
  onEdit: (row: Template) => void;
  onToggle: (row: Template) => void;
  onDelete: (id: number) => void;
}

export function TemplateList({
  templates,
  loading,
  onViewDetail,
  onEdit,
  onToggle,
  onDelete,
}: TemplateListProps) {
  const columns = [
    {
      title: "模板名称",
      dataIndex: "name",
      width: 220,
      render: (value: string, row: Template) => (
        <Button type="link" onClick={() => onViewDetail(row)}>
          {value}
        </Button>
      ),
    },
    {
      title: "分类",
      dataIndex: "category",
      width: 110,
      render: (v: string) => <Tag color="green">{v}</Tag>,
    },
    { title: "版本", dataIndex: "version", width: 90 },
    {
      title: "模板字段",
      dataIndex: "fields",
      width: 360,
      render: (v: string[]) => (
        <Space wrap>
          {v.map((x) => (
            <Tag key={x}>{x}</Tag>
          ))}
        </Space>
      ),
    },
    { title: "说明", dataIndex: "description" },
    {
      title: "状态",
      dataIndex: "is_active",
      width: 80,
      render: (v: boolean) => (
        <Tag color={v ? "green" : "default"}>{v ? "启用" : "停用"}</Tag>
      ),
    },
    {
      title: "操作",
      key: "actions",
      fixed: "right" as const,
      width: 190,
      render: (_: unknown, r: Template) => (
        <Space size={0}>
          <Button type="link" icon={<EditOutlined />} onClick={() => onEdit(r)}>
            编辑
          </Button>
          <Popconfirm
            title={`确定${r.is_active ? "停用" : "启用"}此模板？`}
            onConfirm={() => onToggle(r)}
          >
            <Button type="link" icon={<StopOutlined />}>
              {r.is_active ? "停用" : "启用"}
            </Button>
          </Popconfirm>
          <Popconfirm title="确定删除此模板？" onConfirm={() => onDelete(r.id)}>
            <Button danger type="link" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Table
      rowKey="id"
      loading={loading}
      size="small"
      columns={columns}
      dataSource={templates}
      pagination={{
        pageSize: 15,
        showTotal: (total) => `共 ${total} 条记录`,
        showSizeChanger: true,
      }}
      scroll={{ x: 1200 }}
    />
  );
}

// ===== 归档材料列表 =====
interface ArchiveListProps {
  archiveRows: any[];
  loading: boolean;
  onOpenCaseDetail: (caseNo: string) => void;
  onOpenCustomerDetail: (customer: string) => void;
  onOpenUpload: (target: RecordRow, category: string) => void;
}

export function ArchiveList({
  archiveRows,
  loading,
  onOpenCaseDetail,
  onOpenCustomerDetail,
  onOpenUpload,
}: ArchiveListProps) {
  const columns = [
    {
      title: "案号",
      dataIndex: "serial_no",
      width: 155,
      render: (value: string, r: RecordRow) =>
        value ? (
          <Button type="link" onClick={() => onOpenCaseDetail(value)}>
            {value}
          </Button>
        ) : (
          "—"
        ),
    },
    { title: "案件名称", dataIndex: "title", width: 250 },
    {
      title: "客户",
      dataIndex: "customer",
      width: 190,
      render: (value: string) =>
        value ? (
          <Button type="link" onClick={() => onOpenCustomerDetail(value)}>
            {value}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "归档材料",
      key: "materials",
      width: 400,
      render: (_: unknown, r: any) => (
        <Space wrap>
          {archiveCategories.map((c) => (
            <Tag key={c} color={r.categories.has(c) ? "green" : "default"}>
              {r.categories.has(c) ? "✓ " : "○ "}
              {c}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "完整度",
      key: "progress",
      width: 170,
      render: (_: unknown, r: any) => (
        <Progress
          percent={r.percent}
          size="small"
          status={r.percent === 100 ? "success" : "active"}
        />
      ),
    },
    {
      title: "操作",
      key: "action",
      width: 95,
      render: (_: unknown, r: RecordRow) => (
        <Button
          type="link"
          icon={<UploadOutlined />}
          onClick={() => onOpenUpload(r, "委托材料")}
        >
          上传材料
        </Button>
      ),
    },
  ];

  return (
    <Table
      rowKey="id"
      loading={loading}
      size="small"
      columns={columns}
      dataSource={archiveRows}
      pagination={{
        pageSize: 15,
        showTotal: (total) => `共 ${total} 条记录`,
        showSizeChanger: true,
      }}
      scroll={{ x: 1300 }}
    />
  );
}

// ===== 历史附件元数据列表 =====
interface LegacyHistoryListProps {
  attachments: LegacyHistoricalAttachment[];
  loading: boolean;
  error: string | null;
}

export function LegacyHistoryList({
  attachments,
  loading,
  error,
}: LegacyHistoryListProps) {
  return (
    <>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message="仅元数据：旧系统源文件不可恢复"
        description="合同和公文历史附件只保留可审计元数据。旧路径不用于下载或预览，实时附件也不会被写入。"
      />
      {error ? (
        <Alert type="error" showIcon message={error} />
      ) : (
        <Table<LegacyHistoricalAttachment>
          rowKey="id"
          loading={loading}
          size="small"
          dataSource={attachments}
          locale={{ emptyText: "暂无已导入的历史附件元数据" }}
          columns={[
            {
              title: "来源",
              dataIndex: "legacy_entity_type",
              width: 190,
              render: (value: string) => legacyAttachmentSourceLabel(value),
            },
            { title: "历史文件ID", dataIndex: "legacy_file_id", width: 130 },
            { title: "文件名称", dataIndex: "file_name", width: 300, ellipsis: true },
            { title: "父编号", dataIndex: "legacy_parent_no", width: 150 },
            {
              title: "声明大小",
              dataIndex: "legacy_declared_size_bytes",
              width: 110,
              render: (value: number | null) => (value == null ? "—" : `${value} B`),
            },
            {
              title: "恢复状态",
              dataIndex: "recovery_status",
              width: 220,
              render: (value: string) => (
                <Tag color="orange">{legacyAttachmentRecoveryLabel(value)}</Tag>
              ),
            },
            {
              title: "隔离原因",
              dataIndex: "quarantine_reasons",
              width: 210,
              render: (values: string[]) => legacyAttachmentQuarantineLabel(values),
            },
            {
              title: "物理文件",
              width: 150,
              render: () => <Tag color="default">源文件不可恢复</Tag>,
            },
          ]}
          pagination={{ pageSize: 30, showSizeChanger: true }}
          scroll={{ x: 1250 }}
        />
      )}
    </>
  );
}

// ===== 正式发文搜索表单 =====
interface OutgoingSearchFormProps {
  form: FormInstance;
  onSearch: () => void;
  onReset: () => void;
}

export function OutgoingSearchForm({
  form,
  onSearch,
  onReset,
}: OutgoingSearchFormProps) {
  return (
    <Form
      form={form}
      layout="inline"
      onFinish={onSearch}
      style={{ padding: "0 0 12px", rowGap: 8 }}
    >
      <Form.Item label="申请编号" name="official_no">
        <Input allowClear placeholder="正式发文编号" style={{ width: 176 }} />
      </Form.Item>
      <Form.Item label="申请人" name="owner">
        <Input allowClear placeholder="申请人" style={{ width: 120 }} />
      </Form.Item>
      <Form.Item label="申请日期" name="application_dates">
        <DatePicker.RangePicker allowClear style={{ width: 230 }} />
      </Form.Item>
      <Form.Item label="案件编号" name="case_no">
        <Input allowClear placeholder="案件编号" style={{ width: 160 }} />
      </Form.Item>
      <Form.Item label="合同编号" name="contract_no">
        <Input allowClear placeholder="合同编号" style={{ width: 160 }} />
      </Form.Item>
      <Form.Item label="客户名称" name="customer">
        <Input allowClear placeholder="客户名称" style={{ width: 150 }} />
      </Form.Item>
      <Form.Item label="用印状态" name="status_value">
        <Select
          allowClear
          placeholder="全部"
          style={{ width: 120 }}
          options={outgoingStatusOptions.map((value) => ({ value, label: value }))}
        />
      </Form.Item>
      <Form.Item label="印章类型" name="seal_type">
        <Input allowClear placeholder="印章类型" style={{ width: 140 }} />
      </Form.Item>
      <Form.Item label="文件名称" name="file_name">
        <Input allowClear placeholder="文件名称" style={{ width: 160 }} />
      </Form.Item>
      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>
            查询
          </Button>
          <Button onClick={() => onReset()}>重置</Button>
        </Space>
      </Form.Item>
    </Form>
  );
}

// ===== 正式发文列表 =====
interface OutgoingListProps {
  outgoingDocuments: RecordRow[];
  loading: boolean;
  selectedKeys: Key[];
  onSelectionChange: (keys: Key[]) => void;
  onOpenDetail: (row: RecordRow) => void;
  onOpenEditor: (row: RecordRow) => void;
  onSubmit: (row: RecordRow) => void;
  onOpenSource: (row: any) => void;
  onOpenCustomerDetail: (customer: string) => void;
  onApprove: (row: RecordRow) => void;
  onReject: (row: RecordRow) => void;
  onRollback: (row: RecordRow) => void;
}

export function OutgoingList({
  outgoingDocuments,
  loading,
  selectedKeys,
  onSelectionChange,
  onOpenDetail,
  onOpenEditor,
  onSubmit,
  onOpenSource,
  onOpenCustomerDetail,
  onApprove,
  onReject,
  onRollback,
}: OutgoingListProps) {
  const columns: ColumnsType<RecordRow> = [
    {
      title: "正式发文编号",
      dataIndex: "official_no",
      width: 190,
      render: (_: unknown, row: RecordRow) => (
        <Button type="link" className="case-cell-link" onClick={() => onOpenDetail(row)}>
          {(row as any).official_no || row.serial_no}
        </Button>
      ),
    },
    { title: "文书名称", dataIndex: "title", width: 240, ellipsis: true },
    {
      title: "来源",
      width: 180,
      render: (_, row: any) =>
        row.source_serial_no ? (
          <Button
            type="link"
            className="case-cell-link"
            onClick={() => onOpenSource(row)}
          >
            {`${row.source_type === "contract" ? "合同" : "案件"}：${row.source_serial_no}`}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "客户",
      dataIndex: "customer",
      width: 180,
      ellipsis: true,
      render: (value: string) =>
        value ? (
          <Button
            type="link"
            className="case-cell-link"
            onClick={() => onOpenCustomerDetail(value)}
          >
            {value}
          </Button>
        ) : (
          "—"
        ),
    },
    { title: "印章类型", dataIndex: "seal_type", width: 130, render: (value: string) => value || "—" },
    {
      title: "用印类型",
      key: "official_document_type",
      width: 90,
      render: (_, row: any) =>
        row.source_type === "case" ? "案件" : row.source_type === "contract" ? "合同" : "—",
    },
    {
      title: "文件数",
      key: "file_count",
      width: 80,
      render: (_: unknown, row: RecordRow) => (
        <Button type="link" className="case-cell-link" onClick={() => onOpenDetail(row)}>
          {(row as any).attachments?.length || 0}
        </Button>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 110,
      render: (value: string) => (
        <Tag
          color={
            value === "已通过"
              ? "green"
              : value === "已拒绝"
                ? "red"
                : value === "待审批"
                  ? "orange"
                  : "default"
          }
        >
          {value}
        </Tag>
      ),
    },
    {
      title: "申请人",
      dataIndex: "owner_display_name",
      width: 120,
      render: personDisplayName,
    },
    {
      title: "申请时间",
      dataIndex: "created_at",
      width: 175,
      sorter: (a: any, b: any) => String(a.created_at || "").localeCompare(String(b.created_at || "")),
      render: (value: string) =>
        value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—",
    },
    {
      title: "审核人",
      dataIndex: "auditor_display_name",
      width: 120,
      render: personDisplayName,
    },
    {
      title: "审核时间",
      dataIndex: "audit_time",
      width: 175,
      sorter: (a: any, b: any) => String(a.audit_time || "").localeCompare(String(b.audit_time || "")),
      render: (value: string) =>
        value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—",
    },
    {
      title: "审核意见",
      dataIndex: "audit_remark",
      width: 220,
      ellipsis: true,
      render: (value: string) => value || "—",
    },
    {
      title: "操作",
      fixed: "right",
      width: 290,
      render: (_, row: RecordRow) => (
        <Space size={2}>
          <Button type="link" size="small" onClick={() => onOpenDetail(row)}>
            详情
          </Button>
          {["草稿", "已拒绝", "已撤回"].includes(row.status) && (
            <Button type="link" size="small" onClick={() => onOpenEditor(row)}>
              编辑
            </Button>
          )}
          {["草稿", "已拒绝", "已撤回"].includes(row.status) && (
            <Button type="link" size="small" onClick={() => onSubmit(row)}>
              提交
            </Button>
          )}
          {row.status === "待审批" && (
            <>
              <Button type="link" size="small" onClick={() => onApprove(row)}>
                通过
              </Button>
              <Button danger type="link" size="small" onClick={() => onReject(row)}>
                拒绝
              </Button>
            </>
          )}
          {["待审批", "已拒绝"].includes(row.status) && (
            <Popconfirm title="确认撤回正式发文？" onConfirm={() => onRollback(row)}>
              <Button type="link" size="small">撤回</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Table
      rowKey="id"
      loading={loading}
      size="small"
      rowSelection={{
        selectedRowKeys: selectedKeys,
        onChange: onSelectionChange,
        getCheckboxProps: (row: RecordRow) => ({
          disabled: !["已通过", "已盖章"].includes(row.status),
        }),
      }}
      locale={{ emptyText: "暂无正式发文；请从合同或案件发起" }}
      columns={columns}
      dataSource={outgoingDocuments}
      pagination={{
        pageSize: 15,
        showTotal: (total) => `共 ${total} 条记录`,
        showSizeChanger: true,
      }}
      scroll={{ x: 1920 }}
    />
  );
}

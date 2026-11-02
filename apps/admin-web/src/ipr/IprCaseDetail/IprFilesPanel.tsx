import { roleActionAllowed } from "../../roleActions";
import { Alert,Button,DatePicker,Form,Input,Modal,Radio,Select,Space,Tag } from "antd";
import Table from "../../components/ResizableTable";
import { AttachmentFileInput } from "../../components/common/AttachmentContent";
import type { Attachment,IprDetailPageState,IprFileType,IprRecord } from "../types";
import { IprRowContextMenu } from "./IprRowContextMenu";

const IPR_FILE_TYPE_GROUPS = ["官文", "非官文", "转文"];

interface IprFilesPanelProps {
  detail: IprRecord;
  iprSectionErrors: { files: string };
  attachments: Attachment[];
  filesPageState: IprDetailPageState;
  iprFileTypes: IprFileType[];
  iprFileOpen: boolean;
  iprFileForm: any;
  iprUploadFile: File | null;
  selectedIprFileIds: number[];
  onRefresh: () => void;
  onPreviewAttachment: (item: Attachment) => void;
  onDownloadAttachment: (item: Attachment) => void;
  onOpenUpload: () => void;
  onCloseUpload: () => void;
  onUploadFile: () => void;
  onUploadFileChange: (file: File | null) => void;
  onMarkTransmitted: (row: Attachment) => void;
  onMarkSelectedTransmitted: () => void;
  onDeleteFile: (row: Attachment) => Promise<void>;
  onGenerateApplication: (row: Attachment) => void;
  onSelectedFileIdsChange: (ids: number[]) => void;
  confirmIprDeletion: (kind: string, label: string, operation: () => Promise<void>) => void;
  onPageChange: (page: number, pageSize: number) => void;
}

export function IprFilesPanel({
  detail,
  iprSectionErrors,
  attachments,
  filesPageState,
  iprFileTypes,
  iprFileOpen,
  iprFileForm,
  iprUploadFile,
  selectedIprFileIds,
  onRefresh,
  onPreviewAttachment,
  onDownloadAttachment,
  onOpenUpload,
  onCloseUpload,
  onUploadFile,
  onUploadFileChange,
  onMarkTransmitted,
  onMarkSelectedTransmitted,
  onDeleteFile,
  onGenerateApplication,
  onSelectedFileIdsChange,
  confirmIprDeletion,
  onPageChange,
}: IprFilesPanelProps) {
  const filesPagination = {
    current: filesPageState.page,
    pageSize: filesPageState.pageSize,
    total: filesPageState.total,
    showSizeChanger: true,
    pageSizeOptions: ["15", "20", "50"],
    onChange: onPageChange,
  };

  // 迁移案件的状态是老系统阶段名，和老系统一样都能维护文档；新系统流程里的草稿、待审批、已驳回、已结案除外（BUG20261028020）。
  const active = !!detail.status && !["草稿", "待审批", "已驳回", "已结案"].includes(detail.status);
  const canManage = active && roleActionAllowed("ipr.case.file.manage");
  // 右键菜单按原系统：上传、查看、下载、标记已转、删除、生成申请文件、刷新。
  const menuItems = (row: Attachment | null) => [
    { key: "upload", label: "上传", disabled: !canManage, onClick: onOpenUpload },
    { key: "view", label: "查看", disabled: !row, onClick: () => row && onPreviewAttachment(row) },
    { key: "download", label: "下载", disabled: !row, onClick: () => row && onDownloadAttachment(row) },
    {
      key: "transmitted", label: "标记已转",
      disabled: !row || !canManage || !row.requires_transmission || !!row.is_transmitted,
      onClick: () => row && onMarkTransmitted(row),
    },
    {
      key: "delete", label: "删除", disabled: !row || !active || !roleActionAllowed("ipr.case.file.delete"),
      onClick: () => row && confirmIprDeletion("file", row.original_name, () => onDeleteFile(row)),
    },
    {
      key: "generate", label: "生成申请文件", disabled: !row || detail.status !== "在办" || !roleActionAllowed("ipr.case.document.generate"),
      onClick: () => row && onGenerateApplication(row),
    },
    { key: "refresh", label: "刷新", onClick: onRefresh },
  ];

  return (
    <>
      {/* 文档信息按原系统一张表（BUG20261028001）：序号、上传人、文档类型、文件名称、文档日期、待转文；在办案件另有上传和标记。 */}
      {iprSectionErrors.files ? (
        <Alert type="error" showIcon message={iprSectionErrors.files} style={{ marginBottom: 12 }} />
      ) : null}
      {active ? (
        <Space style={{ marginBottom: 8 }}>
          {roleActionAllowed("ipr.case.file.manage") && <Button size="small" type="primary" onClick={onOpenUpload}>上传文档</Button>}
          {roleActionAllowed("ipr.case.file.manage") && <Button size="small" disabled={!selectedIprFileIds.length} onClick={onMarkSelectedTransmitted}>批量标记已转</Button>}
          <Button size="small" onClick={onRefresh}>刷新</Button>
        </Space>
      ) : null}
      <IprRowContextMenu rows={attachments} rowKey={(row) => row.id} items={menuItems}>
      <Table
        rowKey="id"
        size="small"
        pagination={filesPagination}
        dataSource={attachments}
        rowSelection={active ? {
          selectedRowKeys: selectedIprFileIds,
          onChange: (keys) => onSelectedFileIdsChange(keys.map(Number)),
          getCheckboxProps: (row: Attachment) => ({
            disabled: !row.requires_transmission || !!row.is_transmitted,
          }),
        } : undefined}
        scroll={{ x: 760 }}
        columns={[
          {
            title: "序号",
            width: 60,
            render: (_, _row, index) => (filesPageState.page - 1) * filesPageState.pageSize + index + 1,
          },
          {
            title: "上传人",
            dataIndex: "uploader_display_name",
            width: 95,
            render: (value) => String(value || "").trim() || "—",
          },
          { title: "文档类型", dataIndex: "category", width: 220, ellipsis: true },
          {
            title: "文件名称",
            dataIndex: "original_name",
            ellipsis: true,
            render: (_, row: Attachment) => (
              <Space size={0}>
                <Button type="link" size="small" onClick={() => onPreviewAttachment(row)}>{row.original_name}</Button>
                <Button type="link" size="small" onClick={() => onDownloadAttachment(row)}>下载</Button>
              </Space>
            ),
          },
          { title: "文档日期", dataIndex: "document_date", width: 110, render: (value) => value || "—" },
          {
            title: "待转文",
            width: 80,
            render: (_, row: Attachment) =>
              row.requires_transmission ? (row.is_transmitted ? <Tag color="green">已转</Tag> : <Tag color="gold">是</Tag>) : "否",
          },
          ...(active ? [{
            title: "操作",
            fixed: "right" as const,
            width: 150,
            render: (_: unknown, row: Attachment) => (
              <Space size={0}>
                {row.requires_transmission && !row.is_transmitted && roleActionAllowed("ipr.case.file.manage") && (
                  <Button type="link" onClick={() => onMarkTransmitted(row)}>标记已转</Button>
                )}
                {roleActionAllowed("ipr.case.file.delete") && <Button type="link" danger onClick={() => confirmIprDeletion("file", row.original_name, () => onDeleteFile(row))}>删除</Button>}
              </Space>
            ),
          }] : []),
        ]}
      />
      </IprRowContextMenu>

      <Modal
        open={iprFileOpen}
        title="上传知识产权案件文档"
        onCancel={onCloseUpload}
        onOk={onUploadFile}
        okText="上传"
      >
        <Form form={iprFileForm} layout="vertical">
          {/* 和老系统右键上传一致（BUG20261102005）：先选官文 / 非官文 / 转文，再从本案件类型那份名单里选，显示“编号+名称”。 */}
          <Form.Item name="file_type_group" label="文档类型" style={{ marginBottom: 8 }}>
            <Radio.Group
              optionType="button"
              size="small"
              options={IPR_FILE_TYPE_GROUPS}
              onChange={() => iprFileForm.setFieldValue("file_type_code", undefined)}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev: any, next: any) => prev.file_type_group !== next.file_type_group}>
            {({ getFieldValue }: any) => (
              <Form.Item
                name="file_type_code"
                rules={[{ required: true, message: "请选择文档类型" }]}
              >
                <Select
                  showSearch
                  optionFilterProp="label"
                  placeholder="从下列文档类型中选择，可输入编号或名称搜索"
                  options={iprFileTypes
                    .filter((item) => (item.group || "非官文") === getFieldValue("file_type_group"))
                    .map((item) => ({
                      value: item.code,
                      label: `${/^\d+$/.test(item.code) ? item.code : ""}${item.name}`,
                    }))}
                />
              </Form.Item>
            )}
          </Form.Item>
          <Form.Item
            name="document_date"
            label="文档日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <div style={{ marginBottom: 16, color: "var(--oa-text-2)" }}>
            待转文属性由管理员配置的文件类型决定，上传人不能自行绕过。
          </div>
          <Form.Item label="案件文档" required>
            <AttachmentFileInput
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar"
              onFileChange={onUploadFileChange} />
            {iprUploadFile && <div>{iprUploadFile.name}</div>}
          </Form.Item>
          <Form.Item name="remark" label="说明">
            <Input.TextArea rows={2} maxLength={1000} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

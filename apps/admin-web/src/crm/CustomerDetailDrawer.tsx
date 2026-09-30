import {
  Alert,
  Button,
  Card,
  Checkbox,
  Drawer,
  Form,
  Input,
  Popconfirm,
  Select,
  Space,
  Tabs,
  Tag,
  Upload,
} from "antd";
import Table from "../components/ResizableTable";
import { ReloadOutlined, UploadOutlined } from "@ant-design/icons";
import { displayChinesePersonName, displayChinesePersonNames } from "../contractPeoplePresentation.mjs";
import { CUSTOMER_CONTACT_FORM_DEFAULTS, CUSTOMER_DOCUMENT_FORM_DEFAULTS, canDeleteCustomerAttachment, getCustomerAttachmentDate } from "../customerUiBatchI15.mjs";
import type { FormInstance } from "antd";
import type {
  Attachment,
  Contact,
  Customer,
  CustomerEvent,
  CustomerNotice,
  DirectoryUser,
  Note,
} from "./types";

interface CustomerDetailDrawerProps {
  open: boolean;
  customer: Customer | null;
  detailTab: string;
  detailLoading: boolean;
  historyError: string;
  attachmentError: string;
  customerEventError: string;
  sharedObjectsError: string;
  contactPage: number;
  contactPageSize: number;
  contactTotal: number;
  customerEvents: CustomerNotice[];
  events: CustomerEvent[];
  attachments: Attachment[];
  sharedObjects: string[];
  canManage: boolean;
  directory: DirectoryUser[];
  contactForm: FormInstance;
  noteForm: FormInstance;
  customerEventForm: FormInstance;
  documentForm: FormInstance;
  documentFileRef: React.RefObject<HTMLInputElement | null>;
  documentFile: File | null;
  onClose: () => void;
  onTabChange: (key: string) => void;
  onRefreshContacts: () => void;
  onContactPageChange: (page: number, pageSize: number) => void;
  onAddContact: () => void;
  onViewContact: (contact: Contact) => void;
  onEditContact: (contact: Contact) => void;
  onDeleteContact: (id: string) => void;
  onSetContactPrimary: (contact: Contact) => void;
  onSetContactActive: (contact: Contact) => void;
  onSetContactInactive: (contact: Contact) => void;
  onUploadContactPhoto: (contact: Contact, option: any) => void;
  onViewContactPhoto: (contact: Contact) => void;
  onAddNote: () => void;
  onDeleteNote: (id: string) => void;
  onViewDocument: (file: Attachment) => void;
  onDownloadDocument: (file: Attachment) => void;
  onDeleteDocument: (id: number) => void;
  onUploadDocument: () => void;
  onDocumentFileChange: (file: File | null) => void;
  onOpenContracts: () => void;
  onNewContract: () => void;
  onCreateCustomerEvent: () => void;
}

export function CustomerDetailDrawer({
  open,
  customer,
  detailTab,
  detailLoading,
  historyError,
  attachmentError,
  customerEventError,
  sharedObjectsError,
  contactPage,
  contactPageSize,
  contactTotal,
  customerEvents,
  events,
  attachments,
  sharedObjects,
  canManage,
  directory,
  contactForm,
  noteForm,
  customerEventForm,
  documentForm,
  documentFileRef,
  documentFile,
  onClose,
  onTabChange,
  onRefreshContacts,
  onContactPageChange,
  onAddContact,
  onViewContact,
  onEditContact,
  onDeleteContact,
  onSetContactPrimary,
  onSetContactActive,
  onSetContactInactive,
  onUploadContactPhoto,
  onViewContactPhoto,
  onAddNote,
  onDeleteNote,
  onViewDocument,
  onDownloadDocument,
  onDeleteDocument,
  onUploadDocument,
  onDocumentFileChange,
  onOpenContracts,
  onNewContract,
  onCreateCustomerEvent,
}: CustomerDetailDrawerProps) {
  const userLabels = (values: unknown) => displayChinesePersonNames(values, directory);
  const userLabel = (value: string) => displayChinesePersonName(value, directory);

  const contactPhotoActions = (contact: Contact) => canManage ? (
    <Space size={0}>
      <Upload accept=".jpg,.jpeg,.png,.gif,.webp" showUploadList={false} customRequest={option => void onUploadContactPhoto(contact, option)}>
        <Button type="link">{contact.photo_attachment_id ? "替换照片" : "上传照片"}</Button>
      </Upload>
      {contact.photo_attachment_id && <Button type="link" onClick={() => void onViewContactPhoto(contact)}>查看照片</Button>}
    </Space>
  ) : (
    contact.photo_attachment_id ? <Button type="link" onClick={() => void onViewContactPhoto(contact)}>查看照片</Button> : null
  );

  return (
    <Drawer
      size={720}
      loading={detailLoading}
      destroyOnHidden
      open={open}
      title={`客户详情：${customer?.title || ""}`}
      onClose={onClose}
    >
      <Tabs
        activeKey={detailTab}
        onChange={onTabChange}
        items={[
          {
            key: "contacts",
            label: `联系人（${customer?.data.contacts?.length || 0}）`,
            children: (
              <>
                <Space style={{ marginBottom: 8 }}>
                  <Button size="small" icon={<ReloadOutlined />} onClick={onRefreshContacts}>刷新</Button>
                </Space>
                <Table
                  className="customer-contact-drawer-table"
                  rowKey="id"
                  size="small"
                  tableLayout="fixed"
                  pagination={{
                    current: contactPage,
                    pageSize: contactPageSize,
                    total: contactTotal,
                    showSizeChanger: true,
                    pageSizeOptions: [10, 15, 20, 50, 100, 200],
                    showQuickJumper: { goButton: <Button size="small">GO</Button> },
                    onChange: onContactPageChange,
                    showTotal: (count) => `共有${count}条`,
                  }}
                  dataSource={customer?.data.contacts || []}
                  scroll={{ x: 1170 }}
                  columns={[
                    {
                      title: "姓名",
                      dataIndex: "name",
                      render: (v: string, r: Contact) => (
                        <>
                          {v}
                          {r.is_primary && <Tag color="green">主要</Tag>}
                        </>
                      ),
                    },
                    { title: "职务", dataIndex: "position" },
                    { title: "项目角色", dataIndex: "project_role" },
                    { title: "电话", dataIndex: "phone" },
                    { title: "办公电话", dataIndex: "office_phone" },
                    { title: "IM", dataIndex: "im_account" },
                    { title: "邮箱", dataIndex: "email" },
                    { title: "联系状态", dataIndex: "contact_status" },
                    { title: "有效", dataIndex: "is_valid", render: (value: boolean) => value !== false ? "是" : "否" },
                    { title: "照片", width: 150, render: (_: unknown, r: Contact) => contactPhotoActions(r) },
                    {
                      title: "操作",
                      render: (_: unknown, r: Contact) => canManage ? (
                        <Space size={0}>
                          <Button type="link" onClick={() => onViewContact(r)}>查看</Button>
                          <Button type="link" onClick={() => onEditContact(r)}>编辑</Button>
                          {!r.is_primary && <Button type="link" onClick={() => void onSetContactPrimary(r)}>设为主要</Button>}
                          {r.is_valid === false && <Button type="link" onClick={() => void onSetContactActive(r)}>设为有效</Button>}
                          {r.is_valid !== false && <Button type="link" onClick={() => void onSetContactInactive(r)}>设为无效</Button>}
                          <Popconfirm title="删除联系人？" onConfirm={() => onDeleteContact(r.id)}>
                            <Button type="link" danger>删除</Button>
                          </Popconfirm>
                        </Space>
                      ) : null,
                    },
                  ]}
                />
                <Card
                  size="small"
                  title="新增联系人"
                  style={{ marginTop: 16 }}
                >
                  <Form form={contactForm} layout="vertical" initialValues={CUSTOMER_CONTACT_FORM_DEFAULTS}>
                    <Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item>
                    <div className="form-grid">
                      <Form.Item label="姓名" name="name" rules={[{ required: true }]}><Input /></Form.Item>
                      <Form.Item label="职务" name="position"><Input /></Form.Item>
                      <Form.Item label="项目角色" name="project_role"><Input /></Form.Item>
                      <Form.Item label="电话" name="phone"><Input /></Form.Item>
                      <Form.Item label="办公电话" name="office_phone"><Input /></Form.Item>
                      <Form.Item label="IM" name="im_account"><Input /></Form.Item>
                      <Form.Item label="邮箱" name="email"><Input /></Form.Item>
                      <Form.Item label="客户服务账号" name="portal_account"><Input placeholder="可选；保存后同步到员工管理" /></Form.Item>
                      <Form.Item label="客户服务密码" name="portal_password" rules={[{ min: 8, message: "密码至少 8 位" }]}><Input.Password placeholder="填写后可直接登录客户服务端" /></Form.Item>
                      <Form.Item label="联系状态" name="contact_status" initialValue="正常联系"><Select options={["正常联系", "暂缓联系", "停止联系"].map(value => ({ value, label: value }))} /></Form.Item>
                    </div>
                    <Form.Item name="is_valid" valuePropName="checked" initialValue><Checkbox>有效联系人</Checkbox></Form.Item>
                    <Form.Item name="is_primary" valuePropName="checked"><Checkbox>设为主要联系人</Checkbox></Form.Item>
                    <Button type="primary" onClick={onAddContact}>添加联系人</Button>
                  </Form>
                </Card>
              </>
            ),
          },
          {
            key: "contracts",
            label: `合同（${customer?.data.contract_count ?? 0}）`,
            children: customer ? (
              <Space>
                <Button type="primary" onClick={onOpenContracts}>查看合同</Button>
                {canManage && <Button onClick={onNewContract}>新增合同</Button>}
              </Space>
            ) : null,
          },
          {
            key: "notes",
            label: `跟进记录（${customer?.data.notes?.length || 0}）`,
            children: (
              <>
                <Table
                  rowKey="id"
                  size="small"
                  pagination={false}
                  dataSource={customer?.data.notes || []}
                  scroll={{ x: 720 }}
                  columns={[
                    {
                      title: "类型",
                      dataIndex: "type",
                      width: 95,
                      render: (v: string) => <Tag color="blue">{v}</Tag>,
                    },
                    { title: "跟进内容", dataIndex: "content" },
                    { title: "记录人", dataIndex: "operator", width: 90, render: (value: string) => userLabel(value) },
                    { title: "时间", dataIndex: "created_at", width: 165 },
                    {
                      title: "操作",
                      width: 70,
                      render: (_: unknown, r: Note) => (
                        <Popconfirm title="删除这条记录？" onConfirm={() => onDeleteNote(r.id)}>
                          <Button danger type="link">删除</Button>
                        </Popconfirm>
                      ),
                    },
                  ]}
                />
                <Card size="small" title="新增跟进记录" style={{ marginTop: 16 }}>
                  <Form form={noteForm} layout="vertical" initialValues={{ note_type: "跟进记录" }}>
                    <Form.Item label="记录类型" name="note_type">
                      <Select options={["跟进记录", "会议纪要", "电话沟通", "风险提示", "客户备注"].map((v) => ({ value: v, label: v }))} />
                    </Form.Item>
                    <Form.Item label="内容" name="content" rules={[{ required: true }]}>
                      <Input.TextArea rows={4} />
                    </Form.Item>
                    <Button type="primary" onClick={onAddNote}>保存跟进记录</Button>
                  </Form>
                </Card>
              </>
            ),
          },
          {
            key: "customer-events",
            label: `客户注意事项（${customerEvents.length}）`,
            children: (
              <>
                {customerEventError && <Alert type="warning" showIcon message={customerEventError} style={{ marginBottom: 8 }} />}
                <Table rowKey="id" size="small" pagination={false} dataSource={customerEvents} locale={{ emptyText: "暂无客户注意事项" }} columns={[
                  { title: "事项", dataIndex: "action", width: 150 },
                  { title: "内容", dataIndex: "comment" },
                  { title: "操作人", dataIndex: "operator", width: 100, render: (value: string) => userLabel(value) },
                  { title: "时间", dataIndex: "created_at", width: 165 },
                ]} />
                {canManage && (
                  <Card size="small" title="新增客户注意事项" style={{ marginTop: 16 }}>
                    <Form form={customerEventForm} layout="vertical">
                      <Form.Item label="事项内容" name="content" rules={[{ required: true, message: "请输入客户注意事项" }]}>
                        <Input.TextArea rows={3} maxLength={1000} showCount />
                      </Form.Item>
                      <Button type="primary" onClick={onCreateCustomerEvent}>保存客户注意事项</Button>
                    </Form>
                  </Card>
                )}
              </>
            ),
          },
          {
            key: "shared-objects",
            label: `共享对象（${sharedObjects.length}）`,
            children: (
              <>
                {sharedObjectsError && <Alert type="warning" showIcon message={sharedObjectsError} style={{ marginBottom: 8 }} />}
                <Table rowKey="value" size="small" pagination={false} dataSource={sharedObjects.map((value) => ({ value }))} locale={{ emptyText: "暂无共享对象" }} columns={[{ title: "共享接收人", dataIndex: "value" }]} />
              </>
            ),
          },
          {
            key: "events",
            label: `操作记录（${events.length}）`,
            children: (
              <>
                {historyError && <Alert type="warning" showIcon message={historyError} style={{ marginBottom: 8 }} />}
                <Table rowKey="id" size="small" pagination={false} dataSource={events} locale={{ emptyText: "暂无操作记录" }} columns={[
                  { title: "动作", dataIndex: "action" },
                  { title: "操作人", dataIndex: "operator", render: (value: string) => userLabel(value) },
                  { title: "说明", dataIndex: "comment" },
                  { title: "时间", dataIndex: "created_at" },
                ]} />
              </>
            ),
          },
          {
            key: "documents",
            label: `客户文档（${attachments.length}）`,
            children: (
              <>
                {attachmentError && <Alert type="warning" showIcon message={attachmentError} style={{ marginBottom: 8 }} />}
                <Alert type="info" showIcon title="客户主体资料、授权材料和沟通文件统一归档，可按权限下载。" style={{ marginBottom: 12 }} />
                <Table
                  rowKey="id"
                  size="small"
                  pagination={false}
                  dataSource={attachments}
                  scroll={{ x: 720 }}
                  columns={[
                    { title: "类别", dataIndex: "category", width: 100, render: (v: string) => <Tag>{v}</Tag> },
                    { title: "文件名", dataIndex: "original_name" },
                    { title: "大小", dataIndex: "size", width: 90, render: (v: number) => `${(v / 1024).toFixed(1)} KB` },
                    { title: "上传人", dataIndex: "uploader", width: 80, render: (value: string) => userLabel(value) },
                    { title: "文档日期", render: (_: unknown, r: Attachment) => getCustomerAttachmentDate(r) },
                    {
                      title: "操作",
                      width: 130,
                      render: (_: unknown, row: Attachment) => (
                        <Space size={0}>
                          <Button type="link" onClick={() => onDownloadDocument(row)}>下载</Button>
                          <Button type="link" onClick={() => void onViewDocument(row)}>预览</Button>
                          {canDeleteCustomerAttachment(canManage) && (
                            <Popconfirm title="删除客户文档？" onConfirm={() => onDeleteDocument(row.id)}>
                              <Button type="link" danger>删除</Button>
                            </Popconfirm>
                          )}
                        </Space>
                      ),
                    },
                  ]}
                />
                <Card size="small" title="上传客户文档" style={{ marginTop: 16 }}>
                  <Form form={documentForm} layout="vertical" initialValues={CUSTOMER_DOCUMENT_FORM_DEFAULTS}>
                    <div className="form-grid">
                      <Form.Item label="文档类别" name="category" rules={[{ required: true }]}>
                        <Select options={["客户资料", "工商材料", "授权委托", "沟通记录", "开票资料", "其他材料"].map((v) => ({ value: v, label: v }))} />
                      </Form.Item>
                      <Form.Item label="选择文件" required>
                        <input
                          ref={documentFileRef}
                          type="file"
                          accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar"
                          onChange={(e) => onDocumentFileChange(e.target.files?.[0] || null)}
                        />
                      </Form.Item>
                    </div>
                    <Form.Item label="文件说明" name="remark">
                      <Input />
                    </Form.Item>
                    <Button type="primary" icon={<UploadOutlined />} onClick={onUploadDocument}>上传文档</Button>
                  </Form>
                </Card>
              </>
            ),
          },
        ]}
      />
    </Drawer>
  );
}

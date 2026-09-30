import dayjs from "dayjs";
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Upload,
} from "antd";
import { ReloadOutlined, UploadOutlined } from "@ant-design/icons";
import { displayChinesePersonName, displayChinesePersonNames } from "../contractPeoplePresentation.mjs";
import { canDeleteCustomerAttachment, getCustomerAttachmentDate } from "../customerUiBatchI15.mjs";
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

interface CustomerDetailViewProps {
  initialView: string;
  customer: Customer;
  directory: DirectoryUser[];
  customerTypeOptions: { value: string; label: string }[];
  detailTab: string;
  detailLoading: boolean;
  recordError: string;
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
  customerLicenseAttachment: Attachment | undefined;
  customerLicenseThumb: string;
  canManage: boolean;
  customerEventForm: FormInstance;
  onTabChange: (key: string) => void;
  onClose: () => void;
  onRefreshContacts: () => void;
  onContactPageChange: (page: number, pageSize: number) => void;
  onNewContact: () => void;
  onViewContact: (contact: Contact) => void;
  onEditContact: (contact: Contact) => void;
  onDeleteContact: (id: string) => void;
  onSetContactPrimary: (contact: Contact) => void;
  onSetContactActive: (contact: Contact) => void;
  onSetContactInactive: (contact: Contact) => void;
  onUploadContactPhoto: (contact: Contact, option: any) => void;
  onViewContactPhoto: (contact: Contact) => void;
  onViewDocument: (file: Attachment) => void;
  onDownloadDocument: (file: Attachment) => void;
  onDeleteDocument: (id: number) => void;
  onDeleteNote: (id: string) => void;
  onEditNote: (note: Note) => void;
  onNewNote: () => void;
  onNewDocument: () => void;
  onOpenLicenseUpload: () => void;
  onOpenContracts: () => void;
  onNewContract: () => void;
  onCreateCustomerEvent: () => void;
}

export function CustomerDetailView({
  initialView,
  customer,
  directory,
  customerTypeOptions,
  detailTab,
  detailLoading,
  recordError,
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
  customerLicenseAttachment,
  customerLicenseThumb,
  canManage,
  customerEventForm,
  onTabChange,
  onClose,
  onRefreshContacts,
  onContactPageChange,
  onNewContact,
  onViewContact,
  onEditContact,
  onDeleteContact,
  onSetContactPrimary,
  onSetContactActive,
  onSetContactInactive,
  onUploadContactPhoto,
  onViewContactPhoto,
  onViewDocument,
  onDownloadDocument,
  onDeleteDocument,
  onDeleteNote,
  onEditNote,
  onNewNote,
  onNewDocument,
  onOpenLicenseUpload,
  onOpenContracts,
  onNewContract,
  onCreateCustomerEvent,
}: CustomerDetailViewProps) {
  const userLabels = (values: unknown) => displayChinesePersonNames(values, directory);
  const userLabel = (value: string) => displayChinesePersonName(value, directory);

  const displayDate = (value?: string) => {
    const parsed = dayjs(value);
    return value && parsed.isValid() ? parsed.format("YYYY-M-D") : "—";
  };

  const contactAccountLabels = (c?: Customer | null) => userLabels(
    c?.data.contact_account_display_names?.length
      ? c.data.contact_account_display_names
      : c?.data.contact_accounts?.length
      ? c.data.contact_accounts
      : Array.isArray(c?.data.contact)
        ? c?.data.contact
        : c?.data.contact
          ? [c.data.contact]
          : [],
  );

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

  const viewTitle = initialView === "customer-company-recycle" ? "公司回收站"
    : initialView === "customer-recent-update" ? "最近更新的客户"
    : initialView === "customer-recent-contact" ? "最近联系的客户"
    : initialView === "customer-shared" ? "我的共享客户"
    : initialView === "customer-public" ? "公海客户"
    : initialView === "customer-company" ? "公司客户"
    : initialView === "customer-dept" ? "部门客户"
    : initialView === "customer-dept-recycle" ? "部门回收站"
    : initialView === "customer-recycle" ? "个人回收站"
    : "我的客户";

  return (
    <Card className="customer-view-page" loading={detailLoading}>
      <div className="customer-view-tabbar">
        <span>{viewTitle}</span>
        <Button type="text" aria-label="关闭客户查看" onClick={onClose}>×</Button>
      </div>
      {recordError && <Alert type="warning" showIcon message={recordError} style={{ marginBottom: 8 }} />}
      <section>
        <h3>基本信息</h3>
        <div className="customer-view-fields customer-view-fields-four">
          <label><span><i>*</i>客户名称</span><Input disabled value={customer.title} /></label>
          <label><span>客户编码</span><Input disabled value={customer.serial_no} placeholder="自动生成" /></label>
          <label><span>客户状态</span><Select disabled value={["潜在","目标","立项","关怀","签约","谈判","价值"].includes(customer.status) ? customer.status : "请选择"} options={["请选择","潜在","目标","立项","关怀","签约","谈判","价值"].map(value=>({value,label:value}))} /></label>
          <label><span>客户类型</span><Select disabled value={customer.data.customer_type || "客户"} options={customerTypeOptions} /></label>
          <label><span>注册地址</span><Input disabled value={customer.data.registered_address || ""} /></label>
          <label><span>电话</span><Input disabled value={customer.data.phone || ""} /></label>
          <label><span>传 真</span><Input disabled value={customer.data.fax || ""} /></label>
        </div>
      </section>
      <section>
        <h3>法人信息</h3>
        <div className="customer-view-fields customer-view-fields-four">
          <label><span>法人姓名</span><Input disabled value={customer.data.legal_representative || ""} /></label>
          <label><span>组织类型</span><Input disabled value={customer.data.organization_type || ""} /></label>
          {customer.data.organization_type === "个人" && <label><span>客户身份证号</span><Input disabled value={customer.data.identity_no || ""} /></label>}
          <label><span>法人身份证号</span><Input disabled value={customer.data.legal_agent_id_no || ""} /></label>
          <label><span>职务</span><Input disabled value={customer.data.legal_agent_title || ""} /></label>
        </div>
      </section>
      <section>
        <h3>开票信息</h3>
        <div className="customer-view-fields customer-view-fields-four">
          <label><span>开票地址</span><Input disabled value={customer.data.invoice_address || ""} /></label>
          <label className="customer-credit-code-field"><span>统一社会信用代码</span><Input disabled value={customer.data.credit_code || customer.data.taxpayer_id || ""} /></label>
          <label><span>开 户 行</span><Input disabled value={customer.data.bank_name || ""} /></label>
          <label><span>帐 号</span><Input disabled value={customer.data.bank_account || ""} /></label>
        </div>
      </section>
      <section>
        <h3>控制信息</h3>
        <div className="customer-view-fields customer-view-fields-five">
          <label><span>建档日期</span><Input disabled value={customer.data.file_date || displayDate(customer.created_at)} /></label>
          <label><span>客户来源</span><Input disabled value={customer.data.customer_source_display_name || (customer.data.customer_source ? userLabel(customer.data.customer_source) : userLabel(customer.owner))} /></label>
          <label><span>是否共享</span><Select disabled value={customer.data.is_shared || "否"} options={["是","否"].map(value=>({value,label:value}))} /></label>
          <label><span>客户等级</span><Select disabled value={customer.data.level || "立案客户"} options={["签约客户","立案客户","高级客户","中级客户","低级客户"].map(value=>({value,label:value}))} /></label>
          <label><span>上海市资助信息</span><Select disabled value={customer.data.is_assisted || "否"} options={["是","否"].map(value=>({value,label:value}))} /></label>
          <label><span>客戶管理人</span><Input disabled value={userLabels((customer.data as any).customer_manager_display_names || customer.data.customer_managers || [customer.owner])} /></label>
          <label><span>客户联系人账号</span><Input disabled value={contactAccountLabels(customer)} /></label>
        </div>
      </section>
      <section className="customer-license-section">
        <h3>营业执照</h3>
        {customerLicenseAttachment ? (
          <div className="customer-license-card">
            {customerLicenseThumb && <img className="customer-license-thumb" alt="营业执照" src={customerLicenseThumb} />}
            <Space>
              <Button type="link" onClick={() => onViewDocument(customerLicenseAttachment)}>查看营业执照</Button>
              <Button type="link" onClick={() => onDownloadDocument(customerLicenseAttachment)}>下载营业执照</Button>
            </Space>
          </div>
        ) : (
          <div className="customer-license-empty">暂无营业执照</div>
        )}
        {canManage && <Button icon={<UploadOutlined />} onClick={onOpenLicenseUpload}>上传营业执照</Button>}
      </section>
      <Tabs
        className="customer-view-tabs"
        activeKey={detailTab}
        onChange={onTabChange}
        items={[
          {
            key: "contacts",
            label: "联系人",
            children: (
              <>
                <Space style={{ marginBottom: 8 }}>
                  {canManage && <Button size="small" type="primary" onClick={onNewContact}>新建联系人</Button>}
                  <Button size="small" icon={<ReloadOutlined />} onClick={onRefreshContacts}>刷新</Button>
                </Space>
                <Table
                  className="customer-contact-table"
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
                  dataSource={customer.data.contacts || []}
                  scroll={{ x: 1460 }}
                  locale={{ emptyText: "没有查询到联系人" }}
                  columns={[
                    { title: "序号", render: (_: unknown, _row: Contact, index: number) => index + 1, width: 55 },
                    { title: "姓名", dataIndex: "name" },
                    { title: "职务", dataIndex: "position" },
                    { title: "项目角色", dataIndex: "project_role" },
                    { title: "办公电话", dataIndex: "office_phone" },
                    { title: "移动电话", dataIndex: "phone" },
                    { title: "IM", dataIndex: "im_account" },
                    { title: "邮箱", dataIndex: "email" },
                    { title: "是否接收邮件", render: (_: unknown, row: Contact) => row.email ? "是" : "否" },
                    { title: "是否需要联系", render: (_: unknown, row: Contact) => row.contact_status !== "停止联系" ? "是" : "否" },
                    { title: "是否有效", render: (_: unknown, row: Contact) => row.is_valid !== false ? "是" : "否" },
                    { title: "照片", width: 150, render: (_: unknown, row: Contact) => contactPhotoActions(row) },
                    {
                      title: "操作",
                      render: (_: unknown, row: Contact) => canManage ? (
                        <Space size={0}>
                          <Button type="link" onClick={() => onEditContact(row)}>编辑</Button>
                          {!row.is_primary && <Button type="link" onClick={() => void onSetContactPrimary(row)}>设为主要</Button>}
                          {row.is_valid === false && <Button type="link" onClick={() => void onSetContactActive(row)}>设为有效</Button>}
                          {row.is_valid !== false && <Button type="link" onClick={() => void onSetContactInactive(row)}>设为无效</Button>}
                        </Space>
                      ) : null,
                    },
                    { title: "查看", render: (_: unknown, row: Contact) => <Button type="link" onClick={() => onViewContact(row)}>查看</Button> },
                  ]}
                />
              </>
            ),
          },
          {
            key: "contracts",
            label: `合同（${customer.data.contract_count ?? 0}）`,
            children: (
              <Space>
                <Button type="primary" onClick={onOpenContracts}>查看合同</Button>
                {canManage && <Button onClick={onNewContract}>新增合同</Button>}
              </Space>
            ),
          },
          {
            key: "notes",
            label: "事项记录",
            children: (
              <Table
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={customer.data.notes || []}
                scroll={{ x: 720 }}
                locale={{ emptyText: ["customer-shared", "customer-company"].includes(initialView) ? "没有查询到事项记录，可以去 新建" : "没有查询到事项记录" }}
                columns={[
                  { title: "序号", render: (_: unknown, _row: Note, index: number) => index + 1, width: 55 },
                  { title: "内容", dataIndex: "content" },
                  { title: "操作人", dataIndex: "operator", render: (value: string) => userLabel(value) },
                  { title: "操作日期", dataIndex: "created_at" },
                  { title: "操作", render: () => null },
                ]}
              />
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
                <Table rowKey="value" size="small" pagination={false} dataSource={sharedObjects.map((value) => ({ value }))} locale={{ emptyText: "暂无共享对象" }} columns={[{ title: "共享接收人", dataIndex: "value", render: (value: string) => userLabel(value) }]} />
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
            label: "客户文档",
            children: (
              <Table
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={attachments}
                scroll={{ x: 720 }}
                locale={{ emptyText: ["customer-shared", "customer-company"].includes(initialView) ? "没有查询到客户文件，可以去 上传客户文件" : "没有查询到客户文件" }}
                columns={[
                  { title: "序号", render: (_: unknown, _row: Attachment, index: number) => index + 1, width: 55 },
                  { title: "上传人", dataIndex: "uploader", render: (value: string) => userLabel(value) },
                  { title: "文件名称", dataIndex: "original_name" },
                  { title: "文档日期", render: (_: unknown, row: Attachment) => getCustomerAttachmentDate(row) },
                  { title: "查看", render: (_: unknown, row: Attachment) => <Button type="link" onClick={() => void onViewDocument(row)}>查看</Button> },
                  { title: "下载", render: (_: unknown, row: Attachment) => <Button type="link" onClick={() => void onDownloadDocument(row)}>下载</Button> },
                  { title: "操作", render: () => null },
                ]}
              />
            ),
          },
        ]}
      />
      {canManage && detailTab === "notes" && (
        <div className="customer-detail-actions">
          <Button type="link" onClick={onNewNote}>{initialView === "customer-company" ? "新建" : "新建事项记录"}</Button>
          {(customer.data.notes || []).map((note) => (
            <Space key={note.id} size={0}>
              <Button type="link" onClick={() => onEditNote(note)}>编辑事项记录</Button>
              <Popconfirm title="删除这条记录？" onConfirm={() => onDeleteNote(note.id)}>
                <Button type="link" danger>删除事项记录</Button>
              </Popconfirm>
            </Space>
          ))}
        </div>
      )}
      {canManage && detailTab === "documents" && (
        <div className="customer-detail-actions">
          <Button type="link" onClick={onNewDocument}>上传客户文件</Button>
          {canDeleteCustomerAttachment(canManage) && attachments.map((attachment) => (
            <Popconfirm key={attachment.id} title="删除客户文档？" onConfirm={() => onDeleteDocument(attachment.id)}>
              <Button type="link" danger>删除客户文档</Button>
            </Popconfirm>
          ))}
        </div>
      )}
    </Card>
  );
}

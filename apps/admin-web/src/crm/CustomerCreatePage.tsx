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
  Upload,
} from "antd";
import { displayChinesePersonName } from "../contractPeoplePresentation.mjs";
import { ReloadOutlined } from "@ant-design/icons";
import { matchesDirectoryOption } from "../customerUiBatchI14.mjs";
import { CUSTOMER_DOCUMENT_FORM_DEFAULTS, canDeleteCustomerAttachment, getCustomerAttachmentDate } from "../customerUiBatchI15.mjs";
import { customerRegistrationAddressRules, customerPostalCodeRules } from "./constants";
import type { FormInstance } from "antd";
import type { Attachment, Contact, Customer, DirectoryUser, Note } from "./types";

interface CustomerCreatePageProps {
  form: FormInstance;
  customerTypeOptions: { value: string; label: string }[];
  directoryOptions: { value: string; label: string }[];
  directory: DirectoryUser[];
  customerContactOptions: { value: string; label: string }[];
  detailLoading: boolean;
  attachmentError: string;
  contactPage: number;
  contactPageSize: number;
  contactTotal: number;
  contacts: Customer | null;
  attachments: Attachment[];
  canManage: boolean;
  onEditContact: (contact: Contact) => void;
  onDeleteContact: (id: string) => void;
  onUploadContactPhoto: (contact: Contact, option: any) => void;
  onViewContactPhoto: (contact: Contact) => void;
  onDeleteNote: (id: string) => void;
  onDeleteDocument: (id: number) => void;
  onSave: () => void;
  onRefreshContacts: () => void;
  onContactPageChange: (page: number, pageSize: number) => void;
  onNewEditor: (type: "contact" | "note" | "document") => void;
  onViewDocument: (file: Attachment) => void;
  onDownloadDocument: (file: Attachment) => void;
}

export function CustomerCreatePage({
  form,
  customerTypeOptions,
  directoryOptions,
  directory,
  customerContactOptions,
  detailLoading,
  attachmentError,
  contactPage,
  contactPageSize,
  contactTotal,
  contacts,
  attachments,
  canManage,
  onEditContact,
  onDeleteContact,
  onUploadContactPhoto,
  onViewContactPhoto,
  onDeleteNote,
  onDeleteDocument,
  onSave,
  onRefreshContacts,
  onContactPageChange,
  onNewEditor,
  onViewDocument,
  onDownloadDocument,
}: CustomerCreatePageProps) {
  const userLabel = (value: unknown) => displayChinesePersonName(value, directory);
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

  const renderCustomerRelatedTabs = () => (
    <Tabs
      className="customer-create-tabs"
      tabBarExtraContent={
        <Button type="primary" onClick={onSave}>
          <span>保</span><span>存</span>
        </Button>
      }
      items={[
        {
          key: "contacts",
          label: "联系人",
          children: (
            <>
              <Space style={{ marginBottom: 8 }}>
                <Button size="small" icon={<ReloadOutlined />} onClick={onRefreshContacts}>刷新</Button>
              </Space>
              <Table
                className="customer-create-related-table customer-contact-table"
                loading={detailLoading}
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
                dataSource={contacts?.data.contacts || []}
                scroll={{ x: 1460 }}
                locale={{
                  emptyText: (
                    <span>
                      没有查询到联系人，可以去{" "}
                      <Button type="link" onClick={() => onNewEditor("contact")}>
                        新建联系人
                      </Button>
                    </span>
                  ),
                }}
                columns={[
                  { title: "序号", render: (_: unknown, _r: Contact, index: number) => index + 1, width: 55 },
                  { title: "姓名", dataIndex: "name" },
                  { title: "职务", dataIndex: "position" },
                  { title: "项目角色", dataIndex: "project_role" },
                  { title: "办公电话", dataIndex: "office_phone" },
                  { title: "移动电话", dataIndex: "phone" },
                  { title: "IM", dataIndex: "im_account" },
                  { title: "邮箱", dataIndex: "email" },
                  { title: "是否接收邮件", render: (_: unknown, row: Contact) => row.email ? "是" : "否" },
                  { title: "是否需要联系", render: (_: unknown, row: Contact) => row.contact_status !== "停止联系" ? "是" : "否" },
                  { title: "是否有效", dataIndex: "is_valid", render: (value: boolean) => value !== false ? "是" : "否" },
                  { title: "照片", width: 150, render: (_: unknown, row: Contact) => contactPhotoActions(row) },
                  { title: "操作", render: (_: unknown, row: Contact) => canManage ? <Space size={0}><Button type="link" onClick={() => onEditContact(row)}>编辑</Button><Popconfirm title="删除联系人？" onConfirm={() => onDeleteContact(row.id)}><Button type="link" danger>删除</Button></Popconfirm></Space> : null },
                ]}
              />
              {(contacts?.data.contacts?.length || 0) > 0 && (
                <Button className="customer-create-related-link" type="link" onClick={() => onNewEditor("contact")}>
                  新建联系人
                </Button>
              )}
            </>
          ),
        },
        {
          key: "notes",
          label: "事项记录",
          children: (
            <>
              <Table
                className="customer-create-related-table"
                loading={detailLoading}
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={contacts?.data.notes || []}
                scroll={{ x: 720 }}
                locale={{
                  emptyText: (
                    <span>
                      没有查询到事项记录，可以去{" "}
                      <Button type="link" onClick={() => onNewEditor("note")}>新建</Button>
                    </span>
                  ),
                }}
                columns={[
                  { title: "序号", render: (_: unknown, _r: Note, index: number) => index + 1, width: 55 },
                  { title: "内容", dataIndex: "content" },
                  { title: "操作人", dataIndex: "operator", width: 110, render: (value: string) => userLabel(value) },
                  { title: "操作日期", dataIndex: "created_at", width: 170 },
                  { title: "操作", render: (_: unknown, row: Note) => <Popconfirm title="删除这条记录？" onConfirm={() => onDeleteNote(row.id)}><Button type="link" danger>删除</Button></Popconfirm> },
                ]}
              />
              {(contacts?.data.notes?.length || 0) > 0 && (
                <Button className="customer-create-related-link" type="link" onClick={() => onNewEditor("note")}>
                  新建
                </Button>
              )}
            </>
          ),
        },
        {
          key: "documents",
          label: "客户文档",
          children: (
            <>
              {attachmentError && <Alert type="warning" showIcon message={attachmentError} style={{ marginBottom: 8 }} />}
              <Table
                className="customer-create-related-table"
                loading={detailLoading}
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={attachments}
                scroll={{ x: 720 }}
                locale={{
                  emptyText: (
                    <span>
                      没有查询到客户文件，可以去{" "}
                      <Button type="link" onClick={() => onNewEditor("document")}>上传客户文件</Button>
                    </span>
                  ),
                }}
                columns={[
                  { title: "序号", render: (_: unknown, _r: Attachment, index: number) => index + 1, width: 55 },
                  { title: "上传人", dataIndex: "uploader", width: 110, render: (value: string) => userLabel(value) },
                  { title: "文件名称", dataIndex: "original_name" },
                  { title: "文档日期", width: 170, render: (_: unknown, row: Attachment) => getCustomerAttachmentDate(row) },
                  { title: "查看", render: (_: unknown, row: Attachment) => <Button type="link" onClick={() => void onViewDocument(row)}>查看</Button> },
                  { title: "下载", render: (_: unknown, row: Attachment) => <Button type="link" onClick={() => void onDownloadDocument(row)}>下载</Button> },
                  { title: "操作", render: (_: unknown, row: Attachment) => canDeleteCustomerAttachment(canManage) ? <Popconfirm title="删除客户文档？" onConfirm={() => onDeleteDocument(row.id)}><Button type="link" danger>删除</Button></Popconfirm> : null },
                ]}
              />
              {attachments.length > 0 && (
                <Button className="customer-create-related-link" type="link" onClick={() => onNewEditor("document")}>
                  上传客户文件
                </Button>
              )}
            </>
          ),
        },
      ]}
    />
  );

  return (
    <Card className="customer-create-page">
      <Form form={form} layout="horizontal" className="customer-create-form">
        <section>
          <h3>基本信息</h3>
          <div className="customer-create-grid">
            <Form.Item label="客户名称" name="title" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item label="客户编码" name="serial_no"><Input disabled placeholder="自动生成" /></Form.Item>
            <Form.Item label="客户状态" name="status"><Select allowClear placeholder="请选择" options={["潜在","目标","立项","关怀","签约","谈判","价值"].map(value=>({value,label:value}))} /></Form.Item>
            <Form.Item label="客户类型" name="customer_type"><Select options={customerTypeOptions} /></Form.Item>
            <Form.Item label="注册地址" name="registered_address" rules={customerRegistrationAddressRules}><Input /></Form.Item>
            <Form.Item label="邮编" name="postal_code" rules={customerPostalCodeRules}><Input /></Form.Item>
            <Form.Item label="客户简称" name="short_name"><Input /></Form.Item>
            <Form.Item label="电话" name="phone"><Input /></Form.Item>
            <Form.Item label="传真" name="fax"><Input /></Form.Item>
          </div>
        </section>
        <section>
          <h3>法人信息</h3>
          <div className="customer-create-grid">
            <Form.Item label="法人姓名" name="legal_representative"><Input /></Form.Item>
            <Form.Item label="身份证号" name="legal_agent_id_no"><Input /></Form.Item>
            <Form.Item label="职务" name="legal_agent_title"><Input /></Form.Item>
          </div>
        </section>
        <section>
          <h3>开票信息</h3>
          <div className="customer-create-grid">
            <Form.Item label="开票地址" name="invoice_address"><Input /></Form.Item>
            <Form.Item label="统一社会信用代码" name="credit_code"><Input placeholder="不允许有空格." /></Form.Item>
            <Form.Item label="开户行" name="bank_name"><Input /></Form.Item>
            <Form.Item label="帐号" name="bank_account"><Input /></Form.Item>
          </div>
        </section>
        <section>
          <h3>控制信息</h3>
          <div className="customer-create-grid customer-control-grid">
            <Form.Item label="建档日期" name="file_date"><Input type="date" /></Form.Item>
            <Form.Item label="客户来源" name="customer_source"><Select showSearch optionFilterProp="label" options={directoryOptions} filterOption={matchesDirectoryOption} placeholder="输入或选择人员" /></Form.Item>
            <Form.Item label="是否共享" name="is_shared"><Select options={["是","否"].map(value=>({value,label:value}))} /></Form.Item>
            <Form.Item label="客户等级" name="level"><Select options={["签约客户","立案客户","高级客户","中级客户","低级客户"].map(value=>({value,label:value}))} /></Form.Item>
            <Form.Item label="上海市资助信息" name="is_assisted"><Select options={["是","否"].map(value=>({value,label:value}))} /></Form.Item>
            <Form.Item className="customer-person-multi-field" label="客户管理人" name="customer_managers" rules={[{required:true,message:"至少设置一名客户管理人"}]}>
              <Select mode="multiple" showSearch optionFilterProp="label" options={directoryOptions} />
            </Form.Item>
            <Form.Item className="customer-person-multi-field" label="客户联系人账号" name="contact"><Select mode="multiple" showSearch optionFilterProp="label" options={customerContactOptions} filterOption={matchesDirectoryOption} placeholder="输入姓名或账号，选择客户账号" /></Form.Item>
          </div>
        </section>
      </Form>
      {renderCustomerRelatedTabs()}
    </Card>
  );
}


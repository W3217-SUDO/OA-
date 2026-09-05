import {
  Alert,
  Button,
  Checkbox,
  Form,
  Input,
  Modal,
  Select,
  Space,
} from "antd";
import { CUSTOMER_CONTACT_FORM_DEFAULTS, CUSTOMER_DOCUMENT_FORM_DEFAULTS } from "../customerUiBatchI15.mjs";
import { matchesDirectoryOption } from "../customerUiBatchI14.mjs";
import { displayChinesePersonNames } from "../contractPeoplePresentation.mjs";
import type { FormInstance } from "antd";
import type { Contact, Customer, DirectoryUser, Note } from "./types";

interface CustomerModalsProps {
  // Contact view modal
  viewingContact: Contact | null;
  onCloseViewContact: () => void;

  // Contact photo preview modal
  contactPhotoPreview: { name: string; url: string } | null;
  onCloseContactPhotoPreview: () => void;

  // Customer document preview modal
  customerDocumentPreview: { name: string; url: string } | null;
  onCloseCustomerDocumentPreview: () => void;

  // New contact modal
  newEditorOpen: boolean;
  newEditorType: "contact" | "note" | "document" | null;
  contactForm: FormInstance;
  onCloseNewEditor: () => void;
  onAddContact: () => void;

  // Edit contact modal
  editingContact: Contact | null;
  contactEditForm: FormInstance;
  onCloseEditContact: () => void;
  onUpdateContact: () => void;

  // New note modal
  noteForm: FormInstance;
  onAddNote: () => void;

  // Edit note modal
  editingNote: Note | null;
  noteEditForm: FormInstance;
  onCloseEditNote: () => void;
  onUpdateNote: () => void;

  // Document upload modal
  documentForm: FormInstance;
  documentFileRef: React.RefObject<HTMLInputElement | null>;
  documentFile: File | null;
  onDocumentFileChange: (file: File | null) => void;
  onUploadDocument: () => void;

  // Portal result modal
  portalResult: { account: string; activation_code: string } | null;
  onClosePortalResult: () => void;

  // Portal customer select modal
  portalCustomer: Customer | null;
  portalAccounts: (customer: Customer) => string[];
  onClosePortalCustomer: () => void;
  onOpenPortal: (customer: Customer, account?: string) => void;

  // Assign modal
  assigning: Customer | null;
  assignForm: FormInstance;
  directoryOptions: { value: string; label: string }[];
  directory: DirectoryUser[];
  onCloseAssign: () => void;
  onAssignCustomer: () => void;

  // Share modal
  sharing: Customer | null;
  shareForm: FormInstance;
  onCloseShare: () => void;
  onShare: () => void;
}

export function CustomerModals({
  viewingContact,
  onCloseViewContact,
  contactPhotoPreview,
  onCloseContactPhotoPreview,
  customerDocumentPreview,
  onCloseCustomerDocumentPreview,
  newEditorOpen,
  newEditorType,
  contactForm,
  onCloseNewEditor,
  onAddContact,
  editingContact,
  contactEditForm,
  onCloseEditContact,
  onUpdateContact,
  noteForm,
  onAddNote,
  editingNote,
  noteEditForm,
  onCloseEditNote,
  onUpdateNote,
  documentForm,
  documentFileRef,
  documentFile,
  onDocumentFileChange,
  onUploadDocument,
  portalResult,
  onClosePortalResult,
  portalCustomer,
  portalAccounts,
  onClosePortalCustomer,
  onOpenPortal,
  assigning,
  assignForm,
  directoryOptions,
  directory,
  onCloseAssign,
  onAssignCustomer,
  sharing,
  shareForm,
  onCloseShare,
  onShare,
}: CustomerModalsProps) {
  const userLabels = (values: unknown) => displayChinesePersonNames(values, directory);

  return (
    <>
      {/* 查看联系人 Modal */}
      <Modal
        open={Boolean(viewingContact)}
        title={`查看联系人：${viewingContact?.name || ""}`}
        footer={<Button onClick={onCloseViewContact}>关闭</Button>}
        onCancel={onCloseViewContact}
        destroyOnHidden
      >
        <div className="customer-contact-view-fields">
          <p><b>姓名：</b>{viewingContact?.name || ""}</p>
          <p><b>职务：</b>{viewingContact?.position || ""}</p>
          <p><b>项目角色：</b>{viewingContact?.project_role || ""}</p>
          <p><b>办公电话：</b>{viewingContact?.office_phone || ""}</p>
          <p><b>移动电话：</b>{viewingContact?.phone || ""}</p>
          <p><b>IM：</b>{viewingContact?.im_account || ""}</p>
          <p><b>邮箱：</b>{viewingContact?.email || ""}</p>
          <p><b>联系状态：</b>{viewingContact?.contact_status || ""}</p>
          <p><b>是否有效：</b>{viewingContact?.is_valid === false ? "否" : "是"}</p>
        </div>
      </Modal>

      {/* 联系人照片预览 Modal */}
      <Modal
        open={Boolean(contactPhotoPreview)}
        title={contactPhotoPreview?.name || "联系人照片"}
        footer={null}
        onCancel={onCloseContactPhotoPreview}
        destroyOnHidden
      >
        <img
          src={contactPhotoPreview?.url}
          alt={contactPhotoPreview?.name || "联系人照片"}
          style={{ display: "block", maxWidth: "100%", maxHeight: 560, margin: "0 auto" }}
        />
      </Modal>

      {/* 客户文档预览 Modal */}
      <Modal
        open={Boolean(customerDocumentPreview)}
        title={customerDocumentPreview?.name || "客户文档预览"}
        footer={null}
        width={960}
        onCancel={onCloseCustomerDocumentPreview}
        destroyOnHidden
      >
        <iframe
          title={customerDocumentPreview?.name || "客户文档预览"}
          src={customerDocumentPreview?.url}
          style={{ display: "block", width: "100%", height: "72vh", border: 0 }}
        />
      </Modal>

      {/* 新建联系人 Modal */}
      <Modal
        open={newEditorOpen && newEditorType === "contact"}
        title="新建联系人"
        okText="保存"
        cancelText="取消"
        onOk={onAddContact}
        onCancel={onCloseNewEditor}
        destroyOnHidden
      >
        <Form form={contactForm} layout="vertical" initialValues={CUSTOMER_CONTACT_FORM_DEFAULTS}>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item>
          <div className="form-grid">
            <Form.Item name="name" label="姓名" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="position" label="职务"><Input /></Form.Item>
            <Form.Item name="project_role" label="项目角色"><Input /></Form.Item>
            <Form.Item name="office_phone" label="办公电话"><Input /></Form.Item>
            <Form.Item name="phone" label="移动电话"><Input /></Form.Item>
            <Form.Item name="im_account" label="IM"><Input /></Form.Item>
            <Form.Item name="email" label="邮箱"><Input /></Form.Item>
            <Form.Item name="portal_account" label="客户服务账号"><Input placeholder="可选；保存后同步到员工管理" /></Form.Item>
            <Form.Item name="portal_password" label="客户服务密码" rules={[{ min: 8, message: "密码至少 8 位" }]}><Input.Password placeholder="填写后可直接登录客户服务端" /></Form.Item>
            <Form.Item name="contact_status" label="联系状态" initialValue="正常联系"><Select options={["正常联系", "暂缓联系", "停止联系"].map(value => ({ value, label: value }))} /></Form.Item>
          </div>
          <Form.Item name="is_valid" valuePropName="checked" initialValue><Checkbox>是否有效</Checkbox></Form.Item>
        </Form>
      </Modal>

      {/* 编辑联系人 Modal */}
      <Modal
        open={Boolean(editingContact)}
        title={`编辑联系人：${editingContact?.name || ""}`}
        okText="保存"
        cancelText="取消"
        onOk={onUpdateContact}
        onCancel={onCloseEditContact}
        destroyOnHidden
      >
        <Form form={contactEditForm} layout="vertical">
          <div className="form-grid">
            <Form.Item name="name" label="姓名" rules={[{ required: true, message: "请输入联系人姓名" }]}><Input /></Form.Item>
            <Form.Item name="position" label="职务"><Input /></Form.Item>
            <Form.Item name="project_role" label="项目角色"><Input /></Form.Item>
            <Form.Item name="office_phone" label="办公电话"><Input /></Form.Item>
            <Form.Item name="phone" label="移动电话"><Input /></Form.Item>
            <Form.Item name="im_account" label="IM"><Input /></Form.Item>
            <Form.Item name="email" label="邮箱"><Input /></Form.Item>
            <Form.Item name="contact_status" label="联系状态"><Select options={["正常联系", "暂缓联系", "停止联系"].map(value => ({ value, label: value }))} /></Form.Item>
          </div>
          <Form.Item name="is_valid" valuePropName="checked"><Checkbox>是否有效</Checkbox></Form.Item>
          <Form.Item name="is_primary" valuePropName="checked"><Checkbox>设为主要联系人</Checkbox></Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={3} /></Form.Item>
          <Alert type="info" showIcon title="保存会直接更新原联系人记录，不会删除重建，并写入客户审计日志。" />
        </Form>
      </Modal>

      {/* 新建事项记录 Modal */}
      <Modal
        open={newEditorOpen && newEditorType === "note"}
        title="新建事项记录"
        okText="保存"
        cancelText="取消"
        onOk={onAddNote}
        onCancel={onCloseNewEditor}
        destroyOnHidden
      >
        <Form form={noteForm} layout="vertical" initialValues={{ note_type: "跟进记录" }}>
          <Form.Item name="note_type" label="记录类型">
            <Select options={["跟进记录", "会议纪要", "电话沟通", "风险提示", "客户备注"].map(value => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item name="content" label="内容" rules={[{ required: true }]}><Input.TextArea rows={4} /></Form.Item>
        </Form>
      </Modal>

      {/* 编辑事项记录 Modal */}
      <Modal
        open={Boolean(editingNote)}
        title="编辑事项记录"
        okText="保存修改"
        cancelText="取消"
        onOk={onUpdateNote}
        onCancel={onCloseEditNote}
        destroyOnHidden
      >
        <Form form={noteEditForm} layout="vertical">
          <Form.Item name="note_type" label="记录类型">
            <Select options={["跟进记录", "会议纪要", "电话沟通", "风险提示", "客户备注"].map(value => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item name="content" label="内容" rules={[{ required: true }]}><Input.TextArea rows={4} /></Form.Item>
          <Alert type="info" showIcon message="保存将更新当前事项记录，保留原始创建人和创建时间。" />
        </Form>
      </Modal>

      {/* 上传客户文件 Modal */}
      <Modal
        open={newEditorOpen && newEditorType === "document"}
        title="上传客户文件"
        okText="上传"
        cancelText="取消"
        onOk={onUploadDocument}
        onCancel={onCloseNewEditor}
        destroyOnHidden
      >
        <Form form={documentForm} layout="vertical" initialValues={CUSTOMER_DOCUMENT_FORM_DEFAULTS}>
          <Form.Item name="category" label="文档类别">
            <Select options={["客户资料", "工商材料", "授权委托", "沟通记录", "开票资料", "其他材料"].map(value => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item label="选择文件">
            <input
              ref={documentFileRef}
              type="file"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.png,.jpg,.jpeg,.zip,.rar"
              onChange={event => onDocumentFileChange(event.target.files?.[0] || null)}
            />
          </Form.Item>
          <Form.Item name="remark" label="说明"><Input /></Form.Item>
        </Form>
      </Modal>

      {/* 客户服务端开通结果 Modal */}
      <Modal
        open={Boolean(portalResult)}
        title="客户服务端已开通"
        footer={<Button type="primary" onClick={onClosePortalResult}>我已安全保存</Button>}
        closable={false}
      >
        <Alert type="warning" showIcon message="请将服务账号和一次性激活码一并交付客户；客户首次登录时需用二者设置密码。激活码仅本次显示，再次开通会重置旧激活码。登录入口：客户服务端。" />
        <p style={{ marginTop: 16 }}><strong>客户服务端地址：</strong>{window.location.origin}/?page=customer-portal</p>
        <p><strong>服务账号：</strong>{portalResult?.account}</p>
        <p><strong>一次性激活码：</strong>{portalResult?.activation_code}</p>
      </Modal>

      {/* 选择客户服务账号 Modal */}
      <Modal
        open={Boolean(portalCustomer)}
        title={`选择客户服务账号：${portalCustomer?.title || ""}`}
        footer={null}
        onCancel={onClosePortalCustomer}
      >
        <Alert type="info" showIcon message="客户联系人可绑定多个账号，请选择本次用于登录客户服务端的账号。" style={{ marginBottom: 16 }} />
        <Space direction="vertical" style={{ width: "100%" }}>
          {portalCustomer && portalAccounts(portalCustomer).map((account) => (
            <Button key={account} block onClick={() => void onOpenPortal(portalCustomer!, account)}>{account}</Button>
          ))}
        </Space>
      </Modal>

      {/* 客户分配 Modal */}
      <Modal
        open={Boolean(assigning)}
        title="客户分配"
        okText="确定"
        cancelText="取消"
        onOk={onAssignCustomer}
        onCancel={onCloseAssign}
      >
        <Form form={assignForm} layout="horizontal" className="customer-assign-form">
          <Form.Item label="客户编码">
            <Input readOnly value={assigning?.serial_no || ""} />
          </Form.Item>
          <Form.Item label="客户名称">
            <Input readOnly value={assigning?.title || ""} />
          </Form.Item>
          <Form.Item label="原客戶管理人">
            <Input
              readOnly
              value={userLabels((assigning?.data as any)?.customer_manager_display_names || assigning?.data.customer_managers || (assigning ? [assigning.owner] : []))}
            />
          </Form.Item>
          <Form.Item
            label="现客戶管理人"
            name="manager"
            rules={[{ required: true, message: "请选择现客戶管理人" }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={directoryOptions}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 共享客户 Modal */}
      <Modal
        open={Boolean(sharing)}
        title={`共享客户：${sharing?.title || ""}`}
        okText="确认共享"
        onOk={onShare}
        onCancel={onCloseShare}
      >
        <Form form={shareForm} layout="vertical">
          <Form.Item
            label="共享人员"
            name="recipients"
            rules={[{ required: true }]}
          >
            <Select
              mode="multiple"
              showSearch
              optionFilterProp="label"
              options={directoryOptions}
              filterOption={matchesDirectoryOption}
              tokenSeparators={[",", "，"]}
              placeholder="输入账号后回车，可添加多人"
            />
          </Form.Item>
          <Form.Item label="共享说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

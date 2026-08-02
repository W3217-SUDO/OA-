import { useEffect, useMemo, useRef, useState } from "react";
import type { Key } from "react";
import {
  Alert,
  AutoComplete,
  Button,
  Card,
  Checkbox,
  Drawer,
  Dropdown,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Upload,
} from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  TeamOutlined,
  UndoOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { consumeCustomerDetailTarget } from "./customerDetailNavigation";
import { rememberCustomerRelationTarget } from "./customerRelationNavigation";
import "./customer-center.css";
type Contact = {
  id: string;
  name: string;
  project_role: string;
  phone: string;
  office_phone: string;
  im_account: string;
  email: string;
  position: string;
  contact_status: string;
  is_valid: boolean;
  is_primary: boolean;
  remark: string;
  photo_attachment_id?: number;
  photo_original_name?: string;
};
type Note = {
  id: string;
  type: string;
  content: string;
  operator: string;
  created_at: string;
};
type Attachment = {
  id: number;
  category: string;
  original_name: string;
  size: number;
  uploader: string;
  remark: string;
  created_at: string;
};
type Customer = {
  id: number;
  serial_no: string;
  title: string;
  status: string;
  owner: string;
  department: string;
  description: string;
  created_at: string;
  updated_at: string;
  data: {
    contact?: string;
    phone?: string;
    level?: string;
    shared_with?: string[];
    contacts?: Contact[];
    notes?: Note[];
    customer_managers?: string[];
    source_person?: string;
    file_date?: string;
    last_contact_at?: string;
    last_modified_date?: string;
    contact_count?: number;
    contract_count?: number;
    civil_case_count?: number;
    agency_fee_due?: number;
    official_fee_unreceived?: number;
    credit_code?: string;
    legal_representative?: string;
    registered_address?: string;
    invoice_title?: string;
    taxpayer_id?: string;
    invoice_address?: string;
    invoice_phone?: string;
    bank_name?: string;
    bank_account?: string;
    customer_type?: string;
    short_name?: string;
    fax?: string;
    legal_agent_id_no?: string;
    legal_agent_title?: string;
    customer_source?: string;
    is_shared?: string;
    is_assisted?: string;
    province?: string;
    postal_code?: string;
    patent_customer_type?: string;
    fee_reduction?: string;
    industry?: string;
    output_value?: string;
    cooperation_status?: string;
    gb_classification?: string;
    website?: string;
    organization_nature?: string;
    organization_code?: string;
    registration_region?: string;
    registration_postal_code?: string;
    registered_capital?: string;
    registration_year?: string;
    level_change?: {
      status?: string;
      from_level?: string;
      to_level?: string;
      requested_by?: string;
      review_comment?: string;
    };
    key_change?: { status?: string; before?: Record<string, string>; after?: Record<string, string> };
    portal_access?: {
      account?: string;
      enabled?: boolean;
    };
  };
};
type Profile = {
  username: string;
  display_name: string;
  department: string;
  role?: string;
};
type DirectoryUser = {
  username: string;
  display_name: string;
  department: string;
};
const colors: Record<string, string> = {
  正常: "green",
  跟进中: "blue",
  潜在: "blue",
  目标: "cyan",
  立项: "geekblue",
  关怀: "purple",
  签约: "green",
  谈判: "orange",
  价值: "gold",
  公海: "orange",
  已回收: "red",
};
const initialProfile = (): Profile => {
  try {
    const stored = JSON.parse(localStorage.getItem("user") || "{}");
    return {
      username: stored.username || "",
      display_name: stored.display_name || "",
      department: stored.department || "",
      role: stored.role,
    };
  } catch {
    return { username: "", display_name: "", department: "" };
  }
};
export default function CustomerCenterPage({
  initialView,
  onNavigate,
}: {
  initialView: string;
  onNavigate?: (key: string) => void;
}) {
  const originalCustomerScope = {
    "customer-mine": "mine",
    "customer-recycle": "recycle",
    "customer-dept": "department",
    "customer-dept-recycle": "department_recycle",
    "customer-company": "company",
    "customer-public": "public",
    "customer-shared": "shared",
    "customer-recent-contact": "recent_contact",
    "customer-recent-update": "recent_update",
    "customer-company-recycle": "company_recycle",
  }[initialView];
  const isOriginalCustomerList = Boolean(originalCustomerScope);
  const isReadOnlyCustomerList = isOriginalCustomerList;
  const [allRows, setAllRows] = useState<Customer[]>([]),
    [keyword, setKeyword] = useState(""),
    [customerType, setCustomerType] = useState("客户"),
    [customerTypeOptions, setCustomerTypeOptions] = useState<{value:string;label:string}[]>([{value:"客户",label:"客户"},{value:"当事人",label:"当事人"}]),
    [managerKeyword, setManagerKeyword] = useState(""),
    [loading, setLoading] = useState(false),
    [open, setOpen] = useState(initialView === "customer-new"),
    [editing, setEditing] = useState<Customer | null>(null),
    [assigning, setAssigning] = useState<Customer | null>(null),
    [sharing, setSharing] = useState<Customer | null>(null),
    [levelCustomer, setLevelCustomer] = useState<Customer | null>(null),
    [keyChangeCustomer, setKeyChangeCustomer] = useState<Customer | null>(null),
    [portalResult, setPortalResult] = useState<{ account: string; activation_code: string } | null>(null),
    [contacts, setContacts] = useState<Customer | null>(null),
    [editingContact, setEditingContact] = useState<Contact | null>(null),
    [editingNote, setEditingNote] = useState<Note | null>(null),
    [detailPageOpen, setDetailPageOpen] = useState(false),
    [newEditor, setNewEditor] = useState<"contact" | "note" | "document" | null>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]),
    [detailLoading, setDetailLoading] = useState(false),
    [detailTab, setDetailTab] = useState("contacts"),
    [documentFile, setDocumentFile] = useState<File | null>(null),
    [contactPhotoPreview, setContactPhotoPreview] = useState<{name:string;url:string}|null>(null);
  const [profile, setProfile] = useState<Profile>(initialProfile);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const directoryOptions = directory.map((user) => ({
    value: user.username,
    label: user.display_name ? `${user.display_name}（${user.username}）` : user.username,
  }));
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [total, setTotal] = useState(0);
  const [jumpPage, setJumpPage] = useState("1");
  const [listSummary, setListSummary] = useState({
    agency_fee_due: 0,
    official_fee_unreceived: 0,
  });
  const [form] = Form.useForm(),
    [assignForm] = Form.useForm(),
    [shareForm] = Form.useForm(),
    [contactForm] = Form.useForm(),
    [contactEditForm] = Form.useForm(),
    [noteForm] = Form.useForm(),
    [noteEditForm] = Form.useForm(),
    [levelForm] = Form.useForm(),
    [keyChangeForm] = Form.useForm(),
    [documentForm] = Form.useForm();
  const documentFileRef = useRef<HTMLInputElement>(null);
  const resolveCustomerDetailTarget = async (target: {
    id?: number;
    serial_no?: string;
    title?: string;
  }): Promise<Customer | null> => {
    const targetId = Number(target.id || 0);
    if (targetId) {
      try {
        const { data } = await api.get(`/records/${targetId}`);
        if (data.module === "customer") return data as Customer;
      } catch {
        // A scoped record lookup gives the authoritative result; fall back to
        // the stable customer number/name only when the caller has no access.
      }
    }
    const serialNo = String(target.serial_no || "").trim();
    const title = String(target.title || "").trim();
    for (const keyword of [...new Set([serialNo, title].filter(Boolean))]) {
      try {
        const { data } = await api.get("/records", {
          params: { module: "customer", keyword, page_size: 100 },
        });
        const row = (data.items || []).find((item: Customer) =>
          (serialNo && item.serial_no === serialNo) ||
          (title && item.title === title),
        );
        if (row) return row;
      } catch {
        // Continue to the remaining stable identifier before reporting a miss.
      }
    }
    return null;
  };
  const load = async (overrides: Partial<{ keyword: string; customerType: string; managerKeyword: string; page: number }> = {}) => {
    const requestKeyword = overrides.keyword ?? keyword;
    const requestCustomerType = overrides.customerType ?? customerType;
    const requestManagerKeyword = overrides.managerKeyword ?? managerKeyword;
    const requestPage = overrides.page ?? page;
    setLoading(true);
    try {
      const recordsRequest = isOriginalCustomerList
        ? api.get("/customers", {
            params: {
              scope: originalCustomerScope,
              customer_name: requestKeyword,
              customer_type: requestCustomerType,
              ...(["customer-shared", "customer-recent-contact", "customer-recent-update"].includes(initialView) ? {} : { manager: requestManagerKeyword }),
              page: requestPage,
              page_size: pageSize,
            },
          })
        : api.get("/records", {
          params: { module: "customer", keyword: requestKeyword, page_size: 100 },
          });
      // The customer list and an incoming detail target are core content.  Do
      // not make them disappear when the optional identity/directory panels
      // are temporarily unavailable.
      const recordsRes = await recordsRequest;
      const responseItems = recordsRes.data.items || [];
      const responseTotal = Number(recordsRes.data.total || responseItems.length);
      const responseLastPage = Math.max(1, Math.ceil(responseTotal / pageSize));
      if (
        isOriginalCustomerList &&
        responseTotal > 0 &&
        responseItems.length === 0 &&
        requestPage > responseLastPage
      ) {
        setPage(responseLastPage);
        setJumpPage(String(responseLastPage));
        setSelectedRowKeys([]);
        return;
      }
      setAllRows(responseItems);
      setTotal(responseTotal);
      setListSummary(recordsRes.data.summary || {
        agency_fee_due: 0,
        official_fee_unreceived: 0,
      });
      const target = consumeCustomerDetailTarget();
      if (target) {
        const normalizedTitle = String(target.title || "").trim();
        let targetRow = responseItems.find((item: Customer) =>
          (target.id && item.id === target.id) ||
          (target.serial_no && item.serial_no === target.serial_no) ||
          (normalizedTitle && item.title === normalizedTitle)
        );
        if (!targetRow) targetRow = await resolveCustomerDetailTarget(target) || undefined;
        if (targetRow) void openDetail(targetRow);
        else message.warning("未找到关联客户或当前账号无权查看");
      }
      const [profileResult, directoryResult, customerTypeResult] = await Promise.allSettled([
        api.get("/auth/me"),
        api.get("/users/directory"),
        api.get("/customers/reference-options"),
      ]);
      if (profileResult.status === "fulfilled") setProfile(profileResult.value.data);
      else message.warning("当前登录身份加载失败，已保留客户列表和详情入口");
      if (directoryResult.status === "fulfilled") setDirectory(directoryResult.value.data.items || []);
      else message.warning("客户人员目录加载失败，稍后可刷新重试");
      if (customerTypeResult.status === "fulfilled") {
        const options = customerTypeResult.value.data.customer_types || [];
        if (options.length) {
          setCustomerTypeOptions(options);
          if (!options.some((item:{value:string}) => item.value === customerType)) setCustomerType(options[0].value);
        }
      } else message.warning("客户类型加载失败，暂使用缓存选项");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户数据加载失败");
    } finally {
      setLoading(false);
    }
  };
  const queryCustomerList = () => {
    const requestKeyword = keyword;
    const requestManagerKeyword = managerKeyword;
    setSelectedRowKeys([]);
    setPage(1);
    setJumpPage("1");
    void load({
      keyword: requestKeyword,
      customerType,
      managerKeyword: requestManagerKeyword,
      page: 1,
    }).finally(() => {
      if (initialView === "customer-company") {
        setKeyword("");
        setManagerKeyword("");
      }
    });
  };
  useEffect(() => {
    load();
  }, [initialView, page, pageSize]);
  useEffect(() => {
    if (initialView === "customer-new") startCreate();
    else setOpen(false);
    setContacts(null);
    setDetailPageOpen(false);
    setSelectedRowKeys([]);
    setPage(1);
    setJumpPage("1");
  }, [initialView]);
  const rows = useMemo(() => {
    let list = [...allRows];
    const mine = (x: Customer) =>
      [profile.username, profile.display_name].includes(x.owner);
    if (["customer-recycle", "customer-dept-recycle", "customer-company-recycle"].includes(initialView)) {
      // Dedicated personal/department/company recycle APIs already apply scope and paging.
    }
    else if (["customer-mine", "customer-dept", "customer-company", "customer-public", "customer-shared", "customer-recent-contact", "customer-recent-update"].includes(initialView)) {
      // Dedicated APIs already apply the personal/department/company/public/shared/recent scope and paging.
    }
    else list = list.filter((x) => x.status !== "已回收");
    if (!isOriginalCustomerList && customerType)
      list = list.filter((x) => (x.data.customer_type || "客户") === customerType);
    if (!isOriginalCustomerList && managerKeyword.trim())
      list = list.filter((x) =>
        (x.data.customer_managers || [x.owner]).some((name) =>
          name.toLowerCase().includes(managerKeyword.trim().toLowerCase()),
        ),
      );
    return list;
  }, [allRows, initialView, profile, customerType, managerKeyword]);
  const startCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      serial_no: "",
      status: undefined,
      owner: profile.username || "admin",
      customer_managers: [profile.username || "admin"],
      department: profile.department || "上海分所",
      customer_type: "客户",
      level: "立案客户",
      is_shared: "否",
      is_assisted: "否",
      file_date: dayjs().format("YYYY-MM-DD"),
      customer_source: profile.display_name || profile.username || "管理者",
    });
    setOpen(true);
  };
  const startEdit = (r: Customer) => {
    setEditing(r);
    form.setFieldsValue({
      ...r,
      ...r.data,
      customer_managers: r.data.customer_managers?.length
        ? r.data.customer_managers
        : [r.owner],
    });
    setOpen(true);
  };
  const save = async () => {
    const v = await form.validateFields();
    const detailFields = [
      "contact",
      "phone",
      "level",
      "credit_code",
      "legal_representative",
      "registered_address",
      "invoice_title",
      "taxpayer_id",
      "invoice_address",
      "invoice_phone",
      "bank_name",
      "bank_account",
      "customer_type",
      "short_name",
      "fax",
      "legal_agent_id_no",
      "legal_agent_title",
      "customer_source",
      "is_shared",
      "is_assisted",
      "file_date",
      "province",
      "postal_code",
      "patent_customer_type",
      "fee_reduction",
      "industry",
      "output_value",
      "cooperation_status",
      "gb_classification",
      "website",
      "organization_nature",
      "organization_code",
      "registration_region",
      "registration_postal_code",
      "registered_capital",
      "registration_year",
    ];
    const details = Object.fromEntries(
      detailFields.map((key) => [key, v[key] || ""]),
    );
    if (editing) {
      details.level = editing.data.level || "";
      details.credit_code = editing.data.credit_code || "";
    }
    const managers = (v.customer_managers || []).filter((x: string) =>
      x.trim(),
    );
    const data = {
      ...(editing?.data || {}),
      ...details,
      customer_managers: managers,
    };
    const payload = {
      module: "customer",
      serial_no: v.serial_no,
      title: v.title,
      customer: v.title,
      status: v.status || "",
      owner: editing?.owner || profile.username || v.owner || "admin",
      department: v.department,
      description: v.description || "",
      data,
    };
    try {
      let response;
      if (editing) {
        const existingManagers = editing.data.customer_managers?.length
          ? editing.data.customer_managers
          : [editing.owner];
        const managerChanged = managers.length !== existingManagers.length || managers.some((manager: string, index: number) => manager !== existingManagers[index]);
        const { customer_managers: _customerManagers, ...editableData } = data;
        response = await api.patch(`/records/${editing.id}`, { ...payload, data: editableData });
        if (managerChanged) {
          response = await api.put(`/customers/${editing.id}/managers`, { managers });
        }
      } else response = await api.post("/customers", {
            serial_no: v.serial_no,
            title: v.title,
            status: v.status || "",
            owner: profile.username || v.owner || "admin",
            department: profile.department || v.department || "",
            description: v.description || "",
            customer_managers: managers,
            ...details,
          });
      message.success(editing ? "客户已更新" : "客户已创建");
      if (initialView === "customer-new") {
        setEditing(response.data);
        setContacts(response.data);
        await refreshDetail(response.data);
      } else {
        setOpen(false);
      }
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败");
    }
  };
  const startAssign = (customer: Customer) => {
    setAssigning(customer);
    assignForm.setFieldsValue({
      manager: customer.data.customer_managers?.[0] || customer.owner,
    });
  };
  const assignCustomer = async () => {
    if (!assigning) return;
    const values = await assignForm.validateFields();
    try {
      await api.put(`/customers/${assigning.id}/managers`, { managers: [values.manager] });
      message.success("客户分配成功");
      setAssigning(null);
      setSelectedRowKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户分配失败");
    }
  };
  const action = async (r: Customer, name: string) => {
    try {
      await api.post(`/customers/${r.id}/${name}`, { comment: "" });
      message.success(
        {
          claim: "客户领取成功",
          release: "已释放到公海",
          recycle: "已移入回收站",
          restore: "客户已恢复",
        }[name],
      );
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "操作失败");
    }
  };
  const share = async () => {
    if (!sharing) return;
    const v = await shareForm.validateFields();
    try {
      await api.post(`/customers/${sharing.id}/share`, {
        recipients: v.recipients,
        comment: v.comment || "",
      });
      message.success("客户共享成功");
      setSharing(null);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "共享失败");
    }
  };
  const submitLevelChange = async () => {
    if (!levelCustomer) return;
    const values = await levelForm.validateFields();
    try {
      await api.post(`/customers/${levelCustomer.id}/level-change`, values);
      message.success("客户分级调整已提交审批");
      setLevelCustomer(null);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户分级调整提交失败");
    }
  };
  const reviewLevelChange = async (customer: Customer, approved: boolean) => {
    try {
      await api.post(`/customers/${customer.id}/level-change/review`, { approved, comment: approved ? "同意客户分级调整" : "客户资料需补充后重新提交" });
      message.success(approved ? "客户分级调整已通过" : "客户分级调整已驳回");
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户分级审批失败");
    }
  };
  const submitKeyChange = async () => {
    if (!keyChangeCustomer) return;
    try {
      const values = await keyChangeForm.validateFields();
      await api.post(`/customers/${keyChangeCustomer.id}/key-change`, values);
      message.success("客户关键字段变更已提交审批");
      setKeyChangeCustomer(null);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户关键字段变更提交失败");
    }
  };
  const reviewKeyChange = async (customer: Customer, approved: boolean) => {
    try {
      await api.post(`/customers/${customer.id}/key-change/review`, { approved, comment: approved ? "同意客户关键字段变更" : "客户关键资料需核实" });
      message.success(approved ? "客户关键字段变更已通过" : "客户关键字段变更已驳回");
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户关键字段审批失败");
    }
  };
  const openPortal = async (customer: Customer) => {
    try {
      const response = await api.post(`/customers/${customer.id}/portal/open`, { comment: "从客户管理开通" });
      setPortalResult(response.data);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户服务端开通失败");
    }
  };
  const closePortal = async (customer: Customer) => {
    try {
      await api.post(`/customers/${customer.id}/portal/close`, { comment: "从客户管理停用" });
      message.success("客户服务端已停用");
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "客户服务端停用失败");
    }
  };
  const refreshDetail = async (target = contacts) => {
    if (!target) return;
    setDetailLoading(true);
    try {
      const [recordRes, fileRes] = await Promise.all([
        api.get("/records", {
          params: {
            module: "customer",
            keyword: target.serial_no,
            page_size: 10,
          },
        }),
        api.get("/attachments", { params: { record_id: target.id } }),
      ]);
      setContacts(
        recordRes.data.items.find((x: Customer) => x.id === target.id) ||
          target,
      );
      setAttachments((fileRes.data.items || []).filter((item: Attachment) => item.category !== "客户联系人照片"));
    } finally {
      setDetailLoading(false);
    }
  };
  const openDetail = async (r: Customer, tab = "contacts") => {
    setContacts(r);
    setDetailPageOpen(isReadOnlyCustomerList);
    setDetailTab(tab);
    setAttachments([]);
    await refreshDetail(r);
  };
  const openCustomerContracts = (customer: Customer) => {
    rememberCustomerRelationTarget({ id: customer.id, serial_no: customer.serial_no, title: customer.title, target: "contracts" });
    onNavigate?.("contract-company");
  };
  const openCustomerCivilCases = (customer: Customer) => {
    rememberCustomerRelationTarget({ id: customer.id, serial_no: customer.serial_no, title: customer.title, target: "civil-cases" });
    onNavigate?.("case-company-civil");
  };
  const addContact = async () => {
    if (!contacts) return;
    const v = await contactForm.validateFields();
    try {
      await api.post(`/customers/${contacts.id}/contacts`, v);
      message.success("联系人已添加");
      contactForm.resetFields();
      setNewEditor(null);
      await refreshDetail();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "联系人添加失败");
    }
  };
  const deleteContact = async (id: string) => {
    if (!contacts) return;
    try {
      await api.delete(`/customers/${contacts.id}/contacts/${id}`);
      message.success("联系人已删除");
      await refreshDetail();
      load();
    } catch {
      message.error("删除失败");
    }
  };
  const uploadContactPhoto = async (contact: Contact, option: any) => {
    if (!contacts) return;
    try {
      const data = new FormData(); data.append("file", option.file as Blob);
      await api.post(`/customers/${contacts.id}/contacts/${contact.id}/photo`, data, {headers:{"Content-Type":"multipart/form-data"}});
      option.onSuccess?.({}); message.success("联系人照片已上传"); await refreshDetail(); load();
    } catch (error: any) { option.onError?.(error); message.error(error?.response?.data?.detail || "联系人照片上传失败"); }
  };
  const viewContactPhoto = async (contact: Contact) => {
    if (!contacts || !contact.photo_attachment_id) return message.info("该联系人尚未上传照片");
    try { const response = await api.get(`/customers/${contacts.id}/contacts/${contact.id}/photo/download`, {responseType:"blob"}); setContactPhotoPreview({name:contact.photo_original_name || `${contact.name}的照片`,url:URL.createObjectURL(response.data)}); }
    catch (error:any) { message.error(error?.response?.data?.detail || "联系人照片加载失败"); }
  };
  const contactPhotoActions = (contact: Contact) => canManageCurrentCustomer ? <Space size={0}><Upload accept=".jpg,.jpeg,.png,.gif,.webp" showUploadList={false} customRequest={option=>void uploadContactPhoto(contact,option)}><Button type="link">{contact.photo_attachment_id?"替换照片":"上传照片"}</Button></Upload>{contact.photo_attachment_id&&<Button type="link" onClick={()=>void viewContactPhoto(contact)}>查看照片</Button>}</Space> : (contact.photo_attachment_id?<Button type="link" onClick={()=>void viewContactPhoto(contact)}>查看照片</Button>:null);
  const openContactEdit = (contact: Contact) => {
    contactEditForm.setFieldsValue({ ...contact });
    setEditingContact(contact);
  };
  const updateContact = async () => {
    if (!contacts || !editingContact) return;
    const values = await contactEditForm.validateFields();
    try {
      await api.put(`/customers/${contacts.id}/contacts/${editingContact.id}`, values);
      message.success("联系人已更新");
      setEditingContact(null);
      contactEditForm.resetFields();
      await refreshDetail();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "联系人更新失败");
    }
  };
  const addNote = async () => {
    if (!contacts) return;
    const v = await noteForm.validateFields();
    try {
      await api.post(`/customers/${contacts.id}/notes`, v);
      message.success("跟进记录已保存");
      noteForm.resetFields();
      setNewEditor(null);
      await refreshDetail();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "跟进记录保存失败");
    }
  };
  const deleteNote = async (id: string) => {
    if (!contacts) return;
    try {
      await api.delete(`/customers/${contacts.id}/notes/${id}`);
      message.success("跟进记录已删除");
      await refreshDetail();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const openNoteEdit = (note: Note) => {
    noteEditForm.setFieldsValue({ note_type: note.type, content: note.content });
    setEditingNote(note);
  };
  const updateNote = async () => {
    if (!contacts || !editingNote) return;
    const values = await noteEditForm.validateFields();
    try {
      await api.put(`/customers/${contacts.id}/notes/${editingNote.id}`, values);
      message.success("事项记录已更新");
      setEditingNote(null);
      noteEditForm.resetFields();
      await refreshDetail();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "事项记录更新失败");
    }
  };
  const uploadDocument = async () => {
    if (!contacts || !documentFile) return message.warning("请选择客户文档");
    const v = await documentForm.validateFields();
    const data = new FormData();
    data.append("file", documentFile);
    data.append("record_id", String(contacts.id));
    data.append("category", v.category || "客户资料");
    data.append("remark", v.remark || "");
    try {
      await api.post("/attachments", data);
      message.success("客户文档已上传");
      documentForm.resetFields();
      setDocumentFile(null);
      setNewEditor(null);
      if (documentFileRef.current) documentFileRef.current.value = "";
      await refreshDetail();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "上传失败");
    }
  };
  const downloadDocument = async (file: Attachment) => {
    try {
      const res = await api.get(`/attachments/${file.id}/download`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data),
        a = document.createElement("a");
      a.href = url;
      a.download = file.original_name;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("下载失败");
    }
  };
  const openNewEditor = (type: "contact" | "note" | "document") => {
    if ((!editing && !detailPageOpen) || !contacts) {
      Modal.info({
        title: "提示",
        content: "请先保存客户基本资料.",
        okText: <><span>确</span><span>定</span></>,
      });
      return;
    }
    if (type === "contact") contactForm.resetFields();
    if (type === "note") noteForm.setFieldsValue({ note_type: "跟进记录", content: "" });
    if (type === "document") documentForm.setFieldsValue({ category: "客户资料", remark: "" });
    setNewEditor(type);
  };
  const deleteDocument = async (id: number) => {
    try {
      await api.delete(`/attachments/${id}`);
      message.success("客户文档已删除");
      await refreshDetail();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const selected = rows.find((row) => selectedRowKeys.includes(row.id));
  const requireSingleSelected = () => {
    if (selectedRowKeys.length !== 1 || !selected) {
      message.info("请选择一条客户记录.");
      return null;
    }
    return selected;
  };
  const recycleCustomer = (row: Customer) => {
    Modal.confirm({
      title: `确认删除客户“${row.title}”？`,
      content: "删除后客户将进入回收站，可在回收站恢复或进入公海。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.post(`/customers/${row.id}/recycle`, {
            comment: `${initialView === "customer-company" ? "公司客户" : "客户"}：客户删除`,
          });
          message.success("客户已移入回收站");
          setSelectedRowKeys([]);
          await load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "删除失败");
        }
      },
    });
  };
  const originalActionItems =
    initialView === "customer-mine"
      ? [
          { key: "edit", label: "客户编辑" },
          { key: "delete", label: "客户删除" },
          { key: "contract", label: "新增合同" },
          { key: "level", label: "申请客户分级调整" },
          { key: "key-change", label: "申请关键字段变更" },
          { key: "share", label: "共享客户" },
          { key: "portal-open", label: "开通/重置客户服务端" },
          { key: "portal-close", label: "停用客户服务端" },
        ]
      : initialView === "customer-dept"
        ? [{ key: "assign", label: "分配客户" }]
      : initialView === "customer-company"
        ? [{ key: "assign", label: "分配客户" }]
        : ["customer-recycle", "customer-dept-recycle", "customer-company-recycle"].includes(initialView)
          ? [{ key: "restore", label: "客户恢复" }, { key: "release", label: "进入公海" }]
          : initialView === "customer-shared"
            ? []
        : initialView === "customer-public"
          ? [{ key: "claim", label: "拾回" }]
          : ["customer-recent-contact", "customer-recent-update"].includes(initialView)
            ? [{ key: "edit", label: "客户编辑" }]
            : [];
  const runOriginalAction = (key: string) => {
    const target = requireSingleSelected();
    if (!target) return;
    if (key === "delete") recycleCustomer(target);
    if (key === "edit") startEdit(target);
    if (key === "assign") startAssign(target);
    if (key === "contract") {
      sessionStorage.setItem("sunhold:contract-customer", JSON.stringify({
        id: target.id,
        name: target.title,
        serial_no: target.serial_no,
        at: Date.now(),
      }));
      onNavigate?.("contract-new");
    }
    if (key === "level") { levelForm.setFieldsValue({ level: target.data.level, comment: "" }); setLevelCustomer(target); }
    if (key === "key-change") { keyChangeForm.setFieldsValue({ title: target.title, credit_code: target.data.credit_code || "", comment: "" }); setKeyChangeCustomer(target); }
    if (key === "level-review") {
      if (target.data.level_change?.status !== "待审批") return message.warning("该客户没有待审批的分级调整");
      Modal.confirm({ title: `客户分级审批：${target.title}`, content: `${target.data.level_change.from_level || "—"} → ${target.data.level_change.to_level || "—"}`, okText: "通过", cancelText: "驳回", onOk: () => reviewLevelChange(target, true), onCancel: () => reviewLevelChange(target, false) });
    }
    if (key === "key-change-review") {
      if (target.data.key_change?.status !== "待审批") return message.warning("该客户没有待审批的关键字段变更");
      Modal.confirm({ title: `客户关键字段审批：${target.title}`, content: `客户名称：${target.data.key_change.before?.title || "—"} → ${target.data.key_change.after?.title || "—"}`, okText: "通过", cancelText: "驳回", onOk: () => reviewKeyChange(target, true), onCancel: () => reviewKeyChange(target, false) });
    }
    if (key === "portal-open") void openPortal(target);
    if (key === "portal-close") void closePortal(target);
    if (key === "claim") void action(target, "claim");
    if (key === "share") { shareForm.resetFields(); setSharing(target); }
    if (["release", "recycle", "restore"].includes(key)) void action(target, key);
  };
  const managerLocked = [
    "customer-mine",
    "customer-recycle",
    "customer-shared",
    "customer-recent-contact",
    "customer-recent-update",
  ].includes(initialView);
  const managerDisplay =
    ["customer-shared", "customer-recent-contact", "customer-recent-update"].includes(initialView)
      ? ""
      : isOriginalCustomerList && managerLocked
      ? profile.display_name || profile.username || "管理者"
      : managerKeyword;
  const amount = (value?: number) => Number(value || 0).toFixed(2);
  const displayDate = (value?: string) => {
    const parsed = dayjs(value);
    return value && parsed.isValid() ? parsed.format("YYYY-M-D") : "—";
  };
  const userLabel = (username: string) =>
    directory.find((user) => user.username === username)?.display_name || username;
  const canManageCurrentCustomer = Boolean(contacts && (
    profile.role === "admin" ||
    // admin 是不可降级的最高权限账号；历史账号资料的角色展示不应遮蔽其客户办理能力。
    profile.username === "admin" ||
    contacts.owner === profile.username ||
    (contacts.data.customer_managers || []).includes(profile.username) ||
    (profile.role === "manager" && contacts.department === profile.department)
  ));
  const columns = [
    {
      title: "客户编号",
      dataIndex: "serial_no",
      width: 235,
      align: "center" as const,
      ellipsis: true,
      render: (v: string, r: Customer) => (
        <button
          type="button"
          className="customer-cell-link"
          title={v}
          onClick={() => openDetail(r)}
        >
          <span>{v}</span>
        </button>
      ),
    },
    {
      title: "客户名称",
      dataIndex: "title",
      width: 294,
      align: "center" as const,
      ellipsis: true,
      render: (value: string, r: Customer) => (
        <button type="button" className="customer-cell-link" title={value} onClick={() => openDetail(r)}>
          <span>{value}</span>
        </button>
      ),
    },
    {
      title: "案源人",
      key: "source",
      width: 120,
      align: "center" as const,
      ellipsis: true,
      render: (_: unknown, r: Customer) => userLabel(r.data.source_person || r.owner),
    },
    {
      title: "客户管理人",
      key: "managers",
      width: 220,
      align: "center" as const,
      ellipsis: true,
      render: (_: unknown, r: Customer) => {
        const managers = (r.data.customer_managers || [r.owner]).map(userLabel).join(["customer-recycle", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-public", "customer-recent-update"].includes(initialView) ? "," : "、");
        return <span title={managers}>{managers}</span>;
      },
    },
    ...(initialView === "customer-shared" ? [{
      title: "共享接收人",
      key: "sharedRecipients",
      width: 180,
      align: "center" as const,
      ellipsis: true,
      render: (_: unknown, r: Customer) => {
        const recipients = (r.data.shared_with || []).map(userLabel).join("、") || "—";
        return <span title={recipients}>{recipients}</span>;
      },
    }] : []),
    {
      title: "建档日期",
      key: "fileDate",
      width: 115,
      align: "center" as const,
      render: (_: unknown, r: Customer) =>
        displayDate(r.data.file_date || r.created_at),
    },
    {
      title: "最后联系日期",
      key: "lastContact",
      width: 120,
      align: "center" as const,
      render: (_: unknown, r: Customer) => displayDate(r.data.last_contact_at),
    },
    {
      title: "最后修改日期",
      key: "lastModified",
      width: 120,
      align: "center" as const,
      render: (_: unknown, r: Customer) =>
        displayDate(initialView === "customer-recent-update" ? r.updated_at : r.data.last_modified_date || r.updated_at),
    },
    {
      title: "联系次数",
      key: "contactCount",
      width: 118,
      align: "center" as const,
      render: (_: unknown, r: Customer) =>
        r.data.contact_count ?? r.data.notes?.length ?? 0,
    },
    {
      title: "合同数量",
      key: "contractCount",
      width: 118,
      align: "center" as const,
      render: (_: unknown, r: Customer) => (
        <Button
          type="link"
          className="customer-cell-link"
          onClick={() => openCustomerContracts(r)}
        >
          {r.data.contract_count ?? 0}
        </Button>
      ),
    },
    {
      title: "民事案件数",
      key: "caseCount",
      width: 120,
      align: "center" as const,
      render: (_: unknown, r: Customer) => (
        <Button
          type="link"
          className="customer-cell-link"
          onClick={() => openCustomerCivilCases(r)}
        >
          {r.data.civil_case_count ?? 0}
        </Button>
      ),
    },
    {
      title: (
        <span>
          代理费
          <br />
          待收金额
        </span>
      ),
      key: "agencyFee",
      width: 117,
      align: "center" as const,
      render: (_: unknown, r: Customer) => amount(r.data.agency_fee_due),
    },
    {
      title: (
        <span>
          官费
          <br />
          未到金额
        </span>
      ),
      key: "officialFee",
      width: 118,
      align: "center" as const,
      render: (_: unknown, r: Customer) =>
        amount(r.data.official_fee_unreceived),
    },
    {
      title: "客户状态",
      dataIndex: "status",
      width: 118,
      align: "center" as const,
      render: (v: string) => {
        const label = ["customer-recycle", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-recent-update"].includes(initialView) && v === "已回收" ? "已删除" : v;
        return <span className={`customer-status customer-status-${v}`}>{label}</span>;
      },
    },
  ];
  const customerPageCount = Math.max(1, Math.ceil(total / pageSize));
  const customerPageNumbers = Array.from(
    { length: Math.min(5, customerPageCount) },
    (_, index) => {
      const start = Math.min(
        Math.max(1, page - 2),
        Math.max(1, customerPageCount - 4),
      );
      return start + index;
    },
  );
  const goToCustomerPage = (target: number) => {
    const next = Math.min(Math.max(1, target), customerPageCount);
    setPage(next);
    setJumpPage(String(next));
    setSelectedRowKeys([]);
  };
  return (
    <>
      {isReadOnlyCustomerList && detailPageOpen && contacts && (
        <Card className="customer-view-page" loading={detailLoading}>
          <div className="customer-view-tabbar">
            <span>{initialView === "customer-company-recycle" ? "公司回收站" : initialView === "customer-recent-update" ? "最近更新的客户" : initialView === "customer-recent-contact" ? "最近联系的客户" : initialView === "customer-shared" ? "我的共享客户" : initialView === "customer-public" ? "公海客户" : initialView === "customer-company" ? "公司客户" : initialView === "customer-dept" ? "部门客户" : initialView === "customer-dept-recycle" ? "部门回收站" : initialView === "customer-recycle" ? "个人回收站" : "我的客户"}</span>
            <Button type="text" aria-label="关闭客户查看" onClick={() => { setDetailPageOpen(false); setContacts(null); }}>×</Button>
          </div>
          <section>
            <h3>基本信息</h3>
            <div className="customer-view-fields customer-view-fields-four">
              <label><span><i>*</i>客户名称</span><Input disabled value={contacts.title} /></label>
              <label><span>客户编码</span><Input disabled value={contacts.serial_no} placeholder="自动生成" /></label>
              <label><span>客户状态</span><Select disabled value={["潜在","目标","立项","关怀","签约","谈判","价值"].includes(contacts.status) ? contacts.status : "请选择"} options={["请选择","潜在","目标","立项","关怀","签约","谈判","价值"].map(value=>({value,label:value}))} /></label>
              <label><span>客户类型</span><Select disabled value={contacts.data.customer_type || "客户"} options={customerTypeOptions} /></label>
              <label><span>注册地址</span><Input disabled value={contacts.data.registered_address || ""} /></label>
              <label><span>电话</span><Input disabled value={contacts.data.phone || ""} /></label>
              <label><span>传 真</span><Input disabled value={contacts.data.fax || ""} /></label>
            </div>
          </section>
          <section>
            <h3>法人信息</h3>
            <div className="customer-view-fields customer-view-fields-four">
              <label><span>法人姓名</span><Input disabled value={contacts.data.legal_representative || ""} /></label>
              <label><span>身份证号</span><Input disabled value={contacts.data.legal_agent_id_no || ""} /></label>
              <label><span>职务</span><Input disabled value={contacts.data.legal_agent_title || ""} /></label>
            </div>
          </section>
          <section>
            <h3>开票信息</h3>
            <div className="customer-view-fields customer-view-fields-four">
              <label><span>开票地址</span><Input disabled value={contacts.data.invoice_address || ""} /></label>
              <label><span>统一社会信用代码</span><Input disabled value={contacts.data.credit_code || contacts.data.taxpayer_id || ""} /></label>
              <label><span>开 户 行</span><Input disabled value={contacts.data.bank_name || ""} /></label>
              <label><span>帐 号</span><Input disabled value={contacts.data.bank_account || ""} /></label>
            </div>
          </section>
          <section>
            <h3>控制信息</h3>
            <div className="customer-view-fields customer-view-fields-five">
              <label><span>建档日期</span><Input disabled value={contacts.data.file_date || displayDate(contacts.created_at)} /></label>
              <label><span>客户来源</span><Input disabled value={contacts.data.customer_source || userLabel(contacts.owner)} /></label>
              <label><span>是否共享</span><Select disabled value={contacts.data.is_shared || "否"} options={["是","否"].map(value=>({value,label:value}))} /></label>
              <label><span>客户等级</span><Select disabled value={contacts.data.level || "立案客户"} options={["立案客户","高级客户","中级客户","低级客户"].map(value=>({value,label:value}))} /></label>
              <label><span>上海市资助信息</span><Select disabled value={contacts.data.is_assisted || "否"} options={["是","否"].map(value=>({value,label:value}))} /></label>
              <label><span>客戶管理人</span><Input disabled value={(contacts.data.customer_managers || [contacts.owner]).map(userLabel).join("、")} /></label>
            </div>
          </section>
          <Tabs
            className="customer-view-tabs"
            activeKey={detailTab}
            onChange={setDetailTab}
            items={[
              {
                key: "contacts",
                label: "联系人",
                children: <Table className="customer-contact-table" rowKey="id" size="small" tableLayout="fixed" pagination={false} dataSource={contacts.data.contacts || []} scroll={{ x: 1460 }} locale={{emptyText:"没有查询到联系人"}} columns={[
                  {title:"序号",render:(_:unknown,_row:Contact,index:number)=>index+1,width:55},{title:"姓名",dataIndex:"name"},{title:"职务",dataIndex:"position"},{title:"项目角色",dataIndex:"project_role"},{title:"办公电话",dataIndex:"office_phone"},{title:"移动电话",dataIndex:"phone"},{title:"IM",dataIndex:"im_account"},{title:"邮箱",dataIndex:"email"},{title:"是否接收邮件",render:(_:unknown,row:Contact)=>row.email?"是":"否"},{title:"是否需要联系",render:(_:unknown,row:Contact)=>row.contact_status!=="停止联系"?"是":"否"},{title:"是否有效",render:(_:unknown,row:Contact)=>row.is_valid!==false?"是":"否"},{title:"照片",width:150,render:(_:unknown,row:Contact)=>contactPhotoActions(row)},{title:"操作",render:(_:unknown,row:Contact)=>canManageCurrentCustomer?<Button type="link" onClick={()=>openContactEdit(row)}>编辑</Button>:null},
                ]} />,
              },
              {
                key: "notes",
                label: "事项记录",
                children: <Table rowKey="id" size="small" pagination={false} dataSource={contacts.data.notes || []} scroll={{ x: 720 }} locale={{emptyText: ["customer-shared", "customer-company"].includes(initialView) ? "没有查询到事项记录，可以去 新建" : "没有查询到事项记录"}} columns={[
                  {title:"序号",render:(_:unknown,_row:Note,index:number)=>index+1,width:55},{title:"内容",dataIndex:"content"},{title:"操作人",dataIndex:"operator"},{title:"操作日期",dataIndex:"created_at"},{title:"操作",render:()=>null},
                ]} />,
              },
              {
                key: "documents",
                label: "客户文档",
                children: <Table rowKey="id" size="small" pagination={false} dataSource={attachments} scroll={{ x: 720 }} locale={{emptyText: initialView === "customer-shared" ? "没有查询到客户文件，可以去 上传客户文件" : "没有查询到客户文件"}} columns={[
                  {title:"序号",render:(_:unknown,_row:Attachment,index:number)=>index+1,width:55},{title:"上传人",dataIndex:"uploader"},{title:"文件名称",dataIndex:"original_name"},{title:"文档日期",dataIndex:"created_at"},{title:"查看",render:(_:unknown,row:Attachment)=><Button type="link" onClick={()=>downloadDocument(row)}>查看</Button>},{title:"操作",render:()=>null},
                ]} />,
              },
            ]}
          />
          {canManageCurrentCustomer && detailTab === "notes" && (
            <div className="customer-detail-actions">
              <Button type="link" onClick={() => openNewEditor("note")}>新建事项记录</Button>
              {(contacts.data.notes || []).map((note) => (
                <Space key={note.id} size={0}>
                  <Button type="link" onClick={() => openNoteEdit(note)}>编辑事项记录</Button>
                  <Popconfirm title="删除这条记录？" onConfirm={() => deleteNote(note.id)}>
                    <Button type="link" danger>删除事项记录</Button>
                  </Popconfirm>
                </Space>
              ))}
            </div>
          )}
          {canManageCurrentCustomer && detailTab === "documents" && (
            <div className="customer-detail-actions">
              <Button type="link" onClick={() => openNewEditor("document")}>上传客户文件</Button>
              {attachments.map((attachment) => (
                <Popconfirm key={attachment.id} title="删除客户文档？" onConfirm={() => deleteDocument(attachment.id)}>
                  <Button type="link" danger>删除客户文档</Button>
                </Popconfirm>
              ))}
            </div>
          )}
        </Card>
      )}
      {initialView !== "customer-new" && !(isReadOnlyCustomerList && detailPageOpen) && (
      <Card className="panel customer-list-panel" title="客户列表">
        <div className="customer-query">
          <label>客户名称</label>
          <Input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={queryCustomerList}
            allowClear
          />
          <label>客户/当事人</label>
          <Select
            value={customerType}
            onChange={setCustomerType}
            options={customerTypeOptions}
          />
          <label>客户管理人</label>
          <Input
            disabled={managerLocked}
            value={managerDisplay}
            onChange={(event) => setManagerKeyword(event.target.value)}
          />
          <Button type="primary" icon={<SearchOutlined />} onClick={queryCustomerList}>
            查询
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => {
            const resetCustomerType = customerTypeOptions[0]?.value || "客户";
            setKeyword("");
            setCustomerType(resetCustomerType);
            setManagerKeyword("");
            setSelectedRowKeys([]);
            setPage(1);
            setJumpPage("1");
            void load({ keyword: "", customerType: resetCustomerType, managerKeyword: "", page: 1 });
          }}>
            重置
          </Button>
        </div>
        <Table
          className="customer-original-table"
          rowKey="id"
          size="small"
          loading={loading}
          columns={columns}
          dataSource={rows}
          tableLayout="fixed"
          rowSelection={{
            columnWidth: 44,
            selectedRowKeys,
            onChange: setSelectedRowKeys,
          }}
          scroll={{ x: 2100 }}
          pagination={isOriginalCustomerList ? false : {
            pageSize: 15,
            showSizeChanger: true,
            pageSizeOptions: [15, 30, 50],
            showTotal: (count) => `共 ${count} 条`,
          }}
          locale={{ emptyText: "没有查询到符合条件的记录 。" }}
          rowClassName={(record) => selectedRowKeys.includes(record.id) ? "customer-original-selected" : ""}
          components={isOriginalCustomerList && rows.length > 0 ? {
            body: {
              wrapper: (props: any) => {
                const { children, ...rest } = props;
                return <tbody {...rest}>
                  <tr className="customer-total-row customer-total-row-top">
                    <td colSpan={11} />
                    <td className="ant-table-cell customer-amount-cell">{amount(listSummary.agency_fee_due)}</td>
                    <td className="ant-table-cell customer-amount-cell">{amount(listSummary.official_fee_unreceived)}</td>
                    <td />
                  </tr>
                  {children}
                </tbody>;
              },
            },
          } : undefined}
          summary={["customer-recycle", "customer-dept", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-public", "customer-shared", "customer-recent-contact", "customer-recent-update"].includes(initialView) && rows.length === 0 ? undefined : (data) => (
            <Table.Summary>
              <Table.Summary.Row className="customer-total-row">
                <Table.Summary.Cell index={0} colSpan={11} />
                <Table.Summary.Cell index={11} align="center">
                  {amount(isOriginalCustomerList ? listSummary.agency_fee_due : data.reduce((sum, row) => sum + (row.data.agency_fee_due || 0), 0))}
                </Table.Summary.Cell>
                <Table.Summary.Cell index={12} align="center">
                  {amount(isOriginalCustomerList ? listSummary.official_fee_unreceived : data.reduce((sum, row) => sum + (row.data.official_fee_unreceived || 0), 0))}
                </Table.Summary.Cell>
                <Table.Summary.Cell index={13} />
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
        {(!["customer-recycle", "customer-dept", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-public", "customer-shared", "customer-recent-contact", "customer-recent-update"].includes(initialView) || rows.length > 0) && <div className="customer-grid-footer">
          <div className="customer-footer-actions">
            <Checkbox
              checked={rows.length > 0 && selectedRowKeys.length === rows.length}
              indeterminate={selectedRowKeys.length > 0 && selectedRowKeys.length < rows.length}
              onChange={(event) => setSelectedRowKeys(event.target.checked ? rows.map((row) => row.id) : [])}
            />
            {isReadOnlyCustomerList && (
              <Button onClick={() => {
                const target = requireSingleSelected();
                if (target) void openDetail(target);
              }}>客户查看</Button>
            )}
            {originalActionItems.length > 0 && (
              <Dropdown
                trigger={["click"]}
                menu={{
                  items: originalActionItems,
                  onClick: ({ key }) => runOriginalAction(key),
                }}
              >
                <Button>更多操作</Button>
              </Dropdown>
            )}
          </div>
          {isOriginalCustomerList && <div className="customer-original-pagination">
            <span>共有{total}条，每页显示：</span>
            <Select
              value={pageSize}
              options={[10, 15, 20, 50, 100, 200].map((value) => ({ value, label: String(value) }))}
              onChange={(value) => { setPageSize(value); setPage(1); setJumpPage("1"); setSelectedRowKeys([]); }}
            />
            <span>条</span>
            <Button disabled={page === 1} onClick={() => goToCustomerPage(1)}>«</Button>
            <Button disabled={page === 1} onClick={() => goToCustomerPage(page - 1)}>‹</Button>
            {customerPageNumbers.map((number) => <Button key={number} type={number === page ? "primary" : "default"} onClick={() => goToCustomerPage(number)}>{number}</Button>)}
            <Button disabled={page === customerPageCount} onClick={() => goToCustomerPage(page + 1)}>›</Button>
            {["customer-recycle", "customer-dept", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-recent-update"].includes(initialView) && (
              <Button disabled={page === customerPageCount} onClick={() => goToCustomerPage(customerPageCount)}>»</Button>
            )}
            <Input value={jumpPage} onChange={(event) => setJumpPage(event.target.value.replace(/\D/g, ""))} onPressEnter={() => goToCustomerPage(Number(jumpPage || page))} />
            <Button onClick={() => goToCustomerPage(Number(jumpPage || page))}>GO</Button>
          </div>}
        </div>}
      </Card>
      )}
      {initialView === "customer-new" && (
        <Card className="customer-create-page">
          <Form form={form} layout="horizontal" className="customer-create-form">
            <section>
              <h3>基本信息</h3>
              <div className="customer-create-grid">
                <Form.Item label="客户名称" name="title" rules={[{ required: true }]}><Input /></Form.Item>
                <Form.Item label="客户编码" name="serial_no"><Input disabled placeholder="自动生成" /></Form.Item>
                <Form.Item label="客户状态" name="status"><Select allowClear placeholder="请选择" options={["潜在","目标","立项","关怀","签约","谈判","价值"].map(value=>({value,label:value}))} /></Form.Item>
                <Form.Item label="客户类型" name="customer_type"><Select options={customerTypeOptions} /></Form.Item>
                <Form.Item label="注册地址" name="registered_address"><Input /></Form.Item>
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
                <Form.Item label="客户来源" name="customer_source"><AutoComplete options={directoryOptions} placeholder="输入或选择人员" /></Form.Item>
                <Form.Item label="是否共享" name="is_shared"><Select options={["是","否"].map(value=>({value,label:value}))} /></Form.Item>
                <Form.Item label="客户等级" name="level"><Select options={["立案客户","高级客户","中级客户","低级客户"].map(value=>({value,label:value}))} /></Form.Item>
                <Form.Item label="上海市资助信息" name="is_assisted"><Select options={["是","否"].map(value=>({value,label:value}))} /></Form.Item>
                <Form.Item label="客户管理人" name="customer_managers" rules={[{required:true,message:"至少设置一名客户管理人"}]}>
                  <Select mode="multiple" showSearch optionFilterProp="label" options={directoryOptions} />
                </Form.Item>
                <Form.Item label="客户联系人账号" name="contact"><AutoComplete options={directoryOptions} placeholder="输入姓名或账号，选择系统员工" /></Form.Item>
              </div>
            </section>
          </Form>
          <Tabs
            className="customer-create-tabs"
            tabBarExtraContent={<Button type="primary" onClick={save}><span>保</span><span>存</span></Button>}
            items={[
              {
                key:"contacts",
                label:"联系人",
                children:<>
                  <Table className="customer-create-related-table customer-contact-table" rowKey="id" size="small" tableLayout="fixed" pagination={false} dataSource={contacts?.data.contacts || []} scroll={{ x: 1460 }} locale={{emptyText:<span>没有查询到联系人，可以去 <Button type="link" onClick={()=>openNewEditor("contact")}>新建联系人</Button></span>}} columns={[
                    {title:"序号",render:(_:unknown,_r:Contact,index:number)=>index+1,width:55},
                    {title:"姓名",dataIndex:"name"},{title:"职务",dataIndex:"position"},{title:"项目角色",dataIndex:"project_role"},{title:"办公电话",dataIndex:"office_phone"},{title:"移动电话",dataIndex:"phone"},{title:"IM",dataIndex:"im_account"},{title:"邮箱",dataIndex:"email"},{title:"是否接收邮件",render:(_:unknown,row:Contact)=>row.email?"是":"否"},{title:"是否需要联系",render:(_:unknown,row:Contact)=>row.contact_status!=="停止联系"?"是":"否"},{title:"是否有效",dataIndex:"is_valid",render:(value:boolean)=>value!==false?"是":"否"},
                    {title:"照片",width:150,render:(_:unknown,row:Contact)=>contactPhotoActions(row)},{title:"操作",render:(_:unknown,row:Contact)=>canManageCurrentCustomer?<Space size={0}><Button type="link" onClick={()=>openContactEdit(row)}>编辑</Button><Popconfirm title="删除联系人？" onConfirm={()=>deleteContact(row.id)}><Button type="link" danger>删除</Button></Popconfirm></Space>:null}
                  ]} />
                  {(contacts?.data.contacts?.length || 0) > 0 && <Button className="customer-create-related-link" type="link" onClick={()=>openNewEditor("contact")}>新建联系人</Button>}
                </>
              },
              {
                key:"notes",
                label:"事项记录",
                children:<>
                  <Table className="customer-create-related-table" rowKey="id" size="small" pagination={false} dataSource={contacts?.data.notes || []} scroll={{ x: 720 }} locale={{emptyText:<span>没有查询到事项记录，可以去 <Button type="link" onClick={()=>openNewEditor("note")}>新建</Button></span>}} columns={[
                    {title:"序号",render:(_:unknown,_r:Note,index:number)=>index+1,width:55},{title:"内容",dataIndex:"content"},{title:"操作人",dataIndex:"operator",width:110},{title:"操作日期",dataIndex:"created_at",width:170},
                    {title:"操作",render:(_:unknown,row:Note)=><Popconfirm title="删除这条记录？" onConfirm={()=>deleteNote(row.id)}><Button type="link" danger>删除</Button></Popconfirm>}
                  ]} />
                  {(contacts?.data.notes?.length || 0) > 0 && <Button className="customer-create-related-link" type="link" onClick={()=>openNewEditor("note")}>新建</Button>}
                </>
              },
              {
                key:"documents",
                label:"客户文档",
                children:<>
                  <Table className="customer-create-related-table" rowKey="id" size="small" pagination={false} dataSource={attachments} scroll={{ x: 720 }} locale={{emptyText:<span>没有查询到客户文件，可以去 <Button type="link" onClick={()=>openNewEditor("document")}>上传客户文件</Button></span>}} columns={[
                    {title:"序号",render:(_:unknown,_r:Attachment,index:number)=>index+1,width:55},{title:"上传人",dataIndex:"uploader",width:110},{title:"文件名称",dataIndex:"original_name"},{title:"文档日期",dataIndex:"created_at",width:170},{title:"查看",render:(_:unknown,row:Attachment)=><Button type="link" onClick={()=>downloadDocument(row)}>查看</Button>},
                    {title:"操作",render:(_:unknown,row:Attachment)=><Popconfirm title="删除客户文档？" onConfirm={()=>deleteDocument(row.id)}><Button type="link" danger>删除</Button></Popconfirm>}
                  ]} />
                  {attachments.length > 0 && <Button className="customer-create-related-link" type="link" onClick={()=>openNewEditor("document")}>上传客户文件</Button>}
                </>
              }
            ]}
          />
        </Card>
      )}
      <Modal open={Boolean(contactPhotoPreview)} title={contactPhotoPreview?.name || "联系人照片"} footer={null} onCancel={()=>{if(contactPhotoPreview)URL.revokeObjectURL(contactPhotoPreview.url);setContactPhotoPreview(null);}} destroyOnHidden><img src={contactPhotoPreview?.url} alt={contactPhotoPreview?.name || "联系人照片"} style={{display:"block",maxWidth:"100%",maxHeight:560,margin:"0 auto"}} /></Modal>
      <Modal open={newEditor === "contact"} title="新建联系人" okText="保存" cancelText="取消" onOk={addContact} onCancel={()=>setNewEditor(null)} destroyOnHidden>
        <Form form={contactForm} layout="vertical">
          <div className="form-grid">
            <Form.Item name="name" label="姓名" rules={[{required:true}]}><Input /></Form.Item>
            <Form.Item name="position" label="职务"><Input /></Form.Item>
            <Form.Item name="project_role" label="项目角色"><Input /></Form.Item>
            <Form.Item name="office_phone" label="办公电话"><Input /></Form.Item>
            <Form.Item name="phone" label="移动电话"><Input /></Form.Item>
            <Form.Item name="im_account" label="IM"><Input /></Form.Item>
            <Form.Item name="email" label="邮箱"><Input /></Form.Item>
            <Form.Item name="contact_status" label="联系状态" initialValue="正常联系"><Select options={["正常联系","暂缓联系","停止联系"].map(value=>({value,label:value}))} /></Form.Item>
          </div>
          <Form.Item name="is_valid" valuePropName="checked" initialValue><Checkbox>是否有效</Checkbox></Form.Item>
        </Form>
      </Modal>
      <Modal open={Boolean(editingContact)} title={`编辑联系人：${editingContact?.name || ""}`} okText="保存" cancelText="取消" onOk={updateContact} onCancel={()=>{setEditingContact(null);contactEditForm.resetFields();}} destroyOnHidden>
        <Form form={contactEditForm} layout="vertical">
          <div className="form-grid">
            <Form.Item name="name" label="姓名" rules={[{required:true,message:"请输入联系人姓名"}]}><Input /></Form.Item>
            <Form.Item name="position" label="职务"><Input /></Form.Item>
            <Form.Item name="project_role" label="项目角色"><Input /></Form.Item>
            <Form.Item name="office_phone" label="办公电话"><Input /></Form.Item>
            <Form.Item name="phone" label="移动电话"><Input /></Form.Item>
            <Form.Item name="im_account" label="IM"><Input /></Form.Item>
            <Form.Item name="email" label="邮箱"><Input /></Form.Item>
            <Form.Item name="contact_status" label="联系状态"><Select options={["正常联系","暂缓联系","停止联系"].map(value=>({value,label:value}))} /></Form.Item>
          </div>
          <Form.Item name="is_valid" valuePropName="checked"><Checkbox>是否有效</Checkbox></Form.Item>
          <Form.Item name="is_primary" valuePropName="checked"><Checkbox>设为主要联系人</Checkbox></Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={3} /></Form.Item>
          <Alert type="info" showIcon title="保存会直接更新原联系人记录，不会删除重建，并写入客户审计日志。" />
        </Form>
      </Modal>
      <Modal open={newEditor === "note"} title="新建事项记录" okText="保存" cancelText="取消" onOk={addNote} onCancel={()=>setNewEditor(null)} destroyOnHidden>
        <Form form={noteForm} layout="vertical" initialValues={{note_type:"跟进记录"}}>
          <Form.Item name="note_type" label="记录类型"><Select options={["跟进记录","会议纪要","电话沟通","风险提示","客户备注"].map(value=>({value,label:value}))} /></Form.Item>
          <Form.Item name="content" label="内容" rules={[{required:true}]}><Input.TextArea rows={4} /></Form.Item>
        </Form>
      </Modal>
      <Modal open={Boolean(editingNote)} title="编辑事项记录" okText="保存修改" cancelText="取消" onOk={updateNote} onCancel={()=>{setEditingNote(null);noteEditForm.resetFields();}} destroyOnHidden>
        <Form form={noteEditForm} layout="vertical">
          <Form.Item name="note_type" label="记录类型"><Select options={["跟进记录","会议纪要","电话沟通","风险提示","客户备注"].map(value=>({value,label:value}))} /></Form.Item>
          <Form.Item name="content" label="内容" rules={[{required:true}]}><Input.TextArea rows={4} /></Form.Item>
          <Alert type="info" showIcon message="保存将更新当前事项记录，保留原始创建人和创建时间。" />
        </Form>
      </Modal>
      <Modal open={newEditor === "document"} title="上传客户文件" okText="上传" cancelText="取消" onOk={uploadDocument} onCancel={()=>setNewEditor(null)} destroyOnHidden>
        <Form form={documentForm} layout="vertical" initialValues={{category:"客户资料"}}>
          <Form.Item name="category" label="文档类别"><Select options={["客户资料","工商材料","授权委托","沟通记录","开票资料","其他材料"].map(value=>({value,label:value}))} /></Form.Item>
          <Form.Item label="选择文件"><input ref={documentFileRef} type="file" onChange={event=>setDocumentFile(event.target.files?.[0] || null)} /></Form.Item>
          <Form.Item name="remark" label="说明"><Input /></Form.Item>
        </Form>
      </Modal>
      <Modal
        width={820}
        open={open && initialView !== "customer-new"}
        title={editing ? "编辑客户" : "新增客户"}
        okText="保存"
        cancelText="取消"
        onOk={save}
        onCancel={() => setOpen(false)}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <div className="form-grid">
            <div className="span-2">
              <b>基础与联系资料</b>
            </div>
            <Form.Item
              label="客户编号"
              name="serial_no"
              rules={[{ required: true }]}
            >
              <Input disabled={Boolean(editing)} />
            </Form.Item>
            <Form.Item
              label="客户名称"
              name="title"
              rules={[{ required: true }]}
            >
              <Input disabled={Boolean(editing)} />
            </Form.Item>
            <Form.Item label="客户状态" name="status">
              <Select
                options={["潜在", "目标", "立项", "关怀", "签约", "谈判", "价值"].map((v) => ({
                  value: v,
                  label: v,
                }))}
              />
            </Form.Item>
            <Form.Item label="客户类型" name="customer_type">
              <Select options={customerTypeOptions} />
            </Form.Item>
            <Form.Item label="客户等级" name="level">
              <Select
                disabled={Boolean(editing)}
                options={["潜在客户", "目标客户", "签约客户", "立案客户", "高级客户", "中级客户", "低级客户"].map((v) => ({
                  value: v,
                  label: v,
                }))}
              />
            </Form.Item>
            <Form.Item
              className="span-2"
              label="客户管理人"
              name="customer_managers"
              rules={[{ required: true, message: "至少设置一名客户管理人" }]}
            >
              <Select mode="multiple" showSearch optionFilterProp="label" placeholder="选择客户管理人，可设置多人" options={directoryOptions} />
            </Form.Item>
            <Form.Item label="所属部门" name="department">
              <Input />
            </Form.Item>
            <Form.Item label="客户联系人账号" name="contact">
              <AutoComplete options={directoryOptions} placeholder="输入姓名或账号，选择系统员工" />
            </Form.Item>
            <Form.Item label="联系电话" name="phone">
              <Input />
            </Form.Item>
            <Form.Item label="客户简称" name="short_name"><Input /></Form.Item>
            <Form.Item label="传真" name="fax"><Input /></Form.Item>
            <div className="span-2">
              <b>工商与法务主体资料</b>
            </div>
            <Form.Item label="统一社会信用代码" name="credit_code">
              <Input disabled={Boolean(editing)} />
            </Form.Item>
            <Form.Item label="法定代表人" name="legal_representative">
              <Input />
            </Form.Item>
            <Form.Item label="法人身份证号" name="legal_agent_id_no"><Input /></Form.Item>
            <Form.Item label="法人职务" name="legal_agent_title"><Input /></Form.Item>
            <Form.Item
              className="span-2"
              label="注册地址"
              name="registered_address"
            >
              <Input />
            </Form.Item>
            <div className="span-2">
              <b>开票与银行资料</b>
            </div>
            <Form.Item label="开票地址" name="invoice_address"><Input /></Form.Item>
            <Form.Item label="开户银行" name="bank_name">
              <Input />
            </Form.Item>
            <Form.Item label="银行账号" name="bank_account">
              <Input />
            </Form.Item>
            <div className="span-2"><b>控制信息</b></div>
            <Form.Item label="客户来源" name="customer_source"><AutoComplete options={directoryOptions} placeholder="输入或选择人员" /></Form.Item>
            <Form.Item label="建档日期" name="file_date"><Input type="date" /></Form.Item>
            <Form.Item label="是否共享" name="is_shared"><Select options={["是", "否"].map((value) => ({ value, label: value }))} /></Form.Item>
            <Form.Item label="上海市资助信息" name="is_assisted"><Select options={["是", "否"].map((value) => ({ value, label: value }))} /></Form.Item>
            <Form.Item className="span-2" label="备注" name="description">
              <Input.TextArea rows={2} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
      <Modal
        open={Boolean(levelCustomer)}
        title={`申请客户分级调整：${levelCustomer?.title || ""}`}
        okText="提交审批"
        cancelText="取消"
        onOk={submitLevelChange}
        onCancel={() => setLevelCustomer(null)}
      >
        <Form form={levelForm} layout="vertical">
          <Alert style={{ marginBottom: 12 }} type="info" showIcon message={`当前等级：${levelCustomer?.data.level || "未设置"}`} />
          <Form.Item label="调整为" name="level" rules={[{ required: true, message: "请选择目标等级" }]}>
            <Select options={["潜在客户", "目标客户", "签约客户", "立案客户", "高级客户", "中级客户", "低级客户"].map((value) => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item label="调整说明" name="comment"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(keyChangeCustomer)}
        title={`申请客户关键字段变更：${keyChangeCustomer?.title || ""}`}
        okText="提交审批"
        cancelText="取消"
        onOk={submitKeyChange}
        onCancel={() => setKeyChangeCustomer(null)}
      >
        <Form form={keyChangeForm} layout="vertical">
          <Form.Item label="客户名称" name="title" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="统一社会信用代码" name="credit_code"><Input /></Form.Item>
          <Form.Item label="变更原因" name="comment" rules={[{ required: true, min: 2 }]}><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(portalResult)}
        title="客户服务端已开通"
        footer={<Button type="primary" onClick={() => setPortalResult(null)}>我已安全保存</Button>}
        closable={false}
      >
        <Alert type="warning" showIcon message="请将服务账号和一次性激活码一并交付客户；客户首次登录时需用二者设置密码。激活码仅本次显示，再次开通会重置旧激活码。" />
        <p style={{ marginTop: 16 }}><strong>服务账号：</strong>{portalResult?.account}</p>
        <p><strong>一次性激活码：</strong>{portalResult?.activation_code}</p>
      </Modal>
      <Modal
        open={Boolean(assigning)}
        title="客户分配"
        okText="确定"
        cancelText="取消"
        onOk={assignCustomer}
        onCancel={() => setAssigning(null)}
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
              value={(assigning?.data.customer_managers || (assigning ? [assigning.owner] : []))
                .map(userLabel)
                .join(",")}
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
              options={directory.map((user) => ({
                value: user.username,
                label: `${user.display_name || user.username}${user.department ? `（${user.department}）` : ""}`,
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(sharing)}
        title={`共享客户：${sharing?.title || ""}`}
        okText="确认共享"
        onOk={share}
        onCancel={() => setSharing(null)}
      >
        <Form form={shareForm} layout="vertical">
          <Form.Item
            label="共享人员"
            name="recipients"
            rules={[{ required: true }]}
          >
            <Select
              mode="tags"
              tokenSeparators={[",", "，"]}
              placeholder="输入账号后回车，可添加多人"
            />
          </Form.Item>
          <Form.Item label="共享说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Drawer
        size={720}
        loading={detailLoading}
        open={Boolean(contacts) && initialView !== "customer-new" && !detailPageOpen}
        title={`客户详情：${contacts?.title || ""}`}
        onClose={() => setContacts(null)}
      >
        <Tabs
          activeKey={detailTab}
          onChange={setDetailTab}
          items={[
            {
              key: "contacts",
              label: `联系人（${contacts?.data.contacts?.length || 0}）`,
              children: (
                <>
                  <Table
                    className="customer-contact-drawer-table"
                    rowKey="id"
                    size="small"
                    tableLayout="fixed"
                    pagination={false}
                    dataSource={contacts?.data.contacts || []}
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
                        render: (_: unknown, r: Contact) => canManageCurrentCustomer ? (
                          <Space size={0}>
                            <Button type="link" onClick={() => openContactEdit(r)}>编辑</Button>
                            <Popconfirm title="删除联系人？" onConfirm={() => deleteContact(r.id)}>
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
                    <Form form={contactForm} layout="vertical">
                      <div className="form-grid">
                        <Form.Item
                          label="姓名"
                          name="name"
                          rules={[{ required: true }]}
                        >
                          <Input />
                        </Form.Item>
                        <Form.Item label="职务" name="position">
                          <Input />
                        </Form.Item>
                        <Form.Item label="项目角色" name="project_role">
                          <Input />
                        </Form.Item>
                        <Form.Item label="电话" name="phone">
                          <Input />
                        </Form.Item>
                        <Form.Item label="办公电话" name="office_phone">
                          <Input />
                        </Form.Item>
                        <Form.Item label="IM" name="im_account">
                          <Input />
                        </Form.Item>
                        <Form.Item label="邮箱" name="email">
                          <Input />
                        </Form.Item>
                        <Form.Item label="联系状态" name="contact_status" initialValue="正常联系">
                          <Select options={["正常联系", "暂缓联系", "停止联系"].map(value => ({ value, label: value }))} />
                        </Form.Item>
                      </div>
                      <Form.Item name="is_valid" valuePropName="checked" initialValue>
                        <Checkbox>有效联系人</Checkbox>
                      </Form.Item>
                      <Form.Item name="is_primary" valuePropName="checked">
                        <Checkbox>设为主要联系人</Checkbox>
                      </Form.Item>
                      <Button type="primary" onClick={addContact}>
                        添加联系人
                      </Button>
                    </Form>
                  </Card>
                </>
              ),
            },
            {
              key: "notes",
              label: `跟进记录（${contacts?.data.notes?.length || 0}）`,
              children: (
                <>
                  <Table
                    rowKey="id"
                    size="small"
                    pagination={false}
                    dataSource={contacts?.data.notes || []}
                    scroll={{ x: 720 }}
                    columns={[
                      {
                        title: "类型",
                        dataIndex: "type",
                        width: 95,
                        render: (v: string) => <Tag color="blue">{v}</Tag>,
                      },
                      { title: "跟进内容", dataIndex: "content" },
                      { title: "记录人", dataIndex: "operator", width: 90 },
                      { title: "时间", dataIndex: "created_at", width: 165 },
                      {
                        title: "操作",
                        width: 70,
                        render: (_: unknown, r: Note) => (
                          <Popconfirm
                            title="删除这条记录？"
                            onConfirm={() => deleteNote(r.id)}
                          >
                            <Button danger type="link">
                              删除
                            </Button>
                          </Popconfirm>
                        ),
                      },
                    ]}
                  />
                  <Card
                    size="small"
                    title="新增跟进记录"
                    style={{ marginTop: 16 }}
                  >
                    <Form
                      form={noteForm}
                      layout="vertical"
                      initialValues={{ note_type: "跟进记录" }}
                    >
                      <Form.Item label="记录类型" name="note_type">
                        <Select
                          options={[
                            "跟进记录",
                            "会议纪要",
                            "电话沟通",
                            "风险提示",
                            "客户备注",
                          ].map((v) => ({ value: v, label: v }))}
                        />
                      </Form.Item>
                      <Form.Item
                        label="内容"
                        name="content"
                        rules={[{ required: true }]}
                      >
                        <Input.TextArea rows={4} />
                      </Form.Item>
                      <Button type="primary" onClick={addNote}>
                        保存跟进记录
                      </Button>
                    </Form>
                  </Card>
                </>
              ),
            },
            {
              key: "documents",
              label: `客户文档（${attachments.length}）`,
              children: (
                <>
                  <Alert
                    type="info"
                    showIcon
                    title="客户主体资料、授权材料和沟通文件统一归档，可按权限下载。"
                    style={{ marginBottom: 12 }}
                  />
                  <Table
                    rowKey="id"
                    size="small"
                    pagination={false}
                    dataSource={attachments}
                    scroll={{ x: 720 }}
                    columns={[
                      {
                        title: "类别",
                        dataIndex: "category",
                        width: 100,
                        render: (v: string) => <Tag>{v}</Tag>,
                      },
                      { title: "文件名", dataIndex: "original_name" },
                      {
                        title: "大小",
                        dataIndex: "size",
                        width: 90,
                        render: (v: number) => `${(v / 1024).toFixed(1)} KB`,
                      },
                      { title: "上传人", dataIndex: "uploader", width: 80 },
                      {
                        title: "操作",
                        width: 130,
                        render: (_: unknown, r: Attachment) => (
                          <Space size={0}>
                            <Button
                              type="link"
                              onClick={() => downloadDocument(r)}
                            >
                              下载
                            </Button>
                            {profile.role === "admin" && (
                              <Popconfirm
                                title="删除客户文档？"
                                onConfirm={() => deleteDocument(r.id)}
                              >
                                <Button type="link" danger>
                                  删除
                                </Button>
                              </Popconfirm>
                            )}
                          </Space>
                        ),
                      },
                    ]}
                  />
                  <Card
                    size="small"
                    title="上传客户文档"
                    style={{ marginTop: 16 }}
                  >
                    <Form
                      form={documentForm}
                      layout="vertical"
                      initialValues={{ category: "客户资料" }}
                    >
                      <div className="form-grid">
                        <Form.Item
                          label="文档类别"
                          name="category"
                          rules={[{ required: true }]}
                        >
                          <Select
                            options={[
                              "客户资料",
                              "工商材料",
                              "授权委托",
                              "沟通记录",
                              "开票资料",
                              "其他材料",
                            ].map((v) => ({ value: v, label: v }))}
                          />
                        </Form.Item>
                        <Form.Item label="选择文件" required>
                          <input
                            ref={documentFileRef}
                            type="file"
                            onChange={(e) =>
                              setDocumentFile(e.target.files?.[0] || null)
                            }
                          />
                        </Form.Item>
                      </div>
                      <Form.Item label="文件说明" name="remark">
                        <Input />
                      </Form.Item>
                      <Button
                        type="primary"
                        icon={<UploadOutlined />}
                        onClick={uploadDocument}
                      >
                        上传文档
                      </Button>
                    </Form>
                  </Card>
                </>
              ),
            },
          ]}
        />
      </Drawer>
    </>
  );
}

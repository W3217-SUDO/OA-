import { useEffect, useMemo, useRef, useState } from "react";
import type { Key } from "react";
import { Form, message, Modal } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import { LegacyContractHistoryPanel } from "../LegacyContractHistoryPanel";
import { buildChinesePersonOptions, displayChinesePersonName, displayChinesePersonNames } from "../contractPeoplePresentation.mjs";
import { customerStatusLabel } from "../customerStatusLabel";
import { consumeCustomerDetailTarget } from "../customerDetailNavigation";
import { rememberCustomerRelationTarget } from "../customerRelationNavigation";
import {
  filterCustomerPatchData,
  synchronizeCustomerSource,
  buildCustomerActionConfirmation,
  buildCustomerActionRequest,
  buildCustomerContactListRequest,
  buildCustomerDocumentUploadFields,
  buildCustomerDetailReturnState,
  buildCustomerListParams,
  buildContactStatusRequest,
  runContactStatusUpdate,
  buildCustomerEventRequest,
  buildCustomerEventListPath,
  buildCustomerFileListPath,
  buildCustomerFileDownloadPath,
  getCustomerActionMessage,
  getCustomerDocumentUploadError,
  getCustomerGuid,
  isCustomerDetailManageable,
  isCustomerRegistrationAddressSafe,
  isCustomerPostalCodeSafe,
  normalizeCustomerSummary,
  normalizeCustomerContactPage,
  normalizeSharedObjectValues,
} from "../customerParity.mjs";
import type { CustomerListSummary } from "../customerParity.mjs";
import {
  OLD_CUSTOMER_EMAIL_PATTERN,
  buildCustomerContactStatusRequest,
  buildCustomerManagerRequest,
  buildCustomerShareRequest,
  getCustomerMutationErrorMessage,
  matchesDirectoryOption,
  normalizeCustomerManager,
  validateCustomerPhotoFile,
  validateCustomerUploadFile,
} from "../customerUiBatchI14.mjs";
import {
  CUSTOMER_CONTACT_FORM_DEFAULTS,
  CUSTOMER_DOCUMENT_FORM_DEFAULTS,
  canDeleteCustomerAttachment,
  getCustomerAttachmentDate,
} from "../customerUiBatchI15.mjs";
import {
  normalizeCustomerAttachmentItems,
  normalizeCustomerCollectionItems,
  normalizeCustomerEventItems,
  normalizeCustomerHistoryItems,
  normalizeCustomerSharedObjectItems,
  getCustomerResponseMessage,
} from "../customerUiBatchI16.mjs";
import {
  assertCustomerMutationSuccess,
  getCustomerMutationErrorMessage as getCustomerMutationErrorMessageI17,
} from "../customerUiBatchI17.mjs";
import "../customer-center.css";
import { CustomerList } from "./CustomerList";
import { CustomerDetailView } from "./CustomerDetailView";
import { CustomerDetailDrawer } from "./CustomerDetailDrawer";
import { CustomerCreateEditModal } from "./CustomerCreateEditModal";
import { CustomerCreatePage } from "./CustomerCreatePage";
import { CustomerModals } from "./CustomerModals";
import {
  EMPTY_LEGACY_CUSTOMER_HISTORY,
  type Attachment,
  type Contact,
  type Customer,
  type CustomerEvent,
  type CustomerNotice,
  type DirectoryUser,
  type LegacyCustomerHistory,
  type Note,
  type Profile,
} from "./types";
import {
  initialProfile,
  prioritizeNewCustomerManagers,
} from "./constants";

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

  // ========== State ==========
  const [allRows, setAllRows] = useState<Customer[]>([]);
  const [keyword, setKeyword] = useState("");
  const [customerType, setCustomerType] = useState("客户");
  const [customerTypeOptions, setCustomerTypeOptions] = useState<{ value: string; label: string }[]>([
    { value: "客户", label: "客户" },
    { value: "当事人", label: "当事人" },
  ]);
  const [managerKeyword, setManagerKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(initialView === "customer-new");
  const [editing, setEditing] = useState<Customer | null>(null);
  const [assigning, setAssigning] = useState<Customer | null>(null);
  const [sharing, setSharing] = useState<Customer | null>(null);
  const [portalResult, setPortalResult] = useState<{ account: string; activation_code: string } | null>(null);
  const [portalCustomer, setPortalCustomer] = useState<Customer | null>(null);
  const [contacts, setContacts] = useState<Customer | null>(null);
  const [viewingContact, setViewingContact] = useState<Contact | null>(null);
  const [editingContact, setEditingContact] = useState<Contact | null>(null);
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [detailPageOpen, setDetailPageOpen] = useState(false);
  const [newEditor, setNewEditor] = useState<"contact" | "note" | "document" | null>(null);

  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [attachmentError, setAttachmentError] = useState("");
  const [events, setEvents] = useState<CustomerEvent[]>([]);
  const [historyError, setHistoryError] = useState("");
  const [recordError, setRecordError] = useState("");
  const [customerEvents, setCustomerEvents] = useState<CustomerNotice[]>([]);
  const [customerEventError, setCustomerEventError] = useState("");
  const [sharedObjects, setSharedObjects] = useState<string[]>([]);
  const [sharedObjectsError, setSharedObjectsError] = useState("");
  const [legacyCustomerHistory, setLegacyCustomerHistory] = useState<LegacyCustomerHistory>(EMPTY_LEGACY_CUSTOMER_HISTORY);
  const [legacyCustomerHistoryError, setLegacyCustomerHistoryError] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailTab, setDetailTab] = useState("contacts");
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [contactPhotoPreview, setContactPhotoPreview] = useState<{ name: string; url: string } | null>(null);
  const [customerDocumentPreview, setCustomerDocumentPreview] = useState<{ name: string; url: string } | null>(null);
  const [customerLicenseThumb, setCustomerLicenseThumb] = useState("");

  const [profile, setProfile] = useState<Profile>(initialProfile);
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const [customerDirectory, setCustomerDirectory] = useState<DirectoryUser[]>([]);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [contactPage, setContactPage] = useState(1);
  const [contactPageSize, setContactPageSize] = useState(15);
  const [contactTotal, setContactTotal] = useState(0);
  const [total, setTotal] = useState(0);
  const [jumpPage, setJumpPage] = useState("1");
  const [listSummary, setListSummary] = useState<CustomerListSummary>(() => normalizeCustomerSummary());

  const [form] = Form.useForm();
  const [assignForm] = Form.useForm();
  const [shareForm] = Form.useForm();
  const [contactForm] = Form.useForm();
  const [contactEditForm] = Form.useForm();
  const [noteForm] = Form.useForm();
  const [noteEditForm] = Form.useForm();
  const [customerEventForm] = Form.useForm();
  const [documentForm] = Form.useForm();

  const documentFileRef = useRef<HTMLInputElement>(null);

  // ========== Derived values ==========
  const directoryOptions = useMemo(() => {
    const retained = new Set([
      ...(editing?.data.customer_managers || []),
      ...(editing?.data.contact_accounts || []),
      ...(Array.isArray(editing?.data.contact) ? editing.data.contact : editing?.data.contact ? [editing.data.contact] : []),
    ].map((value) => String(value || "").trim()).filter(Boolean));
    return buildChinesePersonOptions(
      directory,
      (user: DirectoryUser) => user.eligible_customer_person === true || retained.has(user.username),
      { allowNonChinese: true },
    );
  }, [directory, editing]);

  const customerContactOptions = useMemo(() => {
    const retained = new Set([
      ...(editing?.data.contact_accounts || []),
      ...(Array.isArray(editing?.data.contact) ? editing.data.contact : editing?.data.contact ? [editing.data.contact] : []),
    ].map((value) => String(value || "").trim()).filter(Boolean));
    const candidates = [...new Map(
      [...customerDirectory, ...directory].map((user) => [String(user.username || "").trim().toLowerCase(), user]),
    ).values()];
    return buildChinesePersonOptions(
      candidates,
      (user: DirectoryUser) => user.account_type === "客户账号" || retained.has(user.username),
      { allowNonChinese: true },
    );
  }, [customerDirectory, directory, editing]);

  const customerLicenseAttachment = attachments.find(
    (item) => item.is_license === true || item.is_license === "true" || item.IsLicense === true || item.isLicense === true
  );

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
      ? displayChinesePersonName(profile.display_name || profile.username, directory)
      : managerKeyword;

  const canManageCurrentCustomer = Boolean(contacts && (
    isCustomerDetailManageable(contacts, profile)
  ));

  // ========== Data loading ==========
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
    for (const kw of [...new Set([serialNo, title].filter(Boolean))]) {
      try {
        const { data } = await api.get("/records", {
          params: { module: "customer", keyword: kw, page_size: 100 },
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
              ...buildCustomerListParams({
                scope: originalCustomerScope,
                keyword: requestKeyword,
                customerType: requestCustomerType,
                manager: requestManagerKeyword,
                page: requestPage,
                pageSize,
              }),
              customer_name: requestKeyword,
              customer_type: requestCustomerType,
              ...(["customer-shared", "customer-recent-contact", "customer-recent-update"].includes(initialView) ? {} : { manager: requestManagerKeyword }),
              page_size: pageSize,
            },
          })
        : api.get("/records", {
            params: { module: "customer", keyword: requestKeyword, page_size: 100 },
          });
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
      setListSummary(normalizeCustomerSummary(recordsRes.data.summary));
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
      const [profileResult, directoryResult, customerDirectoryResult, customerTypeResult] = await Promise.allSettled([
        api.get("/auth/me"),
        api.get("/users/directory", { params: { purpose: "customer_manager" } }),
        api.get("/users/directory", { params: { purpose: "customer_contact" } }),
        api.get("/customers/reference-options"),
      ]);
      if (profileResult.status === "fulfilled") setProfile(profileResult.value.data);
      else message.warning("当前登录身份加载失败，已保留客户列表和详情入口");
      if (directoryResult.status === "fulfilled") setDirectory(directoryResult.value.data.items || []);
      else message.warning("客户人员目录加载失败，稍后可刷新重试");
      if (customerDirectoryResult.status === "fulfilled") setCustomerDirectory(customerDirectoryResult.value.data.items || []);
      else message.warning("客户账号目录加载失败，稍后可刷新重试");
      if (customerTypeResult.status === "fulfilled") {
        const options = customerTypeResult.value.data.customer_types || [];
        if (options.length) {
          setCustomerTypeOptions(options);
          if (!options.some((item: { value: string }) => item.value === customerType)) setCustomerType(options[0].value);
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

  // ========== Customer CRUD ==========
  const startCreate = (customerType = "客户") => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      serial_no: "",
      status: undefined,
      owner: profile.username || "admin",
      customer_managers: directoryOptions.some((option) => option.value === profile.username) ? [profile.username] : [],
      department: profile.department || "上海分所",
      customer_type: customerType,
      level: "立案客户",
      is_shared: "否",
      is_assisted: "否",
      file_date: dayjs().format("YYYY-MM-DD"),
      customer_source: "",
    });
    setOpen(true);
  };

  const startEdit = (r: Customer) => {
    setEditing(r);
    setContactPage(1);
    setContactPageSize(15);
    setContactTotal(0);
    setContacts(r);
    setAttachments([]);
    setAttachmentError("");
    form.setFieldsValue({
      ...r,
      ...r.data,
      customer_managers: r.data.customer_managers?.length
        ? r.data.customer_managers
        : [r.owner],
      contact: r.data.contact_accounts?.length
        ? r.data.contact_accounts
        : Array.isArray(r.data.contact)
          ? r.data.contact
          : r.data.contact
            ? [r.data.contact]
            : [],
    });
    setOpen(true);
    void refreshDetail(r, 1, 15);
  };

  const save = async () => {
    const v = await form.validateFields();
    const detailFields = [
      "contact", "phone", "level", "credit_code", "legal_representative",
      "registered_address", "invoice_title", "taxpayer_id", "invoice_address",
      "invoice_phone", "bank_name", "bank_account", "customer_type",
      "short_name", "fax", "legal_agent_id_no", "legal_agent_title",
      "customer_source", "is_shared", "is_assisted", "file_date",
      "province", "postal_code", "patent_customer_type", "fee_reduction",
      "industry", "output_value", "cooperation_status", "gb_classification",
      "website", "organization_nature", "organization_code",
      "registration_region", "registration_postal_code", "registered_capital",
      "registration_year",
    ];
    const details = Object.fromEntries(
      detailFields.map((key) => [key, v[key] || ""]),
    );
    const contactAccounts = Array.isArray(v.contact)
      ? v.contact.map((value: string) => String(value || "").trim()).filter(Boolean)
      : String(v.contact || "").trim()
        ? [String(v.contact).trim()]
        : [];
    details.contact_accounts = contactAccounts;
    details.contact = contactAccounts[0] || "";
    const managers = (v.customer_managers || []).filter((x: string) => x.trim());
    const data = synchronizeCustomerSource({
      ...(editing?.data || {}),
      ...details,
      customer_managers: managers,
    }, v.customer_source);
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
        response = await api.patch(`/records/${editing.id}`, { ...payload, data: filterCustomerPatchData(editableData) });
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
            customer_source: data.customer_source || "",
            source_person: data.source_person || "",
          });
      assertCustomerMutationSuccess(response?.data);
      message.success(editing ? "客户已更新" : "客户已创建");
      if (initialView === "customer-new") {
        setEditing(response.data);
        setContacts(response.data);
        await refreshDetail(response.data);
      } else {
        setOpen(false);
        setContacts(null);
        setEditing(null);
      }
      await load();
    } catch (error: any) {
      message.error(getCustomerMutationErrorMessageI17(error, "保存失败"));
    }
  };

  // ========== Assign / Share / Portal ==========
  const startAssign = (customer: Customer) => {
    setAssigning(customer);
    assignForm.setFieldsValue({
      manager: customer.data.customer_managers?.[0] || customer.owner,
    });
  };

  const assignCustomer = async () => {
    if (!assigning) return;
    const values = await assignForm.validateFields();
    const request = buildCustomerManagerRequest(assigning.id, normalizeCustomerManager(values.manager));
    if (!request) {
      message.warning("请选择有效的客户管理人");
      return;
    }
    try {
      const managerUrl = `/customers/${assigning.id}/managers`;
      const legacyManagersPayload = { managers: [values.manager] };
      const response = await api.put(request.url || managerUrl, request.data || legacyManagersPayload);
      assertCustomerMutationSuccess(response?.data);
      message.success("客户分配成功");
      setAssigning(null);
      setSelectedRowKeys([]);
      await load();
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "客户分配失败";
      message.error(getCustomerMutationErrorMessageI17(error, legacyError));
    }
  };

  const action = async (r: Customer, name: string) => {
    const request = buildCustomerActionRequest(r.id, name, "");
    if (!request) {
      message.error("客户操作不受支持");
      return;
    }
    const actionUrl = request.url || `/customers/${r.id}/${name}`;
    try {
      const response = await api.post(actionUrl, request.data);
      assertCustomerMutationSuccess(response?.data);
      message.success(getCustomerActionMessage(name, true));
      setSelectedRowKeys([]);
      await load();
    } catch (error: any) {
      const legacyActionError = error?.response?.data?.detail || "操作失败";
      message.error(getCustomerMutationErrorMessageI17(error, getCustomerActionMessage(name, false) || legacyActionError));
    }
  };

  const share = async () => {
    if (!sharing) return;
    const v = await shareForm.validateFields();
    const request = buildCustomerShareRequest(sharing.id, v.recipients, v.comment);
    if (!request) {
      message.warning("请先添加至少一位共享人员");
      return;
    }
    try {
      const shareUrl = `/customers/${sharing.id}/share`;
      const legacySharePayload = { recipients: v.recipients, comment: v.comment || "" };
      const response = await api.post(request.url || shareUrl, request.data || legacySharePayload);
      assertCustomerMutationSuccess(response?.data);
      message.success("客户共享成功");
      setSharing(null);
      setSelectedRowKeys([]);
      await load();
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "共享失败";
      message.error(getCustomerMutationErrorMessageI17(error, legacyError));
    }
  };

  const openPortal = async (customer: Customer, account = "") => {
    try {
      const response = await api.post(`/customers/${customer.id}/portal/open`, { comment: "从客户管理开通", account });
      assertCustomerMutationSuccess(response?.data);
      setPortalResult(response.data);
      setPortalCustomer(null);
      await load();
    } catch (error: any) {
      message.error(getCustomerMutationErrorMessageI17(error, "客户服务端开通失败"));
    }
  };

  const closePortal = async (customer: Customer) => {
    try {
      const response = await api.post(`/customers/${customer.id}/portal/close`, { comment: "从客户管理停用" });
      assertCustomerMutationSuccess(response?.data);
      message.success("客户服务端已停用");
      await load();
    } catch (error: any) {
      message.error(getCustomerMutationErrorMessageI17(error, "客户服务端停用失败"));
    }
  };

  const portalAccounts = (customer: Customer) => {
    const raw = customer.data.contact_accounts?.length
      ? customer.data.contact_accounts
      : Array.isArray(customer.data.contact) ? customer.data.contact : customer.data.contact ? [customer.data.contact] : [];
    return [...new Set(raw.map((value) => String(value || "").trim()).filter(Boolean))];
  };

  // ========== Detail refresh ==========
  const refreshDetail = async (
    target = contacts,
    nextContactPage = contactPage,
    nextContactPageSize = contactPageSize,
  ) => {
    if (!target) return;
    setDetailLoading(true);
    let historyItems: CustomerEvent[] = [];
    let historyErrorMessage = "";
    let recordErrorMessage = "";
    let attachmentErrorMessage = "";
    let customerEventItems: CustomerNotice[] = [];
    let customerEventErrorMessage = "";
    let sharedObjectItems: string[] = [];
    let sharedObjectsErrorMessage = "";
    let legacyHistoryItems: LegacyCustomerHistory = EMPTY_LEGACY_CUSTOMER_HISTORY;
    let legacyHistoryErrorMessage = "";
    const customerGuid = getCustomerGuid(target);
    const customerEventListPath = buildCustomerEventListPath(customerGuid);
    const customerFileListPath = buildCustomerFileListPath(customerGuid);
    const contactListRequest = buildCustomerContactListRequest(target.id, nextContactPage, nextContactPageSize);
    const fallbackContactResponse = {
      data: {
        items: target.data.contacts || [],
        total: (target.data.contacts || []).length,
        page: nextContactPage,
        page_size: nextContactPageSize,
      },
    };
    try {
      const [recordRes, fileRes, historyRes, customerEventRes, sharedObjectsRes, contactRes, legacyHistoryRes] = await Promise.all([
        api.get("/customers", {
          params: {
            scope: originalCustomerScope,
            customer_name: target.serial_no,
            customer_type: target.data.customer_type || "客户",
            page: 1,
            page_size: 10,
          },
        }).catch((error) => {
          recordErrorMessage = getCustomerResponseMessage(error, "客户记录加载失败");
          return { data: { items: [] } };
        }),
        customerFileListPath
          ? api.get(customerFileListPath).catch((error) => {
              attachmentErrorMessage = getCustomerResponseMessage(error, "客户文档加载失败");
              return { data: { items: [] } };
            })
          : api.get("/attachments", { params: { record_id: target.id } }).catch((error) => {
              attachmentErrorMessage = getCustomerResponseMessage(error, "客户文档加载失败");
              return { data: { items: [] } };
            }),
        api.get(`/records/${target.id}/history`).catch((error) => {
          historyErrorMessage = error?.response?.data?.detail || "操作记录加载失败";
          return { data: { items: [] } };
        }),
        customerEventListPath
          ? api.get(customerEventListPath).catch((error) => {
              customerEventErrorMessage = error?.response?.data?.detail || "客户注意事项加载失败";
              return { data: { items: [] } };
            })
          : Promise.resolve({ data: { items: [] } }),
        api.get(`/customers/${target.id}/shared-objects`).catch((error) => {
          sharedObjectsErrorMessage = error?.response?.data?.detail || "共享对象加载失败";
          return { data: { items: [] } };
        }),
        contactListRequest
          ? api.get(contactListRequest.url, { params: contactListRequest.params }).catch(() => fallbackContactResponse)
          : Promise.resolve(fallbackContactResponse),
        customerGuid
          ? api.get(`/customers/guid/${encodeURIComponent(customerGuid)}/legacy-history`).catch((error) => {
              legacyHistoryErrorMessage = getCustomerResponseMessage(error, "旧系统客户历史加载失败");
              return { data: EMPTY_LEGACY_CUSTOMER_HISTORY };
            })
          : Promise.resolve({ data: EMPTY_LEGACY_CUSTOMER_HISTORY }),
      ]);
      let resolvedCustomer = target;
      try {
        resolvedCustomer = (normalizeCustomerCollectionItems(recordRes.data) as Customer[]).find((x) => x?.id === target.id) || target;
      } catch (error: any) {
        recordErrorMessage = getCustomerResponseMessage(error, "客户记录加载失败");
      }
      const contactPageData = normalizeCustomerContactPage(contactRes.data);
      setContactTotal(contactPageData.total);
      setContacts({
        ...resolvedCustomer,
        data: { ...resolvedCustomer.data, contacts: contactPageData.items },
      });
      try {
        setAttachments((normalizeCustomerAttachmentItems(fileRes.data) as Attachment[]).filter((item) => item.category !== "客户联系人照片"));
      } catch (error: any) {
        attachmentErrorMessage = getCustomerResponseMessage(error, "客户文档加载失败");
        setAttachments([]);
      }
      try {
        historyItems = normalizeCustomerHistoryItems(historyRes.data) as CustomerEvent[];
      } catch (error: any) {
        historyErrorMessage = getCustomerResponseMessage(error, "操作记录加载失败");
      }
      try {
        customerEventItems = normalizeCustomerEventItems(customerEventRes.data) as CustomerNotice[];
      } catch (error: any) {
        customerEventErrorMessage = getCustomerResponseMessage(error, "客户注意事项加载失败");
      }
      if (!customerEventListPath) {
        const resolvedEventPath = buildCustomerEventListPath(getCustomerGuid(resolvedCustomer));
        if (resolvedEventPath) {
          try {
            const resolvedEventRes = await api.get(resolvedEventPath);
            customerEventItems = normalizeCustomerEventItems(resolvedEventRes.data) as CustomerNotice[];
          } catch (error: any) {
            customerEventErrorMessage = getCustomerResponseMessage(error, "客户注意事项加载失败");
          }
        }
      }
      try {
        sharedObjectItems = normalizeCustomerSharedObjectItems(sharedObjectsRes.data);
      } catch (error: any) {
        sharedObjectsErrorMessage = getCustomerResponseMessage(error, "共享对象加载失败");
      }
      const rawLegacyHistory = legacyHistoryRes?.data || EMPTY_LEGACY_CUSTOMER_HISTORY;
      legacyHistoryItems = {
        coordinators: Array.isArray(rawLegacyHistory.coordinators) ? rawLegacyHistory.coordinators : [],
        contacts: Array.isArray(rawLegacyHistory.contacts) ? rawLegacyHistory.contacts : [],
        events: Array.isArray(rawLegacyHistory.events) ? rawLegacyHistory.events : [],
        files: Array.isArray(rawLegacyHistory.files) ? rawLegacyHistory.files : [],
        zero_baselines: Array.isArray(rawLegacyHistory.zero_baselines) ? rawLegacyHistory.zero_baselines : [],
        counts: { ...EMPTY_LEGACY_CUSTOMER_HISTORY.counts, ...(rawLegacyHistory.counts || {}) },
      };
    } finally {
      setEvents(historyItems);
      setHistoryError(historyErrorMessage);
      setRecordError(recordErrorMessage);
      setAttachmentError(attachmentErrorMessage);
      setCustomerEvents(customerEventItems);
      setCustomerEventError(customerEventErrorMessage);
      setSharedObjects(sharedObjectItems);
      setSharedObjectsError(sharedObjectsErrorMessage);
      setLegacyCustomerHistory(legacyHistoryItems);
      setLegacyCustomerHistoryError(legacyHistoryErrorMessage);
      setDetailLoading(false);
    }
  };

  const loadContactPage = async (target = contacts, nextPage = contactPage, nextPageSize = contactPageSize) => {
    if (!target) return;
    const request = buildCustomerContactListRequest(target.id, nextPage, nextPageSize);
    if (!request) return;
    try {
      const response = await api.get(request.url, { params: request.params });
      const pageData = normalizeCustomerContactPage(response.data);
      setContactPage(pageData.page);
      setContactPageSize(pageData.pageSize);
      setContactTotal(pageData.total);
      setContacts((current) => current && current.id === target.id
        ? { ...current, data: { ...current.data, contacts: pageData.items } }
        : current);
    } catch (error: any) {
      message.error(getCustomerResponseMessage(error, "联系人加载失败"));
    }
  };

  const refreshCustomerContacts = () => {
    if (!contacts) return;
    void loadContactPage(contacts);
  };

  const handleCustomerDetailTabChange = (key: string) => {
    setDetailTab(key);
    if (contacts && key !== detailTab) void refreshDetail(contacts);
  };

  const openDetail = async (r: Customer, tab = "contacts") => {
    setContactPage(1);
    setContactPageSize(15);
    setContactTotal(0);
    setContacts(r);
    setDetailPageOpen(isReadOnlyCustomerList);
    setDetailTab(tab);
    setAttachments([]);
    setAttachmentError("");
    setEvents([]);
    setHistoryError("");
    setRecordError("");
    setCustomerEvents([]);
    setCustomerEventError("");
    setSharedObjects([]);
    setSharedObjectsError("");
    try {
      await refreshDetail(r, 1, 15);
    } catch (error: any) {
      message.error(getCustomerResponseMessage(error, "客户详情加载失败"));
    }
  };

  // ========== Navigation ==========
  const openCustomerContracts = (customer: Customer) => {
    sessionStorage.setItem("sunhold:customer-return", JSON.stringify(buildCustomerDetailReturnState({
      scope: originalCustomerScope,
      page,
      pageSize,
      keyword,
      managerKeyword,
    })));
    rememberCustomerRelationTarget({ id: customer.id, serial_no: customer.serial_no, title: customer.title, target: "contracts" });
    const targetView = initialView === "customer-mine"
      ? "contract-mine"
      : ["customer-dept", "customer-dept-recycle"].includes(initialView)
        ? "contract-dept"
        : "contract-company";
    onNavigate?.(targetView);
  };

  const openCustomerContractCreate = (customer: Customer) => {
    sessionStorage.setItem("sunhold:contract-customer", JSON.stringify({
      id: customer.id,
      name: customer.title,
      serial_no: customer.serial_no,
      at: Date.now(),
    }));
    sessionStorage.setItem("sunhold:contract-customer-route-source", "customer");
    onNavigate?.("contract-new");
  };

  const openCustomerCivilCases = (customer: Customer) => {
    sessionStorage.setItem("sunhold:customer-return", JSON.stringify(buildCustomerDetailReturnState({
      scope: originalCustomerScope,
      page,
      pageSize,
      keyword,
      managerKeyword,
    })));
    rememberCustomerRelationTarget({ id: customer.id, serial_no: customer.serial_no, title: customer.title, target: "civil-cases" });
    const targetViewBase = initialView === "customer-mine"
      ? "case-mine"
      : ["customer-dept", "customer-dept-recycle"].includes(initialView)
        ? "case-dept"
        : "case-company";
    const targetView = `${targetViewBase}-civil-customer-${customer.id}`;
    onNavigate?.(targetView);
  };

  const openCustomerIprCases = (customer: Customer) => {
    sessionStorage.setItem("sunhold:customer-return", JSON.stringify(buildCustomerDetailReturnState({
      scope: originalCustomerScope,
      page,
      pageSize,
      keyword,
      managerKeyword,
    })));
    sessionStorage.setItem("sunhold:customer-ipr-relation", JSON.stringify({
      id: customer.id,
      serial_no: customer.serial_no,
      title: customer.title,
      target: "ipr-cases",
      at: Date.now(),
    }));
    onNavigate?.("ipr-patent");
  };

  const openCustomerCommunication = (customer: Customer) => {
    sessionStorage.setItem("sunhold:communication-customer", JSON.stringify({
      id: customer.id,
      serial_no: customer.serial_no,
      name: customer.title,
      at: Date.now(),
    }));
    onNavigate?.("user-communications");
  };

  // ========== Contact operations ==========
  const addContact = async () => {
    if (!contacts) return;
    const v = await contactForm.validateFields();
    if (v.email && !OLD_CUSTOMER_EMAIL_PATTERN.test(String(v.email))) {
      message.error("请填写正确联系邮件.");
      return;
    }
    try {
      const response = await api.post(`/customers/${contacts.id}/contacts`, v);
      assertCustomerMutationSuccess(response?.data);
      message.success("联系人已添加");
      contactForm.resetFields();
      setNewEditor(null);
      await refreshDetail();
      load();
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "联系人添加失败";
      message.error(getCustomerMutationErrorMessage(error, legacyError));
    }
  };

  const deleteContact = async (id: string) => {
    if (!contacts) return;
    try {
      const response = await api.delete(`/customers/${contacts.id}/contacts/${id}`);
      assertCustomerMutationSuccess(response?.data);
      message.success("联系人已删除");
      await refreshDetail();
      load();
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "删除失败";
      if (error?.response?.data?.detail) {
        message.error(error?.response?.data?.detail || "删除失败");
      } else {
        message.error(getCustomerMutationErrorMessage(error, legacyError));
      }
    }
  };

  const uploadContactPhoto = async (contact: Contact, option: any) => {
    if (!contacts) return;
    const validation = validateCustomerPhotoFile(option.file);
    if (!validation.ok) {
      option.onError?.(validation);
      message.error(validation.code === "empty" ? "照片文件为空" : validation.code === "size" ? "联系人照片不能超过 10MB" : "联系人照片仅支持 JPG、PNG、GIF 或 WEBP 图片");
      return;
    }
    try {
      const data = new FormData(); data.append("file", option.file as Blob);
      const response = await api.post(`/customers/${contacts.id}/contacts/${contact.id}/photo`, data, { headers: { "Content-Type": "multipart/form-data" } });
      assertCustomerMutationSuccess(response?.data);
      option.onSuccess?.({}); message.success("联系人照片已上传"); await refreshDetail(); load();
    } catch (error: any) { option.onError?.(error); message.error(getCustomerMutationErrorMessage(error, "联系人照片上传失败")); }
  };

  const viewContactPhoto = async (contact: Contact) => {
    if (!contacts || !contact.photo_attachment_id) return message.info("该联系人尚未上传照片");
    try {
      const response = await api.get(`/customers/${contacts.id}/contacts/${contact.id}/photo/download`, { responseType: "blob" });
      setContactPhotoPreview({ name: contact.photo_original_name || `${contact.name}的照片`, url: URL.createObjectURL(response.data) });
    }
    catch (error: any) { message.error(error?.response?.data?.detail || "联系人照片加载失败"); }
  };

  const openContactEdit = (contact: Contact) => {
    contactEditForm.setFieldsValue({ ...contact });
    setEditingContact(contact);
  };

  const updateContact = async () => {
    if (!contacts || !editingContact) return;
    const values = await contactEditForm.validateFields();
    if (values.email && !OLD_CUSTOMER_EMAIL_PATTERN.test(String(values.email))) {
      message.error("请填写正确联系邮件.");
      return;
    }
    try {
      const response = await api.put(`/customers/${contacts.id}/contacts/${editingContact.id}`, values);
      assertCustomerMutationSuccess(response?.data);
      message.success("联系人已更新");
      setEditingContact(null);
      contactEditForm.resetFields();
      await refreshDetail();
      load();
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "联系人更新失败";
      message.error(getCustomerMutationErrorMessage(error, legacyError));
    }
  };

  const updateContactStatus = async (contact: Contact, action: "primary" | "active" | "inactive") => {
    if (!contacts) return;
    const request = buildCustomerContactStatusRequest(contacts.id, contact.id, action) || buildContactStatusRequest(contacts.id, contact.id, contact, action);
    if (!request) return;
    try {
      await runContactStatusUpdate(
        request,
        (url, data) => api.patch(url, data).then((response) => {
          assertCustomerMutationSuccess(response?.data);
          return response;
        }),
        refreshDetail,
        load,
      );
      message.success(action === "primary" ? "联系人已设为主要联系人" : action === "active" ? "联系人已恢复有效" : "联系人已设为无效");
    } catch (error: any) {
      message.error(getCustomerMutationErrorMessage(error, "联系人状态更新失败"));
    }
  };

  // ========== Note operations ==========
  const addNote = async () => {
    if (!contacts) return;
    const v = await noteForm.validateFields();
    try {
      const response = await api.post(`/customers/${contacts.id}/notes`, v);
      assertCustomerMutationSuccess(response?.data);
      message.success("跟进记录已保存");
      noteForm.resetFields();
      setNewEditor(null);
      await refreshDetail();
      load();
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "跟进记录保存失败";
      message.error(getCustomerMutationErrorMessage(error, legacyError));
    }
  };

  const deleteNote = async (id: string) => {
    if (!contacts) return;
    try {
      const response = await api.delete(`/customers/${contacts.id}/notes/${id}`);
      assertCustomerMutationSuccess(response?.data);
      message.success("跟进记录已删除");
      await refreshDetail();
      load();
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "删除失败";
      message.error(getCustomerMutationErrorMessage(error, legacyError));
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
      const response = await api.put(`/customers/${contacts.id}/notes/${editingNote.id}`, values);
      assertCustomerMutationSuccess(response?.data);
      message.success("事项记录已更新");
      setEditingNote(null);
      noteEditForm.resetFields();
      await refreshDetail();
      load();
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "事项记录更新失败";
      message.error(getCustomerMutationErrorMessage(error, legacyError));
    }
  };

  // ========== Document operations ==========
  const uploadDocument = async () => {
    if (!contacts || !documentFile) return message.warning("请选择客户文档");
    const validation = validateCustomerUploadFile(documentFile);
    if (!validation.ok) {
      message.error(validation.code === "empty" ? "文件没有任何内容" : validation.code === "size" ? "单个文件不能超过 20MB" : "不支持的文件格式");
      return;
    }
    const v = await documentForm.validateFields();
    const data = new FormData();
    data.append("file", documentFile);
    const fields = buildCustomerDocumentUploadFields({
      customerId: contacts.id,
      customerGuid: getCustomerGuid(contacts),
      category: v.category,
      remark: v.remark,
      isLicense: Boolean(v.is_license),
    });
    data.append("record_id", String(contacts.id));
    Object.entries(fields)
      .filter(([key]) => key !== "record_id")
      .forEach(([key, value]) => data.append(key, value));
    try {
      const response = await api.post("/attachments", data);
      assertCustomerMutationSuccess(response?.data);
      message.success("客户文档已上传");
      documentForm.resetFields();
      setDocumentFile(null);
      setNewEditor(null);
      if (documentFileRef.current) documentFileRef.current.value = "";
      await refreshDetail();
    } catch (error: any) {
      message.error(getCustomerMutationErrorMessage(error, getCustomerDocumentUploadError(error)));
    }
  };

  const fetchCustomerDocument = async (file: Attachment) => {
    const guidDownloadPath = buildCustomerFileDownloadPath(getCustomerGuid(contacts), file.id);
    if (guidDownloadPath) return await api.get(guidDownloadPath, { responseType: "blob" });
    return await api.get(`/attachments/${file.id}/download`, { responseType: "blob" });
  };

  const downloadDocument = async (file: Attachment) => {
    try {
      const res = await fetchCustomerDocument(file);
      const url = URL.createObjectURL(res.data),
        a = document.createElement("a");
      a.href = url;
      a.download = file.original_name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "下载失败";
      message.error(getCustomerMutationErrorMessage(error, legacyError));
    }
  };

  const viewDocument = async (file: Attachment) => {
    const previewable = /\.(pdf|jpe?g|png|gif|webp|tiff?)$/i.test(file.original_name);
    if (!previewable) return downloadDocument(file);
    try {
      const res = await fetchCustomerDocument(file);
      const url = URL.createObjectURL(res.data);
      setCustomerDocumentPreview({ name: file.original_name, url });
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "文档加载失败";
      message.error(getCustomerMutationErrorMessage(error, legacyError));
    }
  };

  useEffect(() => {
    let cancelled = false;
    setCustomerLicenseThumb((current) => {
      if (current) URL.revokeObjectURL(current);
      return "";
    });
    if (!customerLicenseAttachment) return;
    void fetchCustomerDocument(customerLicenseAttachment)
      .then((res) => { if (!cancelled) setCustomerLicenseThumb(URL.createObjectURL(res.data)); })
      .catch(() => { if (!cancelled) setCustomerLicenseThumb(""); });
    return () => { cancelled = true; };
  }, [customerLicenseAttachment?.id]);

  const openLicenseUpload = () => {
    openNewEditor("document");
    documentForm.setFieldsValue({ ...CUSTOMER_DOCUMENT_FORM_DEFAULTS, is_license: true });
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
    if (type === "document") documentForm.setFieldsValue(CUSTOMER_DOCUMENT_FORM_DEFAULTS);
    setNewEditor(type);
  };

  const deleteDocument = async (id: number) => {
    try {
      const response = await api.delete(`/attachments/${id}`);
      assertCustomerMutationSuccess(response?.data);
      message.success("客户文档已删除");
      await refreshDetail();
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "删除失败";
      message.error(getCustomerMutationErrorMessage(error, legacyError));
    }
  };

  const createCustomerEvent = async () => {
    if (!contacts) return;
    const request = buildCustomerEventRequest(
      getCustomerGuid(contacts),
      customerEventForm.getFieldValue("content"),
    );
    if (!request) {
      message.warning(getCustomerGuid(contacts) ? "请输入客户注意事项" : "客户编号缺失，无法保存注意事项");
      return;
    }
    try {
      const response = await api.post(request.url, request.data);
      assertCustomerMutationSuccess(response?.data);
      message.success("客户注意事项已保存");
      customerEventForm.resetFields();
      await refreshDetail();
    } catch (error: any) {
      const legacyError = error?.response?.data?.detail || "客户注意事项保存失败";
      message.error(getCustomerMutationErrorMessage(error, legacyError));
    }
  };

  // ========== Actions ==========
  const selected = rows.find((row) => selectedRowKeys.includes(row.id));

  const requireSingleSelected = () => {
    if (selectedRowKeys.length !== 1 || !selected) {
      message.info("请选择一条客户记录.");
      return null;
    }
    return selected;
  };

  const recycleCustomer = (row: Customer) => {
    const confirmation = buildCustomerActionConfirmation("recycle", row.title);
    if (!confirmation) return;
    Modal.confirm({
      title: `确认删除客户"${confirmation.title}"？`,
      content: "删除后客户将进入回收站，可在回收站恢复或进入公海。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        const request = buildCustomerActionRequest(row.id, confirmation.action, `${initialView === "customer-company" ? "公司客户" : "客户"}：客户删除`);
        if (!request) return;
        try {
          const response = await api.post(`/customers/${row.id}/recycle`, request.data);
          assertCustomerMutationSuccess(response?.data);
          message.success(getCustomerActionMessage(confirmation.action, true));
          setSelectedRowKeys([]);
          await load();
        } catch (error: any) {
          message.error(getCustomerMutationErrorMessageI17(error, getCustomerActionMessage(confirmation.action, false)));
        }
      },
    });
  };

  const releaseCustomer = (row: Customer) => {
    const confirmation = buildCustomerActionConfirmation("release", row.title);
    if (!confirmation) return;
    Modal.confirm({
      title: `确认将客户"${confirmation.title}"释放到公海？`,
      content: "释放后，该客户将从当前负责人名下移入公海，可由有权限的人员拾回。",
      okText: "确认释放",
      cancelText: "取消",
      onOk: () => action(row, confirmation.action),
    });
  };

  const originalActionItems = (() => {
    const customerNavigationActions = [
      { key: "communication", label: "新增沟通记录" },
      { key: "contact-management", label: "联系人管理" },
    ];
    const customerPortalActions = [
      { key: "portal-open", label: "开通/重置客户服务端" },
      { key: "portal-close", label: "停用客户服务端" },
    ];
    return (
      initialView === "customer-mine"
        ? [
            { key: "edit", label: "客户编辑" },
            { key: "delete", label: "客户删除" },
            { key: "release", label: "释放到公海" },
            { key: "contract", label: "新增合同" },
            ...customerNavigationActions,
            { key: "share", label: "共享客户" },
            ...customerPortalActions,
          ]
        : initialView === "customer-dept"
          ? [{ key: "assign", label: "分配客户" }]
          : initialView === "customer-company"
            ? [{ key: "assign", label: "分配客户" }]
            : ["customer-recycle", "customer-dept-recycle", "customer-company-recycle"].includes(initialView)
              ? [{ key: "restore", label: "客户恢复" }, { key: "release", label: "进入公海" }]
              : initialView === "customer-shared"
                ? [...customerNavigationActions]
                : initialView === "customer-public"
                  ? profile.role === "admin"
                    ? [{ key: "edit", label: "客户编辑" }, { key: "claim", label: "拾回" }]
                    : [{ key: "claim", label: "拾回" }]
                  : ["customer-recent-contact", "customer-recent-update"].includes(initialView)
                    ? [{ key: "edit", label: "客户编辑" }, ...customerNavigationActions]
                    : []
    );
  })();

  const runOriginalAction = (key: string) => {
    const target = requireSingleSelected();
    if (!target) return;
    if (key === "delete") recycleCustomer(target);
    if (key === "edit") startEdit(target);
    if (key === "assign") startAssign(target);
    if (key === "communication") openCustomerCommunication(target);
    if (key === "contact-management") void openDetail(target, "contacts");
    if (key === "contract") openCustomerContractCreate(target);
    if (key === "portal-open") {
      const accounts = portalAccounts(target);
      if (accounts.length > 1) setPortalCustomer(target);
      else void openPortal(target, accounts[0] || "");
    }
    if (key === "portal-close") void closePortal(target);
    if (key === "claim") void action(target, "claim");
    if (key === "share") {
      shareForm.setFieldsValue({ recipients: normalizeSharedObjectValues(target.data.shared_with) });
      setSharing(target);
    }
    if (key === "release") releaseCustomer(target);
    if (["recycle", "restore"].includes(key)) void action(target, key);
  };

  const goToCustomerPage = (target: number) => {
    const next = Math.min(Math.max(1, target), customerPageCount);
    setPage(next);
    setJumpPage(String(next));
    setSelectedRowKeys([]);
  };

  const handleResetSearch = () => {
    const resetCustomerType = customerTypeOptions[0]?.value || "客户";
    setKeyword("");
    setCustomerType(resetCustomerType);
    setManagerKeyword("");
    setSelectedRowKeys([]);
    setPage(1);
    setJumpPage("1");
    void load({ keyword: "", customerType: resetCustomerType, managerKeyword: "", page: 1 });
  };

  const handlePageSizeChange = (value: number) => {
    setPageSize(value);
    setPage(1);
    setJumpPage("1");
    setSelectedRowKeys([]);
  };

  const handleDetailViewClose = () => {
    setDetailPageOpen(false);
    setContacts(null);
  };

  const handleCreateEditCancel = () => {
    setOpen(false);
    setContacts(null);
    setEditing(null);
  };

  const handleCloseContactPhotoPreview = () => {
    if (contactPhotoPreview) URL.revokeObjectURL(contactPhotoPreview.url);
    setContactPhotoPreview(null);
  };

  const handleCloseCustomerDocumentPreview = () => {
    if (customerDocumentPreview) URL.revokeObjectURL(customerDocumentPreview.url);
    setCustomerDocumentPreview(null);
  };

  const handleCloseEditContact = () => {
    setEditingContact(null);
    contactEditForm.resetFields();
  };

  const handleCloseEditNote = () => {
    setEditingNote(null);
    noteEditForm.resetFields();
  };

  const handleContactPageChange = (nextPage: number, nextPageSize: number) => {
    void loadContactPage(contacts, nextPage, nextPageSize);
  };

  // ========== Render ==========
  return (
    <>
      {/* 只读详情视图 */}
      {isReadOnlyCustomerList && detailPageOpen && contacts && (
        <CustomerDetailView
          initialView={initialView}
          customer={contacts}
          directory={directory}
          customerTypeOptions={customerTypeOptions}
          detailTab={detailTab}
          detailLoading={detailLoading}
          recordError={recordError}
          historyError={historyError}
          attachmentError={attachmentError}
          customerEventError={customerEventError}
          sharedObjectsError={sharedObjectsError}
          legacyCustomerHistoryError={legacyCustomerHistoryError}
          contactPage={contactPage}
          contactPageSize={contactPageSize}
          contactTotal={contactTotal}
          customerEvents={customerEvents}
          events={events}
          attachments={attachments}
          sharedObjects={sharedObjects}
          legacyCustomerHistory={legacyCustomerHistory}
          customerLicenseAttachment={customerLicenseAttachment}
          customerLicenseThumb={customerLicenseThumb}
          canManage={canManageCurrentCustomer}
          customerEventForm={customerEventForm}
          onTabChange={handleCustomerDetailTabChange}
          onClose={handleDetailViewClose}
          onRefreshContacts={refreshCustomerContacts}
          onContactPageChange={handleContactPageChange}
          onNewContact={() => openNewEditor("contact")}
          onViewContact={setViewingContact}
          onEditContact={openContactEdit}
          onDeleteContact={deleteContact}
          onSetContactPrimary={(c) => void updateContactStatus(c, "primary")}
          onSetContactActive={(c) => void updateContactStatus(c, "active")}
          onSetContactInactive={(c) => void updateContactStatus(c, "inactive")}
          onUploadContactPhoto={uploadContactPhoto}
          onViewContactPhoto={viewContactPhoto}
          onViewDocument={viewDocument}
          onDownloadDocument={downloadDocument}
          onDeleteDocument={deleteDocument}
          onDeleteNote={deleteNote}
          onEditNote={openNoteEdit}
          onNewNote={() => openNewEditor("note")}
          onNewDocument={() => openNewEditor("document")}
          onOpenLicenseUpload={openLicenseUpload}
          onOpenContracts={() => openCustomerContracts(contacts)}
          onNewContract={() => openCustomerContractCreate(contacts)}
          onCreateCustomerEvent={createCustomerEvent}
        />
      )}

      {/* 客户列表 */}
      {initialView !== "customer-new" && !(isReadOnlyCustomerList && detailPageOpen) && (
        <CustomerList
          initialView={initialView}
          rows={rows}
          total={total}
          page={page}
          pageSize={pageSize}
          customerPageCount={customerPageCount}
          customerPageNumbers={customerPageNumbers}
          jumpPage={jumpPage}
          loading={loading}
          keyword={keyword}
          customerType={customerType}
          customerTypeOptions={customerTypeOptions}
          managerKeyword={managerKeyword}
          managerLocked={managerLocked}
          managerDisplay={managerDisplay}
          isOriginalCustomerList={isOriginalCustomerList}
          isReadOnlyCustomerList={isReadOnlyCustomerList}
          selectedRowKeys={selectedRowKeys}
          listSummary={listSummary}
          profile={profile}
          directory={directory}
          originalActionItems={originalActionItems}
          onKeywordChange={setKeyword}
          onCustomerTypeChange={setCustomerType}
          onManagerKeywordChange={setManagerKeyword}
          onSearch={queryCustomerList}
          onReset={handleResetSearch}
          onSelectedRowKeysChange={setSelectedRowKeys}
          onStartCreate={startCreate}
          onOpenDetail={openDetail}
          onOpenCustomerCommunication={openCustomerCommunication}
          onOpenCustomerContracts={openCustomerContracts}
          onOpenCustomerCivilCases={openCustomerCivilCases}
          onOpenCustomerIprCases={openCustomerIprCases}
          onRunOriginalAction={runOriginalAction}
          onGoToPage={goToCustomerPage}
          onJumpPageChange={(v) => setJumpPage(v.replace(/\D/g, ""))}
          onPageSizeChange={handlePageSizeChange}
        />
      )}

      {/* 新建客户页面（customer-new 视图，Card 布局而非 Modal） */}
      {initialView === "customer-new" && (
        <CustomerCreatePage
          directory={directory}
          canManage={canManageCurrentCustomer}
          onEditContact={openContactEdit}
          onDeleteContact={deleteContact}
          onUploadContactPhoto={uploadContactPhoto}
          onViewContactPhoto={viewContactPhoto}
          onDeleteNote={deleteNote}
          onDeleteDocument={deleteDocument}
          form={form}
          customerTypeOptions={customerTypeOptions}
          directoryOptions={directoryOptions}
          customerContactOptions={customerContactOptions}
          detailLoading={detailLoading}
          attachmentError={attachmentError}
          contactPage={contactPage}
          contactPageSize={contactPageSize}
          contactTotal={contactTotal}
          contacts={contacts}
          attachments={attachments}
          onSave={save}
          onRefreshContacts={refreshCustomerContacts}
          onContactPageChange={handleContactPageChange}
          onNewEditor={openNewEditor}
          onViewDocument={viewDocument}
          onDownloadDocument={downloadDocument}
        />
      )}

      {/* 新增/编辑客户 Modal（非 customer-new 视图） */}
      {open && initialView !== "customer-new" && (
        <CustomerCreateEditModal
          directory={directory}
          open={open}
          editing={editing}
          customerTypeOptions={customerTypeOptions}
          directoryOptions={directoryOptions}
          customerContactOptions={customerContactOptions}
          detailLoading={detailLoading}
          attachmentError={attachmentError}
          contactPage={contactPage}
          contactPageSize={contactPageSize}
          contactTotal={contactTotal}
          contacts={contacts}
          attachments={attachments}
          canManage={canManageCurrentCustomer}
          form={form}
          contactForm={contactForm}
          noteForm={noteForm}
          documentForm={documentForm}
          documentFileRef={documentFileRef}
          documentFile={documentFile}
          onCancel={handleCreateEditCancel}
          onSave={save}
          onRefreshContacts={refreshCustomerContacts}
          onContactPageChange={handleContactPageChange}
          onNewEditor={openNewEditor}
          onAddContact={addContact}
          onEditContact={openContactEdit}
          onDeleteContact={deleteContact}
          onUploadContactPhoto={uploadContactPhoto}
          onViewContactPhoto={viewContactPhoto}
          onAddNote={addNote}
          onDeleteNote={deleteNote}
          onViewDocument={viewDocument}
          onDownloadDocument={downloadDocument}
          onDeleteDocument={deleteDocument}
          onUploadDocument={uploadDocument}
          onDocumentFileChange={setDocumentFile}
        />
      )}

      {/* 客户详情 Drawer */}
      <CustomerDetailDrawer
        open={Boolean(contacts) && !editing && initialView !== "customer-new" && !detailPageOpen}
        customer={contacts}
        detailTab={detailTab}
        detailLoading={detailLoading}
        historyError={historyError}
        attachmentError={attachmentError}
        customerEventError={customerEventError}
        sharedObjectsError={sharedObjectsError}
        legacyCustomerHistoryError={legacyCustomerHistoryError}
        contactPage={contactPage}
        contactPageSize={contactPageSize}
        contactTotal={contactTotal}
        customerEvents={customerEvents}
        events={events}
        attachments={attachments}
        sharedObjects={sharedObjects}
        legacyCustomerHistory={legacyCustomerHistory}
        canManage={canManageCurrentCustomer}
        directory={directory}
        contactForm={contactForm}
        noteForm={noteForm}
        customerEventForm={customerEventForm}
        documentForm={documentForm}
        documentFileRef={documentFileRef}
        documentFile={documentFile}
        onClose={() => setContacts(null)}
        onTabChange={handleCustomerDetailTabChange}
        onRefreshContacts={refreshCustomerContacts}
        onContactPageChange={handleContactPageChange}
        onAddContact={addContact}
        onViewContact={setViewingContact}
        onEditContact={openContactEdit}
        onDeleteContact={deleteContact}
        onSetContactPrimary={(c) => void updateContactStatus(c, "primary")}
        onSetContactActive={(c) => void updateContactStatus(c, "active")}
        onSetContactInactive={(c) => void updateContactStatus(c, "inactive")}
        onUploadContactPhoto={uploadContactPhoto}
        onViewContactPhoto={viewContactPhoto}
        onAddNote={addNote}
        onDeleteNote={deleteNote}
        onViewDocument={viewDocument}
        onDownloadDocument={downloadDocument}
        onDeleteDocument={deleteDocument}
        onUploadDocument={uploadDocument}
        onDocumentFileChange={setDocumentFile}
        onOpenContracts={() => contacts && openCustomerContracts(contacts)}
        onNewContract={() => contacts && openCustomerContractCreate(contacts)}
        onCreateCustomerEvent={createCustomerEvent}
      />

      {/* 各种小 Modal */}
      <CustomerModals
        viewingContact={viewingContact}
        onCloseViewContact={() => setViewingContact(null)}
        contactPhotoPreview={contactPhotoPreview}
        onCloseContactPhotoPreview={handleCloseContactPhotoPreview}
        customerDocumentPreview={customerDocumentPreview}
        onCloseCustomerDocumentPreview={handleCloseCustomerDocumentPreview}
        newEditorOpen={Boolean(newEditor)}
        newEditorType={newEditor}
        contactForm={contactForm}
        onCloseNewEditor={() => setNewEditor(null)}
        onAddContact={addContact}
        editingContact={editingContact}
        contactEditForm={contactEditForm}
        onCloseEditContact={handleCloseEditContact}
        onUpdateContact={updateContact}
        noteForm={noteForm}
        onAddNote={addNote}
        editingNote={editingNote}
        noteEditForm={noteEditForm}
        onCloseEditNote={handleCloseEditNote}
        onUpdateNote={updateNote}
        documentForm={documentForm}
        documentFileRef={documentFileRef}
        documentFile={documentFile}
        onDocumentFileChange={setDocumentFile}
        onUploadDocument={uploadDocument}
        portalResult={portalResult}
        onClosePortalResult={() => setPortalResult(null)}
        portalCustomer={portalCustomer}
        portalAccounts={portalAccounts}
        onClosePortalCustomer={() => setPortalCustomer(null)}
        onOpenPortal={openPortal}
        assigning={assigning}
        assignForm={assignForm}
        directoryOptions={directoryOptions}
        directory={directory}
        onCloseAssign={() => setAssigning(null)}
        onAssignCustomer={assignCustomer}
        sharing={sharing}
        shareForm={shareForm}
        onCloseShare={() => setSharing(null)}
        onShare={share}
      />

    </>
  );
}

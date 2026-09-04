import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  AutoComplete,
  Button,
  Card,
  Cascader,
  Checkbox,
  DatePicker,
  Descriptions,
  Dropdown,
  Drawer,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Radio,
  Select,
  Space,
  Steps,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  CheckCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  FileSearchOutlined,
  ImportOutlined,
  PaperClipOutlined,
  PlusOutlined,
  ReloadOutlined,
  TeamOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { useCascaderAreaData } from "@vant/area-data";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { consumeInvestigationDetailTarget } from "./investigationDetailNavigation";
import { rememberInvestigationDetailTarget } from "./investigationDetailNavigation";
import { formatRequiredDate } from "./formSafety";
import { INVESTIGATION_REGION_GROUPS } from "./investigationRegionOptions.mjs";
import {
  COLLECTED_CLUE_STATUSES,
  clueCaseNo,
  clueInvestigatorSearchText,
} from "./investigationCollectedClueParity.mjs";
import "./investigation-center.css";

type Row = {
  id: number;
  module: string;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  description?: string;
  data: Record<string, any>;
  updated_at: string;
};
type Attachment = {
  id: number;
  category: string;
  original_name: string;
  size: number;
  uploader: string;
  uploader_display_name?: string;
  created_at: string;
};
type ClueEvidenceRow = Row & {
  files: Attachment[];
  can_edit: boolean;
  can_delete: boolean;
};
type ClueWorkspace = {
  clue: Row;
  clue_files: Attachment[];
  evidence: ClueEvidenceRow[];
};
type Contract = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
};
type ResolvedClueContract = {
  clue_id: number;
  clue_no?: string;
  clue_title?: string;
  customer?: string;
  contract?: Contract | null;
  error?: string;
};
type TaskRow = {
  id: number;
  serial_no: string;
  title: string;
  status: string;
  owner: string;
  owner_display_name?: string;
  owner_display_name_missing?: boolean;
  deadline: string;
  priority: string;
  parent_task_id?: number;
  parent_task_no?: string;
  investigation_no?: string;
  data?: Record<string, unknown>;
};
type Profile = {
  username: string;
  display_name: string;
  role: string;
  role_ids?: string[];
  department?: string;
};
type PersonOption = {
  value: string;
  label: string;
  username?: string;
  search_text?: string;
};
type InvestigationActions = {
  review_clue: boolean;
  review_customer_clue: boolean;
  review_notary: boolean;
  register_notary_certificate: boolean;
};
const isLegacyInvestigationRecord = (row: Row | null) => {
  const data = row?.data || {};
  return Boolean(
    data.migration_source ||
      data.legacy_investigation_id ||
      data.legacy_record,
  );
};
type InvestigationBootstrapData = {
  profile: Profile;
  assignmentSupervisor: string;
  notaryOfficeOptions: { value: string }[];
  casePeopleOptions: PersonOption[];
  warehouseCatalog: WarehouseCatalogItem[];
};
type WarehouseStorageLocation = { id: number; name: string; is_active: boolean };
type WarehouseCatalogItem = { id: number; name: string; is_active: boolean; locations: WarehouseStorageLocation[] };

type InvestigationRegionGroup = {
  province: string;
  cities: string[];
};
type AdministrativeRegionOption = {
  text: string;
  value: string;
  children?: AdministrativeRegionOption[];
};

const INVESTIGATION_ADMINISTRATIVE_REGIONS = useCascaderAreaData() as AdministrativeRegionOption[];

const investigationAdministrativeCity = (province: string, city: string) => {
  const cities = INVESTIGATION_ADMINISTRATIVE_REGIONS.find(
    (item) => item.text === province,
  )?.children || [];
  // The legacy contract scope represents municipalities as "市辖区", while the
  // national division data names their only city node after the municipality.
  if (city === "市辖区" && cities.length === 1) return cities[0];
  return cities.find((item) => item.text === city);
};

const investigationDistrictsForCity = (province: string, city: string) =>
  investigationAdministrativeCity(province, city)?.children?.map((item) => item.text) || [];

const investigationTaskRegionOptions = (groups: InvestigationRegionGroup[]) =>
  groups.map(({ province, cities }) => ({
    value: province,
    label: province,
    children: cities.map((city) => ({
      value: city,
      label: city,
      children: investigationDistrictsForCity(province, city).map((district) => ({
        value: district,
        label: district,
      })),
    })),
  }));

const CLUE_INFRINGEMENT_METHOD_OPTIONS = [
  "电商平台",
  "实体店铺",
  "工厂",
  "网页链接",
  "其他",
];
const CLUE_SALES_CHANNEL_OPTIONS = [
  "淘宝",
  "天猫",
  "京东",
  "拼多多",
  "抖音",
  "快手",
  "小红书",
  "微信",
  "官网",
  "线下门店",
  "其他",
];

const investigationTaskScopeGroups = (data: Record<string, any>) => {
  const scope = String(data.authorization_scope || "").trim();
  const scopeTokens = scope
    .split(/[\s,，、;；|/]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  const groups = INVESTIGATION_REGION_GROUPS as InvestigationRegionGroup[];
  if (["全国", "全国范围"].includes(scope) || scopeTokens.includes("全国")) return groups;

  const scopeIncludes = (value: string) =>
    scopeTokens.includes(value) || scope.includes(value);

  const scopedGroups = groups
    .map(({ province, cities }) => {
      const provinceSelected = scopeIncludes(province);
      const selectedCities = provinceSelected
        ? cities
        : cities.filter((city) => scopeIncludes(city));
      return { province, cities: selectedCities };
    })
    .filter((group) => group.cities.length > 0);
  if (scopedGroups.length) return scopedGroups;

  const inheritedProvince = String(data.province || "").trim();
  const inheritedCity = String(data.city || "").trim();
  const inheritedGroup = groups.find((group) => group.province === inheritedProvince);
  if (inheritedGroup) {
    return [{
      province: inheritedGroup.province,
      cities: inheritedCity && inheritedGroup.cities.includes(inheritedCity)
        ? [inheritedCity]
        : inheritedGroup.cities,
    }];
  }
  return groups;
};
const loadInvestigationBootstrap = () =>
  Promise.all([
      api.get("/auth/me").then(({ data }) => data as Profile),
      api.get("/investigations/assignment-supervisor")
        .then(({ data }) => String(data.username || ""))
        .catch(() => ""),
      api.get("/system/parameters/options", { params: { category: "notary_office" } })
        .then(({ data }) =>
          (data.items || [])
            .map((item: { name?: string }) => ({ value: String(item.name || "").trim() }))
            .filter((item: { value: string }) => item.value),
        )
        .catch(() => [] as { value: string }[]),
      api.get("/people/options")
        .then(({ data }) => data.items || [])
        .catch(() => [] as PersonOption[]),
      api.get("/warehouse/catalog")
        .then(({ data }) => data.items || [])
        .catch(() => [] as WarehouseCatalogItem[]),
  ]).then(([profile, assignmentSupervisor, notaryOfficeOptions, casePeopleOptions, warehouseCatalog]) => ({
    profile, assignmentSupervisor, notaryOfficeOptions, casePeopleOptions, warehouseCatalog,
  }));
type SubtaskLifecycleAction = "accept" | "complete";
const investigationListView = (route: string) => {
  if (
    route === "investigation-task-unassigned" ||
    route === "investigation-task-sub-mine"
  )
    return "assigned";
  if (
    route === "investigation-task-published" ||
    route === "investigation-task-overdue" ||
    route === "investigation-task-sub-published"
  )
    return "published";
  if (route === "investigation-task-mine") return "published";
  return "";
};

const clueStatusesByRoute: Record<string, string[]> = {
  "clue-my-draft": ["草稿"],
  "clue-my-pending": ["待审批"],
  "clue-my-customer": ["待客户审核"],
  "clue-my-collect": ["待取证"],
  "clue-my-collected": [...COLLECTED_CLUE_STATUSES],
  "clue-my-refused": ["已驳回", "已拒绝"],
  "clue-audit-pending": ["待审批"],
  "clue-audit-customer": ["待客户审核"],
  "clue-audit-refused": ["已驳回", "已拒绝"],
  "clue-audit-collect": ["待取证"],
  "clue-audit-collected": [...COLLECTED_CLUE_STATUSES],
  "clue-company-draft": ["草稿"],
  "clue-company-pending": ["待审批"],
  "clue-company-collect": ["待取证"],
  "clue-company-collected": [...COLLECTED_CLUE_STATUSES],
  "clue-company-refused": ["已驳回", "已拒绝"],
};
const moduleMeta = {
  investigation: {
    title: "调查任务",
    prefix: "DC",
    statuses: ["待分配", "进行中", "已完成", "已取消"],
  },
  clue: {
    title: "调查线索",
    prefix: "XS",
    statuses: [
      "草稿",
      "待审批",
      "待取证",
      "已取证",
      "待公证",
      "已转案件",
      "已驳回",
    ],
  },
  notary: {
    title: "公证审核",
    prefix: "GZ",
    statuses: ["等待材料", "待审核", "审核通过", "审核驳回"],
  },
  evidence: {
    title: "证据材料",
    prefix: "ZJ",
    statuses: ["待整理", "已整理", "已入卷"],
  },
};
const statusColors: Record<string, string> = {
  待分配: "orange",
  进行中: "blue",
  已完成: "green",
  已取消: "red",
  待审批: "orange",
  待客户审核: "gold",
  待取证: "cyan",
  已取证: "blue",
  待公证: "purple",
  已转案件: "green",
  等待材料: "gold",
  审核通过: "green",
  审核驳回: "red",
  待审核: "orange",
  已入卷: "green",
};
const serial = (prefix: string) =>
  prefix + new Date().toISOString().replace(/\D/g, "").slice(0, 14);

export default function InvestigationCenterPage({
  initialTab,
  onNavigate,
}: {
  initialTab: string;
  onNavigate?: (route: string) => void;
}) {
  const initial = (
    initialTab.startsWith("notary")
      ? "notary"
      : initialTab.startsWith("evidence")
        ? "evidence"
        : initialTab.startsWith("investigation-task-")
          ? "investigation"
          : "clue"
  ) as keyof typeof moduleMeta;
  const [profile, setProfile] = useState<Profile>({
    username: "",
    display_name: "",
    role: "",
  });
  const [assignmentSupervisor, setAssignmentSupervisor] = useState("");
  const [notaryOfficeOptions, setNotaryOfficeOptions] = useState<
    { value: string }[]
  >([]);
  const [casePeopleOptions, setCasePeopleOptions] = useState<PersonOption[]>([]);
  const [warehouseCatalog, setWarehouseCatalog] = useState<WarehouseCatalogItem[]>([]);
  const [investigationActions, setInvestigationActions] = useState<
    Record<string, InvestigationActions>
  >({});
  const [tab, setTab] = useState<keyof typeof moduleMeta>(initial);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [investigationCreateOpen, setInvestigationCreateOpen] = useState(false);
  const [clueCreateOpen, setClueCreateOpen] = useState(false);
  const [clueFiles, setClueFiles] = useState<File[]>([]);
  const [collectionFiles, setCollectionFiles] = useState<File[]>([]);
  const [reviewing, setReviewing] = useState<Row | null>(null);
  const [clueReviewing, setClueReviewing] = useState<Row | null>(null);
  const [batchSubmitOpen, setBatchSubmitOpen] = useState(false);
  const [turnOnAuditTarget, setTurnOnAuditTarget] = useState<Row | null>(null);
  const [reviewerCandidates, setReviewerCandidates] = useState<PersonOption[]>([]);
  const [reviewerCandidatesLoading, setReviewerCandidatesLoading] = useState(false);
  const [collectionTarget, setCollectionTarget] = useState<Row | null>(null);
  const [batchCollectionTargets, setBatchCollectionTargets] = useState<Row[]>([]);
  const [evidenceSource, setEvidenceSource] = useState<Row | null>(null);
  const [certificateTarget, setCertificateTarget] = useState<Row | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importReference, setImportReference] = useState("");
  const [importResult, setImportResult] = useState<{
    created: number;
    failed: number;
    errors: { row: number; error: string }[];
  } | null>(null);
  const [importPreviewRows, setImportPreviewRows] = useState<
    Record<string, unknown>[]
  >([]);
  const [selectedClues, setSelectedClues] = useState<number[]>([]);
  const [batchOpen, setBatchOpen] = useState(false);
  const [resolvedClueContracts, setResolvedClueContracts] = useState<
    ResolvedClueContract[]
  >([]);
  const [contractOptions, setContractOptions] = useState<Contract[]>([]);
  const [batchStep, setBatchStep] = useState(0);
  const [validatedBatchCaseValues, setValidatedBatchCaseValues] = useState<Record<string, any> | null>(null);
  const [materialOpen, setMaterialOpen] = useState(false);
  const [materialTarget, setMaterialTarget] = useState<Row | null>(null);
  const [materials, setMaterials] = useState<Attachment[]>([]);
  const [allowedCategories, setAllowedCategories] = useState<string[]>([]);
  const [materialFiles, setMaterialFiles] = useState<File[]>([]);
  const [taskTarget, setTaskTarget] = useState<Row | null>(null);
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [creatingSubtask, setCreatingSubtask] = useState(false);
  const [subtaskActionTarget, setSubtaskActionTarget] = useState<{
    row: Row;
    action: SubtaskLifecycleAction;
  } | null>(null);
  const [editTarget, setEditTarget] = useState<Row | null>(null);
  const [assignTarget, setAssignTarget] = useState<Row | null>(null);
  const [feeTarget, setFeeTarget] = useState<Row | null>(null);
  const [investigationDetail, setInvestigationDetail] = useState<Row | null>(
    null,
  );
  const [clueWorkspace, setClueWorkspace] = useState<ClueWorkspace | null>(null);
  const [clueWorkspaceLoading, setClueWorkspaceLoading] = useState(false);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<number | null>(null);
  const [editingEvidence, setEditingEvidence] = useState<ClueEvidenceRow | null>(null);
  const [linkedCase, setLinkedCase] = useState<Row | null>(null);
  const [createContextTask, setCreateContextTask] = useState<Row | null>(null);
  const [createModule, setCreateModule] =
    useState<keyof typeof moduleMeta>(initial);
  const [listQuery, setListQuery] = useState<Record<string, any>>({});
  const [createForm] = Form.useForm();
  const [reviewForm] = Form.useForm();
  const [clueReviewForm] = Form.useForm();
  const [batchSubmitForm] = Form.useForm();
  const [turnOnAuditForm] = Form.useForm();
  const [collectionForm] = Form.useForm();
  const [evidenceForm] = Form.useForm();
  const [certificateForm] = Form.useForm();
  const [taskForm] = Form.useForm();
  const taskProvince = Form.useWatch("province", taskForm);
  const taskCity = Form.useWatch("city", taskForm);
  const [subtaskActionForm] = Form.useForm();
  const [materialForm] = Form.useForm();
  const [batchForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [assignForm] = Form.useForm();
  const [feeForm] = Form.useForm();
  const [evidenceEditForm] = Form.useForm();
  const certificateWarehouseId = Form.useWatch("warehouse_id", certificateForm) as number | undefined;
  const storageLocationOptions = (warehouseId: number | undefined) =>
    (warehouseCatalog.find((warehouse) => warehouse.id === Number(warehouseId))?.locations || [])
      .filter((location) => location.is_active)
      .map((location) => ({ value: location.id, label: location.name }));
  const collectionStorageOptions = warehouseCatalog
    .filter((warehouse) => warehouse.is_active)
    .map((warehouse) => ({
      value: warehouse.id,
      label: warehouse.name,
      children: warehouse.locations
        .filter((location) => location.is_active)
        .map((location) => ({ value: location.id, label: location.name })),
    }))
    .filter((warehouse) => warehouse.children.length > 0);
  const personDisplayName = (value: unknown) => {
    const raw = String(value || "").trim();
    if (!raw) return "—";
    const matched = casePeopleOptions.find(
      (item) =>
        item.username === raw ||
        item.value === raw ||
        item.label === raw,
    );
    return matched?.label || "姓名待维护";
  };
  const projectedPersonDisplayName = (displayName: unknown, username: unknown) => {
    const projected = String(displayName || "").trim();
    if (projected && projected !== String(username || "").trim()) return projected;
    const matched = casePeopleOptions.find(
      (item) =>
        item.username === String(username || "").trim() ||
        item.value === String(username || "").trim(),
    );
    return matched?.label || personDisplayName(username);
  };
  const systemPersonOptions = casePeopleOptions.map((item) => ({
    value: item.username || item.value,
    label: item.label,
  }));
  const systemPersonValue = (value: unknown) => {
    const raw = String(value || "").trim();
    const matched = casePeopleOptions.find(
      (item) => item.username === raw || item.value === raw || item.label === raw,
    );
    return matched?.username || matched?.value || raw;
  };
  const resetTaskForm = (target: Row) => {
    const allowedGroups = investigationTaskScopeGroups(target.data || {});
    const inheritedProvince = String(target.data.province || "").trim();
    const province = allowedGroups.some((group) => group.province === inheritedProvince)
      ? inheritedProvince
      : "";
    const provinceGroup = allowedGroups.find((group) => group.province === province);
    const inheritedCity = String(target.data.city || "").trim();
    const city = provinceGroup?.cities.includes(inheritedCity) ? inheritedCity : "";
    const inheritedDistrict = String(target.data.district || "").trim();
    const district = investigationDistrictsForCity(province, city).includes(inheritedDistrict)
      ? inheritedDistrict
      : "";
    taskForm.resetFields();
    taskForm.setFieldsValue({
      title: `${target.title || target.serial_no} - 调查子任务`,
      priority: "普通",
      start_date: target.data.authorized_from
        ? dayjs(String(target.data.authorized_from))
        : undefined,
      end_date: target.data.authorized_to
        ? dayjs(String(target.data.authorized_to))
        : undefined,
      deadline: target.data.authorized_to
        ? dayjs(String(target.data.authorized_to))
        : undefined,
      authorization_scope: String(target.data.authorization_scope || "").trim(),
      province,
      city,
      district,
      region_path: province && city ? [province, city, ...(district ? [district] : [])] : [],
      contract_record_id:
        target.data.contract_id || target.data.contract_record_id || undefined,
    });
  };
  const load = async (key = tab) => {
    setLoading(true);
    try {
      const module = initialTab.startsWith("investigation-task-sub-")
        ? "task"
        : initialTab.startsWith("investigation-task-")
          ? "investigation"
          : key;
      const { data } =
        initialTab === "notary-query-files"
          ? await api.get("/investigations/notaries/files")
          : await api.get("/records", {
              params: {
                module,
                page_size: 100,
                scope:
                  initialTab.includes("-my-") ||
                  (initialTab.startsWith("investigation-task-") &&
                  !initialTab.startsWith("investigation-task-sub-"))
                    ? "mine"
                    : "all",
                investigation_view: investigationListView(initialTab),
                statuses: (clueStatusesByRoute[initialTab] || []).join(","),
              },
            });
      const loadedRows = data.items as Row[];
      setRows(loadedRows);
      setInvestigationActions({});
      const target = consumeInvestigationDetailTarget();
      if (target) {
        let targetRow = loadedRows.find(
          (row) =>
            (target.id && row.id === target.id) ||
            (target.serial_no && row.serial_no === target.serial_no),
        );
        if (!targetRow && target.id) {
          try {
            const detail = await api.get(`/records/${target.id}`);
            if (detail.data.module === target.module || !target.module)
              targetRow = detail.data;
          } catch {
            /* Keep the serial-number fallback for scoped or stale IDs. */
          }
        }
        if (!targetRow && target.serial_no) {
          const res = await api.get("/records", {
            params: {
              module: target.module || module,
              keyword: target.serial_no,
              page_size: 100,
            },
          });
          targetRow = (res.data.items as Row[]).find(
            (row) => row.serial_no === target.serial_no,
          );
        }
        if (targetRow) setInvestigationDetail(targetRow);
        else message.warning("未找到关联调查记录或当前账号无权查看");
      }
      const capabilityRows = loadedRows.filter(
        (row) => row.module === "clue" || row.module === "notary",
      );
      if (capabilityRows.length)
        void api
          .get("/investigations/action-capabilities", {
            params: {
              record_ids: capabilityRows.map((row) => row.id).join(","),
            },
          })
          .then((capabilities) =>
            setInvestigationActions(capabilities.data.items || {}),
          )
          .catch(() => message.warning("调查操作权限加载失败，详情仍可查看"));
    } catch {
      message.error("调查中心数据加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    const bootstrap = async () => {
      setTab(initial);
      setCreateModule(initial);
      setListQuery({});
      setSelectedClues([]);
      await Promise.all([
        load(initial),
        loadInvestigationBootstrap().then((bootstrapData) => {
          setProfile(bootstrapData.profile);
          setAssignmentSupervisor(bootstrapData.assignmentSupervisor);
            setNotaryOfficeOptions(bootstrapData.notaryOfficeOptions);
            setCasePeopleOptions(bootstrapData.casePeopleOptions);
            setWarehouseCatalog(bootstrapData.warehouseCatalog);
        }).catch(() =>
          message.error("调查辅助数据加载失败，业务列表仍可正常使用"),
        ),
      ]);
    };
    void bootstrap();
  }, [initialTab]);
  const visibleRows = useMemo(() => {
    let result = rows;
    const statuses = clueStatusesByRoute[initialTab] || [];
    if (statuses.length)
      result = result.filter((row) => statuses.includes(row.status));
    if (initialTab === "investigation-task-published" && profile.role !== "admin") {
      const names = [profile.username, profile.display_name].filter(Boolean);
      result = result.filter((row) =>
        names.includes(String(row.data.publisher || row.owner || "")),
      );
    }
    if (initialTab.startsWith("investigation-task-sub-"))
      result = result.filter((row) =>
        Boolean(
          row.data.investigation_record_id ||
          row.data.investigation_no ||
          row.data.investigation_module,
        ),
      );
    if (
      initialTab === "investigation-task-sub-published" &&
      profile.role !== "admin" &&
      Boolean(profile.username)
    ) {
      const names = [profile.username, profile.display_name].filter(Boolean);
      result = result.filter((row) =>
        names.includes(String(row.data.initiator || row.data.publisher || "")),
      );
    }
    if (
      initialTab === "investigation-task-sub-mine" &&
      profile.role !== "admin" &&
      Boolean(profile.username)
    ) {
      const names = [profile.username, profile.display_name].filter(Boolean);
      result = result.filter((row) => names.includes(row.owner));
    }
    if (initialTab === "investigation-task-overdue")
      result = result.filter(
        (row) =>
          Boolean(row.data.authorized_to) &&
          dayjs(String(row.data.authorized_to)).isBefore(dayjs(), "day") &&
          !["已完成", "已取消"].includes(row.status),
      );
    if (initialTab === "investigation-task-unassigned") {
      const supervisor = assignmentSupervisor || profile.username;
      result = result.filter(
        (row) =>
          Boolean(supervisor) &&
          row.owner === supervisor &&
          !["已完成", "已取消"].includes(row.status),
      );
    }
    if (
      initialTab.includes("-my-") &&
      Boolean(profile.username)
    ) {
      result = result.filter(
        (row) =>
          String(row.owner || "").toLocaleLowerCase() ===
          String(profile.username).toLocaleLowerCase(),
      );
    }
    if (initialTab.endsWith("-no-fee"))
      result = result.filter(
        (row) => !row.data.fee_application_id && !row.data.fee_no,
      );
    else if (initialTab.endsWith("-fee"))
      result = result.filter((row) =>
        Boolean(row.data.fee_application_id || row.data.fee_no),
      );
    const d = (row: Row) => row.data || {},
      contains = (value: unknown, key: string) =>
        !listQuery[key] ||
        String(value || "")
          .toLocaleLowerCase()
          .includes(String(listQuery[key]).trim().toLocaleLowerCase());
    const inRange = (value: unknown, key: string) => {
      const range = listQuery[key];
      if (!range?.[0] || !range?.[1] || !value)
        return !range?.[0] && !range?.[1];
      const current = dayjs(String(value));
      return (
        current.isValid() &&
        !current.isBefore(range[0], "day") &&
        !current.isAfter(range[1], "day")
      );
    };
    result = result.filter((row) => {
      const data = d(row),
        hasCase = Boolean(
          data.case_no || data.converted_case_no || data.converted_case_id,
        );
      const evidenceStatus =
        data.evidence_status ||
        data.warehouse_status ||
        data.storage_status ||
        "";
      return (
        contains(row.serial_no, "serial_no") &&
        contains(
          clueInvestigatorSearchText(row, personDisplayName(row.owner)),
          "investigator",
        ) &&
        contains(row.customer, "rights_holder") &&
        contains(data.region || data.address, "region") &&
        contains(row.title, "shop_name") &&
        contains(
          data.warehouse || data.certificate_storage_location,
          "warehouse",
        ) &&
        contains(data.certificate_no, "certificate_no") &&
        contains(clueCaseNo(row), "case_no") &&
        contains(data.document_type, "document_type") &&
        contains(data.handler, "handler") &&
        contains(data.invoice_no, "invoice_no") &&
        contains(data.notary_institution, "notary_institution") &&
        contains(
          data.infringement_method || data.platform,
          "infringement_method",
        ) &&
        contains(data.address, "shop_address") &&
        (!listQuery.right_type ||
          listQuery.right_type === "全部" ||
          data.right_type === listQuery.right_type) &&
        (!listQuery.evidence_status ||
          evidenceStatus === listQuery.evidence_status) &&
        (!listQuery.case_status ||
          listQuery.case_status === "全部" ||
          (listQuery.case_status === "已生成案件" ? hasCase : !hasCase)) &&
        inRange(
          data.authorized_from || data.authorized_to,
          "authorized_range",
        ) &&
        inRange(
          data.investigated_at || data.started_at || data.ended_at,
          "investigation_range",
        ) &&
        inRange(data.imported_at || row.updated_at, "import_range") &&
        inRange(data.collected_at, "collection_range")
      );
    });
    return result;
  }, [rows, initialTab, profile, listQuery]);
  const create = async (submitAfterCreate = false) => {
    const values = await createForm.validateFields();
    const targetModule = createModule;
    const meta = moduleMeta[targetModule];
    const initialStatus =
      targetModule === "clue"
        ? "草稿"
        : targetModule === "evidence"
          ? "待整理"
          : targetModule === "notary"
            ? "待审核"
            : targetModule === "investigation"
              ? "待分配"
              : values.status;
    try {
      const { data: created } = await api.post("/investigations/records", {
        module: targetModule,
        serial_no: targetModule === "clue" ? "" : values.serial_no,
        title: values.title,
        customer: values.customer || "",
        status: initialStatus,
        owner: values.owner || profile.username || "admin",
        department: profile.department || "上海分所",
        description: values.description || "",
        data: {
          product: values.product || "",
          source: values.source || "",
          source_task_id: createContextTask?.id || null,
          source_task_no: createContextTask?.serial_no || "",
          publisher: profile.username || "admin",
          source_owner:
            values.source_owner ||
            profile.display_name ||
            profile.username ||
            "",
          region: values.region || "",
          address: values.address || "",
          right_type: values.right_type || "",
          infringement_method: values.infringement_method || "",
          sales_channel: values.sales_channel || "",
          // Keep platform populated for existing exports and downstream evidence flows.
          platform: values.sales_channel || "",
          store_url: values.store_url || "",
          shop_name: values.shop_name || "",
          shop_id: values.shop_id || "",
          has_product: Boolean(values.has_product),
          product_url: values.product_url || "",
          sale_num: values.sale_num || "",
          investigated_at: values.investigated_at
            ? formatRequiredDate(values.investigated_at, "调查日期")
            : "",
          producer: values.producer || "",
          indictee: values.indictee || "",
          investigation_assistant: values.investigation_assistant || "",
          authorized_from:
            targetModule === "investigation"
              ? formatRequiredDate(values.authorized_from, "授权开始日期")
              : undefined,
          authorized_to:
            targetModule === "investigation"
              ? formatRequiredDate(values.authorized_to, "授权结束日期")
              : undefined,
          customer_review:
            targetModule === "clue"
              ? Boolean(createContextTask?.data.customer_review)
              : Boolean(values.customer_review),
        },
      });
      if (targetModule === "clue" && clueFiles.length) {
        for (const file of clueFiles) {
          const form = new FormData();
          form.append("file", file);
          form.append("record_id", String(created.id));
          form.append("category", "调查线索附件");
          form.append("remark", "新建线索附件");
          await api.post("/attachments", form);
        }
      }
      if (targetModule === "clue" && submitAfterCreate) {
        await api.post(`/investigations/clues/${created.id}/submit`, {
          comment: "提交线索审批",
        });
      }
      message.success(`${meta.title}已创建`);
      setCreateOpen(false);
      setInvestigationCreateOpen(false);
      setClueCreateOpen(false);
      setCreateContextTask(null);
      setCreateModule(tab);
      setClueFiles([]);
      createForm.resetFields();
      load(targetModule === "clue" ? "clue" : tab);
    } catch (error: any) {
      message.error(
        error?.response?.data?.detail || error?.message || "创建失败",
      );
    }
  };
  const submitClue = async (row: Row) => {
    try {
      await api.post(`/investigations/clues/${row.id}/submit`, {
        comment: "提交线索审批",
      });
      message.success("线索已提交审批");
      load("clue");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "提交失败");
    }
  };
  const openBatchSubmit = () => {
    if (!selectedRows.length) {
      message.warning("请至少勾选一条待提交线索");
      return;
    }
    if (
      selectedRows.some(
        (row) =>
          row.module !== "clue" || !["草稿", "已驳回"].includes(row.status),
      )
    ) {
      message.warning("仅可批量提交草稿或已驳回线索");
      return;
    }
    batchSubmitForm.resetFields();
    batchSubmitForm.setFieldsValue({ comment: "批量提交线索审批" });
    setBatchSubmitOpen(true);
  };
  const submitCluesBatch = async () => {
    const values = await batchSubmitForm.validateFields();
    try {
      const { data } = await api.post("/investigations/clues/batch-submit", {
        clue_ids: selectedRows.map((row) => row.id),
        comment: String(values.comment || "").trim(),
      });
      message.success(`已提交 ${data.updated || selectedRows.length} 条线索审批`);
      setBatchSubmitOpen(false);
      setSelectedClues([]);
      load("clue");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量提交失败");
    }
  };
  const openTurnOnAudit = async (row: Row) => {
    setTurnOnAuditTarget(row);
    setReviewerCandidates([]);
    turnOnAuditForm.resetFields();
    setReviewerCandidatesLoading(true);
    try {
      const { data } = await api.get(
        `/investigations/clues/${row.id}/reviewer-candidates`,
      );
      setReviewerCandidates(
        (data.items || []).map((item: PersonOption & { display_name?: string }) => ({
          value: item.username || item.value,
          username: item.username || item.value,
          label: item.label || item.display_name || item.username || item.value,
        })),
      );
    } catch (error: any) {
      setTurnOnAuditTarget(null);
      message.error(error?.response?.data?.detail || "审核人候选列表加载失败");
    } finally {
      setReviewerCandidatesLoading(false);
    }
  };
  const saveTurnOnAudit = async () => {
    if (!turnOnAuditTarget) return;
    const values = await turnOnAuditForm.validateFields();
    try {
      await api.post(
        `/investigations/clues/${turnOnAuditTarget.id}/turn-on-audit`,
        {
          reviewer: values.reviewer,
          comment: String(values.comment || "").trim(),
        },
      );
      message.success("线索已转交审核人");
      setTurnOnAuditTarget(null);
      load("clue");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "转交审核人失败");
    }
  };
  const reviewClue = async () => {
    if (!clueReviewing) return;
    const v = await clueReviewForm.validateFields();
    const customerReview = clueReviewing.status === "待客户审核";
    try {
      await api.post(
        `/investigations/clues/${clueReviewing.id}/${customerReview ? "customer-review" : "review"}`,
        v,
      );
      message.success(
        v.approved
          ? customerReview
            ? "客户审核通过，进入待取证"
            : "内部审核已通过"
          : "线索已驳回",
      );
      setClueReviewing(null);
      clueReviewForm.resetFields();
      load("clue");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "线索审核失败");
    }
  };
  const registerCollection = async () => {
    if (!collectionTarget && batchCollectionTargets.length === 0) return;
    const uploadedIds: number[] = [];
    try {
      const v = await collectionForm.validateFields();
      for (const file of collectionFiles) {
        const form = new FormData();
        form.append("file", file);
        form.append("record_id", String(collectionTarget!.id));
        form.append("category", "取证文件");
        form.append("remark", "线索取证登记附件");
        const { data } = await api.post("/attachments", form);
        uploadedIds.push(data.id);
      }
      const payload = {
        ...v,
        evidence_file_ids: uploadedIds,
        collected_at: formatRequiredDate(v.collected_at, "取证日期"),
      };
      if (batchCollectionTargets.length > 0) {
        const { data } = await api.post("/investigations/clues/batch-collect", {
          ...payload,
          clue_ids: batchCollectionTargets.map((row) => row.id),
        });
        message.success(`已为 ${data.collected} 条线索批量登记取证`);
      } else {
        await api.post(`/investigations/clues/${collectionTarget!.id}/collect`, payload);
        message.success("取证信息已登记，线索进入已取证");
      }
      setCollectionTarget(null);
      setBatchCollectionTargets([]);
      setSelectedClues([]);
      setCollectionFiles([]);
      load("clue");
    } catch (error: any) {
      await Promise.all(uploadedIds.map((id) => api.delete(`/attachments/${id}`)));
      if (error?.errorFields) return;
      message.error(
        error?.response?.data?.detail || error?.message || "取证登记失败",
      );
    }
  };
  const openSingleCollection = (row: Row) => {
    collectionForm.resetFields();
    collectionForm.setFieldsValue({
      warehouse_id: Number(row.data.warehouse_id) || undefined,
      storage_location_id: Number(row.data.storage_location_id) || undefined,
      evidence_storage_path:
        row.data.warehouse_id && row.data.storage_location_id
          ? [Number(row.data.warehouse_id), Number(row.data.storage_location_id)]
          : undefined,
    });
    setCollectionFiles([]);
    setBatchCollectionTargets([]);
    setCollectionTarget(row);
  };
  const openBatchCollection = () => {
    const targets = rows.filter((row) => selectedClues.includes(row.id));
    if (targets.length < 2) return message.warning("请至少选择两条待取证线索");
    const invalid = targets.filter((row) => row.status !== "待取证");
    if (invalid.length > 0) return message.warning(`仅待取证线索可批量办理：${invalid.map((row) => row.serial_no).join("、")}`);
    collectionForm.resetFields();
    setCollectionFiles([]);
    setCollectionTarget(null);
    setBatchCollectionTargets(targets);
  };
  const createEvidence = async () => {
    if (!evidenceSource) return;
    const v = await evidenceForm.validateFields();
    try {
      await api.post(`/investigations/clues/${evidenceSource.id}/evidence`, v);
      message.success("证据目录已建立");
      setEvidenceSource(null);
      evidenceForm.resetFields();
      if (onNavigate) onNavigate("evidence");
      else {
        setTab("evidence");
        load("evidence");
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "建立证据目录失败");
    }
  };
  const evidenceAction = async (row: Row, action: "organize" | "file") => {
    try {
      await api.post(`/investigations/evidence/${row.id}/${action}`, {
        comment: action === "organize" ? "证据整理完成" : "证据材料入卷",
      });
      message.success(action === "organize" ? "证据已整理" : "证据已入卷");
      load("evidence");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "证据操作失败");
    }
  };
  const registerCertificate = async () => {
    if (!certificateTarget) return;
    try {
      const v = await certificateForm.validateFields();
      await api.post(`/notaries/${certificateTarget.id}/certificate`, {
        ...v,
        issued_date: formatRequiredDate(v.issued_date, "签发日期"),
      });
      message.success("公证书编号及存放信息已登记");
      setCertificateTarget(null);
      certificateForm.resetFields();
      load("notary");
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(
        error?.response?.data?.detail || error?.message || "公证书登记失败",
      );
    }
  };
  const applyNotary = async (row: Row) => {
    try {
      const { data } = await api.post(`/investigations/${row.id}/notary`);
      message.success(`已生成公证记录 ${data.serial_no}`);
      if (onNavigate) onNavigate("notary");
      else {
        setTab("notary");
        load("notary");
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "申请公证失败");
    }
  };
  const review = async () => {
    if (!reviewing) return;
    const values = await reviewForm.validateFields();
    try {
      const { data } = await api.post(
        `/notaries/${reviewing.id}/review`,
        values,
      );
      message.success(
        values.approved
          ? `审核通过，已自动生成案件 ${data.case.serial_no}`
          : "公证审核已驳回",
      );
      setReviewing(null);
      reviewForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "审核失败");
    }
  };
  const downloadImportTemplate = async () => {
    const target = tab === "notary" ? "notaries" : "clues";
    try {
      const res = await api.get(`/investigations/${target}/import-template`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = tab === "notary" ? "公证导入模板.csv" : "线索导入模板.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("模板下载失败");
    }
  };
  const importRows = async () => {
    if (!importFile) {
      message.warning("请选择上传文件");
      return;
    }
    const needsReference =
      initialTab === "notary-import-files" ||
      initialTab === "notary-import-invoices";
    if (needsReference && !importReference.trim()) {
      message.warning(
        initialTab === "notary-import-files"
          ? "请填写公证书号"
          : "请填写发票号",
      );
      return;
    }
    const form = new FormData();
    form.append("file", importFile);
    if (initialTab === "notary-import-files")
      form.append("certificate_no", importReference.trim());
    if (initialTab === "notary-import-invoices")
      form.append("invoice_no", importReference.trim());
    const endpoint: Record<string, string> = {
      "notary-import-info": "/investigations/notaries/import",
      "notary-import-storage": "/investigations/notaries/storage/import",
      "notary-import-files": "/investigations/notaries/files/import",
      "notary-import-invoices": "/investigations/notaries/invoices/import",
    };
    const target =
      endpoint[initialTab] ||
      `/investigations/${tab === "notary" ? "notaries" : "clues"}/import`;
    try {
      const { data } = await api.post(target, form);
      setImportResult(data);
      if (initialTab === "notary-import-storage")
        setImportPreviewRows(data.items || []);
      else if (
        initialTab === "notary-import-files" ||
        initialTab === "notary-import-invoices"
      )
        setImportPreviewRows([
          {
            id: data.attachment?.id,
            文件名: data.attachment?.original_name,
            案号: "",
            公证书号:
              initialTab === "notary-import-files" ? data.reference_no : "",
            发票号:
              initialTab === "notary-import-invoices" ? data.reference_no : "",
            线索编号: "",
            调查员: projectedPersonDisplayName(data.attachment?.uploader_display_name, data.attachment?.uploader),
            处理人: projectedPersonDisplayName(data.attachment?.uploader_display_name, data.attachment?.uploader),
            导入时间: data.attachment?.created_at,
          },
        ]);
      else if (Array.isArray(data.created_ids)) {
        const created = await Promise.all(
          data.created_ids.map((id: number) =>
            api.get(`/records/${id}`).then((res) => res.data),
          ),
        );
        setImportPreviewRows(
          created.map((row: any) => ({
            id: row.id,
            来源线索编号: row.data.clue_no,
            公证标题: row.title,
            负责人: projectedPersonDisplayName(row.owner_display_name, row.owner),
            审核截止日: row.data.review_due_date,
            公证书编号: row.data.certificate_no,
            签发日期: row.data.certificate_issued_date,
            存放位置: row.data.certificate_storage_location,
            实物已收: row.data.physical_received ? "是" : "否",
            说明: row.description,
          })),
        );
      }
      message.success(
        initialTab === "notary-import-storage"
          ? `成功更新 ${data.updated ?? data.created} 条公证仓库信息`
          : initialTab === "notary-import-files"
            ? `公证书文件已按公证书号匹配 ${data.record_no} 并上传`
            : initialTab === "notary-import-invoices"
              ? `发票文件已按发票号匹配 ${data.record_no} 并上传`
              : `成功导入 ${data.created} 条${tab === "notary" ? "公证记录" : "线索"}`,
      );
      setImportFile(null);
      setImportReference("");
      load(tab);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "导入失败");
    }
  };
  const openBatchCases = async () => {
    if (!selectedClues.length) {
      message.warning("请先勾选需要转案的线索");
      return;
    }
    try {
      const { data } = await api.post("/investigations/clues/case-contracts", {
        clue_ids: selectedClues,
      });
      const unresolved = (data.items || []).find(
        (item: ResolvedClueContract) => !item.contract,
      ) as ResolvedClueContract | undefined;
      if (unresolved && selectedClues.length === 1) {
        const { data: contractData } = await api.get("/records", {
          params: { module: "contract", page_size: 100 },
        });
        setContractOptions(
          contractData.items.filter(
            (contract: Contract) =>
            ["审批中", "审批通过", "已完成"].includes(
                contract.status,
              ) && contract.customer === unresolved.customer,
          ),
        );
      } else {
        setContractOptions([]);
      }
      setResolvedClueContracts(data.items || []);
      batchForm.resetFields();
      setValidatedBatchCaseValues(null);
      const selectedRows = rows.filter((row) => selectedClues.includes(row.id));
      const firstClue = selectedRows[0];
      batchForm.setFieldsValue({
        case_type: "民事案件",
        client_position: firstClue?.data.client_position || "原告",
        cause_or_charge: firstClue?.data.cause_or_charge || firstClue?.data.cause || "",
        case_phase: "等待公证书",
        handling_lawyer: profile.username || "",
        assistant: "",
      });
      setBatchStep(0);
      setBatchOpen(true);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "来源任务关联合同解析失败");
    }
  };
  const batchCases = async () => {
    if (!validatedBatchCaseValues) {
      message.error("请返回基本信息并完成必填项");
      setBatchStep(0);
      return;
    }
    try {
      const { data } = await api.post("/investigations/clues/batch-cases", {
        ...validatedBatchCaseValues,
        clue_ids: selectedClues,
      });
      if (data.failed)
        message.warning(
          `生成 ${data.created} 个案件，${data.failed} 条未处理：${data.errors
            .slice(0, 3)
            .map((x: any) => x.error)
            .join("；")}`,
        );
      else message.success(`已生成 ${data.created} 个待分配案件`);
      setBatchOpen(false);
      setSelectedClues([]);
      setResolvedClueContracts([]);
      setValidatedBatchCaseValues(null);
      setBatchStep(0);
      load("clue");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量转案失败");
    }
  };
  const bindMissingSourceContract = async () => {
    if (selectedClues.length !== 1) {
      message.warning("请一次只选择一条缺少合同绑定的历史线索");
      return;
    }
    try {
      const values = await batchForm.validateFields(["source_contract_record_id"]);
      await api.post(
        `/investigations/clues/${selectedClues[0]}/bind-source-contract`,
        { contract_record_id: values.source_contract_record_id },
      );
      const { data } = await api.post("/investigations/clues/case-contracts", {
        clue_ids: selectedClues,
      });
      setResolvedClueContracts(data.items || []);
      setContractOptions([]);
      batchForm.setFieldValue("source_contract_record_id", undefined);
      message.success("已绑定到来源调查任务，后续将自动带入合同");
      load("clue");
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || "来源任务合同绑定失败");
    }
  };
  const openMaterials = async (row: Row) => {
    setMaterialTarget(row);
    setMaterialFiles([]);
    try {
      const { data } = await api.get(`/investigations/${row.id}/materials`);
      setMaterials(data.items);
      setAllowedCategories(data.allowed_categories);
      materialForm.setFieldsValue({
        category: data.allowed_categories[0],
        remark: "",
      });
      setMaterialOpen(true);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "材料加载失败");
    }
  };
  const uploadMaterial = async () => {
    if (!materialTarget) return;
    const v = await materialForm.validateFields();
    if (!materialFiles.length) {
      message.warning("请选择材料文件");
      return;
    }
    try {
      const uploaded: Attachment[] = [];
      for (const file of materialFiles) {
        const form = new FormData();
        form.append("file", file);
        form.append("record_id", String(materialTarget.id));
        form.append("category", v.category);
        form.append("remark", v.remark || "");
        const { data } = await api.post("/attachments", form);
        uploaded.push(data);
      }
      setMaterials((x) => [...uploaded, ...x]);
      setMaterialFiles([]);
      materialForm.setFieldValue("remark", "");
      message.success(`已批量上传 ${uploaded.length} 个材料`);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "上传失败");
    }
  };
  const downloadMaterial = async (row: Attachment) => {
    try {
      const res = await api.get(`/attachments/${row.id}/download`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = row.original_name;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("材料下载失败");
    }
  };
  const deleteMaterial = async (row: Attachment) => {
    try {
      await api.delete(`/attachments/${row.id}`);
      setMaterials((x) => x.filter((item) => item.id !== row.id));
      message.success("材料已删除");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const downloadExport = async (endpoint: string, filename: string) => {
    const source = selectedRows.length ? selectedRows : visibleRows;
    if (!source.length) {
      message.warning("当前没有可导出的记录");
      return;
    }
    try {
      const ids = source.map((row) => row.id).join(",");
      const res = await api.get(endpoint, {
        params: { ids },
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("导出失败");
    }
  };
  const exportRows = (kind: "clues" | "handover") =>
    downloadExport(
      kind === "handover"
        ? "/investigations/clues/handover-export"
        : "/investigations/clues/export",
      kind === "handover" ? "调查线索交接清单.csv" : "调查线索.csv",
    );
  const openLinkedCase = async (caseNo: string) => {
    const serialNo = String(caseNo || "").trim();
    if (!serialNo) {
      message.warning("当前记录未关联案件");
      return;
    }
    try {
      const { data } = await api.get("/records", {
        params: { module: "case", keyword: serialNo, page_size: 100 },
      });
      const row = (data.items as Row[]).find(
        (item) => item.serial_no === serialNo,
      );
      if (!row) {
        message.warning("未找到关联案件或当前账号无权查看");
        return;
      }
      if (onNavigate) {
        rememberCaseDetailTarget({ id: row.id, serial_no: row.serial_no });
        onNavigate("case-company");
        return;
      }
      setLinkedCase(row);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联案件加载失败");
    }
  };
  const openLinkedCustomer = async (customerName: string) => {
    const title = String(customerName || "").trim();
    if (!title) {
      message.warning("当前记录未关联权利人");
      return;
    }
    try {
      const { data } = await api.get("/records", {
        params: { module: "customer", keyword: title, page_size: 100 },
      });
      const customer = (data.items as Row[]).find(
        (item) => item.title === title || item.customer === title,
      );
      if (!customer) {
        message.warning("未找到关联权利人档案或当前账号无权查看");
        return;
      }
      if (onNavigate) {
        rememberCustomerDetailTarget({
          id: customer.id,
          serial_no: customer.serial_no,
          title: customer.title,
        });
        onNavigate("customer-company");
        return;
      }
      message.warning("当前页面未配置客户详情跳转");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联权利人加载失败");
    }
  };
  const openLinkedNotary = async (
    recordId?: number,
    certificateNo?: string,
  ) => {
    try {
      let targetId = recordId;
      let targetNo = "";
      if (!targetId) {
        const certificate = String(certificateNo || "").trim();
        if (!certificate) {
          message.warning("当前记录未关联公证信息");
          return;
        }
        const { data } = await api.get("/notaries/lookup", {
          params: { certificate_no: certificate },
        });
        targetId = data.id;
        targetNo = data.serial_no;
      }
      if (onNavigate) {
        rememberInvestigationDetailTarget({
          id: targetId,
          serial_no: targetNo,
          module: "notary",
        });
        onNavigate("notary");
        return;
      }
      message.warning("当前页面未配置公证详情跳转");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联公证加载失败");
    }
  };
  const openLinkedInvestigation = async (
    serialNo: string,
    module: "investigation" | "clue" | "task",
  ) => {
    const no = String(serialNo || "").trim();
    if (!no) {
      message.warning(
        module === "task"
          ? "当前线索未关联来源调查任务"
          : "当前记录未关联调查编号",
      );
      return;
    }
    try {
      const { data } = await api.get("/records", {
        params: { module, keyword: no, page_size: 100 },
      });
      const target = (data.items as Row[]).find((row) => row.serial_no === no);
      if (!target) {
        message.warning(
          module === "task"
            ? "未找到来源调查任务或当前账号无权查看"
            : "未找到关联调查记录或当前账号无权查看",
        );
        return;
      }
      if (onNavigate) {
        rememberInvestigationDetailTarget({
          id: target.id,
          serial_no: target.serial_no,
          module,
        });
        onNavigate(
          module === "investigation"
            ? "investigation-task-published"
            : module === "task"
              ? "investigation-task-sub-published"
              : "clue-company-draft",
        );
        return;
      }
      message.warning("当前页面未配置调查详情跳转");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联调查记录加载失败");
    }
  };
  const openInvestigationDetail = async (row: Row) => {
    try {
      const { data } = await api.get(`/records/${row.id}`);
      setInvestigationDetail(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "调查详情加载失败");
    }
  };
  useEffect(() => {
    if (!investigationDetail || investigationDetail.module !== "clue") {
      setClueWorkspace(null);
      setSelectedEvidenceId(null);
      return;
    }
    let cancelled = false;
    setClueWorkspaceLoading(true);
    api.get(`/investigations/clues/${investigationDetail.id}/workspace`)
      .then(({ data }) => {
        if (!cancelled) {
          setClueWorkspace(data);
          setSelectedEvidenceId(null);
        }
      })
      .catch((error) => {
        if (!cancelled) message.error(error?.response?.data?.detail || "线索取证信息加载失败");
      })
      .finally(() => {
        if (!cancelled) setClueWorkspaceLoading(false);
      });
    return () => { cancelled = true; };
  }, [investigationDetail?.id, investigationDetail?.module]);
  const selectedEvidence = clueWorkspace?.evidence.find((item) => item.id === selectedEvidenceId) || null;
  const openEvidenceEditor = () => {
    if (!selectedEvidence) return message.warning("请先选择一条取证信息");
    if (!selectedEvidence.can_edit) return message.warning("当前账号无权修改该取证信息");
    evidenceEditForm.setFieldsValue({
      notary_institution: selectedEvidence.data.notary_institution || "",
      certificate_no: selectedEvidence.data.notarization_no || selectedEvidence.data.certificate_no || "",
      collected_at: selectedEvidence.data.collected_at ? dayjs(selectedEvidence.data.collected_at) : undefined,
      invoice_no: selectedEvidence.data.invoice_no || "",
      storage_location: selectedEvidence.data.storage_location || "",
      evidence_status: selectedEvidence.data.storage_state || selectedEvidence.data.evidence_status || "未入库",
    });
    setEditingEvidence(selectedEvidence);
  };
  const saveEvidenceEdit = async () => {
    if (!editingEvidence) return;
    try {
      const values = await evidenceEditForm.validateFields();
      await api.put(`/investigations/evidence/${editingEvidence.id}`, {
        ...values,
        collected_at: values.collected_at ? formatRequiredDate(values.collected_at, "取证日期") : null,
      });
      const { data } = await api.get(`/investigations/clues/${investigationDetail?.id}/workspace`);
      setClueWorkspace(data);
      setEditingEvidence(null);
      message.success("取证信息已修改");
    } catch (error: any) {
      if (!error?.errorFields) message.error(error?.response?.data?.detail || "取证信息修改失败");
    }
  };
  const deleteSelectedEvidence = async () => {
    if (!selectedEvidence) return message.warning("请先选择一条取证信息");
    if (!selectedEvidence.can_delete) return message.warning(selectedEvidence.status === "已入卷" ? "已入卷证据不能删除" : "当前账号无权删除该取证信息");
    Modal.confirm({
      title: "删除取证信息",
      content: `确定删除 ${selectedEvidence.serial_no} 及其附件吗？`,
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.delete(`/investigations/evidence/${selectedEvidence.id}`);
          const { data } = await api.get(`/investigations/clues/${investigationDetail?.id}/workspace`);
          setClueWorkspace(data);
          setSelectedEvidenceId(null);
          message.success("取证信息已删除");
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "取证信息删除失败");
        }
      },
    });
  };
  const openTasks = async (row: Row, createSubtask = false) => {
    const authorizationEnd = dayjs(String(row.data.authorized_to || row.data.end_date || ""));
    if (
      createSubtask &&
      authorizationEnd.isValid() &&
      authorizationEnd.isBefore(dayjs(), "day")
    ) {
      Modal.error({
        title: "无法新建子任务",
        content: "该任务已过期，不允许新建子任务",
        okText: "知道了",
      });
      return;
    }
    try {
      const [{ data }, { data: contractData }] = await Promise.all([
        api.get(`/investigations/${row.id}/tasks`),
        api.get("/records", { params: { module: "contract", page_size: 100 } }),
      ]);
      const existingTasks = data.items as TaskRow[];
      const parentTask =
        existingTasks.find((task) => !task.parent_task_id) || existingTasks[0];
      const hasParent = Boolean(parentTask);
      const taskContext =
        createSubtask && parentTask
          ? ({
              ...row,
              title: parentTask.title || row.title,
              serial_no: parentTask.serial_no || row.serial_no,
              data: {
                ...(parentTask.data || {}),
                ...(row.data || {}),
              },
            } as Row)
          : row;
      setTaskTarget(row);
      setTasks(existingTasks);
      // The investigation record is itself the parent task. A first child
      // can therefore be created even when no task projection exists yet.
      setCreatingSubtask(Boolean(createSubtask));
      resetTaskForm(taskContext);
      taskForm.setFieldValue(
        "parent_task_id",
        createSubtask && hasParent ? parentTask.id : undefined,
      );
      setContractOptions(
        contractData.items.filter(
          (contract: Contract) =>
            contract.status !== "草稿" &&
            contract.customer === row.customer,
        ),
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "调查任务加载失败");
    }
  };
  const createTask = async (nextAction: "complete" | "continue") => {
    if (!taskTarget) return;
    try {
      const v = await taskForm.validateFields();
      const regionPath = Array.isArray(v.region_path) ? v.region_path : [];
      await api.post(`/investigations/${taskTarget.id}/tasks`, {
        ...v,
        province: regionPath[0] || v.province || "",
        city: regionPath[1] || v.city || "",
        district: regionPath[2] || v.district || "",
        // Keep the selected investigation area distinct from the inherited
        // authorization scope.  The API still inherits the scope from the
        // parent when this concrete province/city path is supplied.
        authorization_scope: regionPath.length ? "" : v.authorization_scope || "",
        deadline: formatRequiredDate(v.deadline, "截止日期"),
        start_date: v.start_date ? formatRequiredDate(v.start_date, "开始日期") : undefined,
        end_date: v.end_date ? formatRequiredDate(v.end_date, "结束日期") : undefined,
      });
      message.success(nextAction === "continue" ? "子任务已创建，可继续分配" : "子任务已创建");
      const { data } = await api.get(`/investigations/${taskTarget.id}/tasks`);
      setTasks(data.items);
      if (nextAction === "complete") {
        setTaskTarget(null);
        setCreatingSubtask(false);
        return;
      }
      resetTaskForm(taskTarget);
    } catch (error: any) {
      if (error?.errorFields) {
        const name = String(error.errorFields[0]?.name?.[0] || "");
        const labels: Record<string, string> = {
          title: "任务名称",
          owner: "调查员",
          deadline: "截止日期",
          province: "调查省份",
          city: "调查城市",
          district: "调查区/县",
        };
        taskForm.scrollToField(error.errorFields[0].name);
        message.warning(`请填写${labels[name] || "必填信息"}后再创建任务`);
        return;
      }
      message.error(
        error?.response?.data?.detail || error?.message || "任务创建失败",
      );
    }
  };
  const openSubtaskAction = (row: Row, action: SubtaskLifecycleAction) => {
    subtaskActionForm.resetFields();
    setSubtaskActionTarget({ row, action });
  };
  const submitSubtaskAction = async () => {
    if (!subtaskActionTarget) return;
    try {
      const values = await subtaskActionForm.validateFields();
      const { row, action } = subtaskActionTarget;
      await api.post(`/tasks/${row.id}/${action}`, {
        comment: values.comment || "",
      });
      message.success(
        action === "accept"
          ? "调查子任务已接收，进入办理中"
          : "调查子任务已提交完成，等待发起人验收",
      );
      setSubtaskActionTarget(null);
      subtaskActionForm.resetFields();
      await load();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(
        error?.response?.data?.detail || error?.message || "调查子任务流转失败",
      );
    }
  };
  const openEdit = (row: Row) => {
    setEditTarget(row);
    editForm.setFieldsValue({
      title: row.title,
      customer: row.customer,
      owner: row.owner,
      description: row.description || "",
      region: row.data.region || "",
      address: row.data.address || "",
      right_type: row.data.right_type || "",
      sales_channel: row.data.sales_channel || row.data.platform || "",
      product: row.data.product || "",
      source: row.data.source || "",
      infringement_method: row.data.infringement_method || "",
      store_url: row.data.store_url || "",
      shop_name: row.data.shop_name || "",
      shop_id: row.data.shop_id || "",
      has_product: Boolean(row.data.has_product),
      investigated_at: row.data.investigated_at
        ? dayjs(String(row.data.investigated_at))
        : undefined,
      producer: row.data.producer || "",
      indictee: row.data.indictee || "",
      investigation_assistant: row.data.investigation_assistant || "",
      deadline: row.data.deadline ? dayjs(row.data.deadline) : undefined,
      priority: row.data.priority || "普通",
    });
  };
  const saveEdit = async () => {
    if (!editTarget) return;
    const v = await editForm.validateFields();
    try {
      const resubmit =
        editTarget.module === "clue" &&
        !["草稿", "已驳回"].includes(editTarget.status);
      await api.patch(`/investigations/records/${editTarget.id}`, {
        title: v.title,
        customer: v.customer || "",
        description: v.description || "",
        ...(resubmit ? { status: "待审批" } : {}),
        data: {
          region: v.region || "",
          address: v.address || "",
          right_type: v.right_type || "",
          platform: v.sales_channel || "",
          sales_channel: v.sales_channel || "",
          product: v.product || "",
          source: v.source || "",
          infringement_method: v.infringement_method || "",
          store_url: v.store_url || "",
          shop_name: v.shop_name || "",
          shop_id: v.shop_id || "",
          has_product: Boolean(v.has_product),
          investigated_at: v.investigated_at
            ? formatRequiredDate(v.investigated_at, "调查日期")
            : "",
          producer: v.producer || "",
          indictee: v.indictee || "",
          investigation_assistant: v.investigation_assistant || "",
          deadline:
            v.deadline?.format("YYYY-MM-DD") || editTarget.data.deadline,
          priority: v.priority || editTarget.data.priority,
        },
      });
      message.success(
        resubmit ? "线索已修改并重新进入待审核" : "调查资料已修改",
      );
      setEditTarget(null);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "修改失败");
    }
  };
  const openAssign = (row: Row) => {
    setAssignTarget(row);
    assignForm.setFieldsValue({ investigator: row.owner, comment: "" });
  };
  const saveAssign = async () => {
    if (!assignTarget) return;
    const v = await assignForm.validateFields();
    try {
      await api.post(`/investigations/${assignTarget.id}/assign`, v);
      message.success("调查员已更新");
      setAssignTarget(null);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "调查员分配失败");
    }
  };
  const openFee = (
    row: Row,
    feeType: "公证费已付" | "公证费" | "公证服务费" = "公证费",
  ) => {
    setFeeTarget(row);
    feeForm.setFieldsValue({
      fee_type: feeType,
      amount: row.data.fee_amount || undefined,
      description: "",
    });
  };
  const saveFee = async () => {
    if (!feeTarget) return;
    const v = await feeForm.validateFields();
    try {
      const { data } = await api.post(
        `/investigations/clues/${feeTarget.id}/fee-application`,
        v,
      );
      message.success(`费用申请 ${data.fee.serial_no} 已创建`);
      setFeeTarget(null);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "费用申请失败");
    }
  };
  const closeInvestigation = (row: Row) =>
    Modal.confirm({
      title: `关闭调查任务：${row.serial_no}`,
      content:
        "系统会检查全部调查子任务和线索；全部办结后生成可下载的 Word 调查报告。",
      okText: "关闭并生成报告",
      cancelText: "取消",
      async onOk() {
        try {
          const { data } = await api.post(`/investigations/${row.id}/close`, {
            comment: "全部调查事项已经办结",
          });
          message.success(
            `调查任务已关闭，报告 ${data.report.original_name} 已生成`,
          );
          load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "调查任务关闭失败");
          throw error;
        }
      },
    });
  const batchDeleteSelected = (selected: Row[]) => {
    if (!selected.length) {
      message.warning("请先勾选记录");
      return;
    }
    Modal.confirm({
      title: `确认删除 ${selected.length} 条记录？`,
      content:
        "仅草稿、已驳回线索或未开始任务允许删除；有关联业务的记录会被拒绝。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      async onOk() {
        try {
          const { data } = await api.post("/investigations/batch-delete", {
            record_ids: selected.map((x) => x.id),
            comment: "列表批量删除",
          });
          if (data.failed)
            message.warning(
              `删除 ${data.deleted} 条，失败 ${data.failed} 条：${data.errors
                .slice(0, 3)
                .map((x: any) => x.error)
                .join("；")}`,
            );
          else message.success(`已删除 ${data.deleted} 条记录`);
          setSelectedClues([]);
          load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "批量删除失败");
        }
      },
    });
  };
  const columns = useMemo(() => {
    if (initialTab === "notary-query-files")
      return [
        "文件名称",
        "发票号",
        "取证时间",
        "取证机构",
        "线索编号",
        "案件编号",
        "调查员",
        "文书",
        "店铺名称",
        "权利人",
        "处理人",
        "公证书号",
        "导入时间",
      ].map((title, index) => ({
        title,
        key: `notary-${index}`,
        width: index === 0 ? 220 : 120,
        render: (_: unknown, r: Row) => {
          const value = [
            r.title,
            r.data.invoice_no,
            r.data.collected_at,
            r.data.notary_institution,
            r.data.clue_no,
            r.data.case_no,
            projectedPersonDisplayName(r.owner_display_name, r.owner),
            r.data.document_type,
            r.data.shop_name,
            r.customer,
            projectedPersonDisplayName(
              r.data.handler_display_name,
              r.data.handler,
            ),
            r.data.certificate_no,
            r.data.imported_at,
          ][index];
          if (index === 4 && value)
            return (
              <Button
                type="link"
                onClick={() => openLinkedInvestigation(String(value), "clue")}
              >
                {value}
              </Button>
            );
          if (index === 5 && value)
            return (
              <Button
                type="link"
                onClick={() => void openLinkedCase(String(value))}
              >
                {value}
              </Button>
            );
          if (index === 9 && value)
            return (
              <Button
                type="link"
                onClick={() => void openLinkedCustomer(String(value))}
              >
                {value}
              </Button>
            );
          if (index === 11 && value)
            return (
              <Button
                type="link"
                onClick={() => void openLinkedNotary(undefined, String(value))}
              >
                {value}
              </Button>
            );
          return value || "—";
        },
      }));
    if (initialTab.startsWith("investigation-task-sub-"))
      return [
        {
          title: "任务编号",
          dataIndex: "serial_no",
          width: 170,
          render: (value: string, r: Row) => (
            <Button type="link" onClick={() => void openInvestigationDetail(r)}>
              {value}
            </Button>
          ),
        },
        {
          title: "父调查编号",
          width: 170,
          render: (_: unknown, r: Row) => {
            const no = String(r.data.parent_task_no || r.data.investigation_no || "");
            return no ? <Button type="link" onClick={() => void openLinkedInvestigation(no, r.data.parent_task_no ? "task" : "investigation")}>{no}</Button> : "—";
          },
        },
        {
          title: "权利人",
          dataIndex: "customer",
          width: 180,
          render: (value: string) =>
            value ? (
              <Button
                type="link"
                onClick={() => void openLinkedCustomer(value)}
              >
                {value}
              </Button>
            ) : (
              "—"
            ),
        },
        {
          title: "权利类型",
          width: 100,
          render: (_: unknown, r: Row) => r.data.right_type || "—",
        },
          { title: "调查员", width: 100, render: (_: unknown, r: Row) => r.owner_display_name || personDisplayName(r.owner) },
        {
          title: "调查区域",
          width: 160,
          render: (_: unknown, r: Row) =>
            r.data.region || r.data.address || "—",
        },
        {
          title: "开始时间",
          width: 110,
          render: (_: unknown, r: Row) =>
            r.data.started_at || r.data.authorized_from || "—",
        },
        {
          title: "结束时间",
          width: 110,
          render: (_: unknown, r: Row) =>
            r.data.ended_at || r.data.authorized_to || r.data.deadline || "—",
        },
        {
          title: "案源人",
          width: 100,
          render: (_: unknown, r: Row) => r.data.source_owner_display_name || personDisplayName(r.data.source_owner),
        },
        {
          title: "状态",
          dataIndex: "status",
          width: 100,
          render: (value: string) => (
            <Tag color={statusColors[value] || "blue"}>{value}</Tag>
          ),
        },
        {
          title: "办理",
          key: "lifecycle",
          fixed: "right",
          width: 170,
          render: (_: unknown, r: Row) => {
            const canHandle =
              profile.role === "admin" || r.owner === profile.username;
            return (
              <Space size={0}>
                {canHandle && ["待接收", "待处理"].includes(r.status) && (
                  <Button
                    type="link"
                    onClick={() => openSubtaskAction(r, "accept")}
                  >
                    接收任务
                  </Button>
                )}
                {canHandle && r.status === "处理中" && (
                  <Button
                    type="link"
                    onClick={() => openSubtaskAction(r, "complete")}
                  >
                    提交完成
                  </Button>
                )}
                {!canHandle && <span>仅负责人可办理</span>}
              </Space>
            );
          },
        },
      ];
    if (initialTab.startsWith("investigation-task-"))
      return [
        {
          title: "调查编号",
          dataIndex: "serial_no",
          width: 170,
          render: (value: string, r: Row) => (
            <Button type="link" onClick={() => void openInvestigationDetail(r)}>
              {value}
            </Button>
          ),
        },
        {
          title: "权利人",
          dataIndex: "customer",
          width: 180,
          render: (value: string) =>
            value ? (
              <Button
                type="link"
                onClick={() => void openLinkedCustomer(value)}
              >
                {value}
              </Button>
            ) : (
              "—"
            ),
        },
        {
          title: "权利类型",
          width: 100,
          render: (_: unknown, r: Row) => r.data.right_type || "—",
        },
        {
          title: "线索是否客户审核",
          width: 135,
          render: (_: unknown, r: Row) =>
            r.data.customer_review ? "是" : "否",
        },
        {
          title: "授权开始时间",
          width: 115,
          render: (_: unknown, r: Row) => r.data.authorized_from || "—",
        },
        {
          title: "授权结束时间",
          width: 115,
          render: (_: unknown, r: Row) => r.data.authorized_to || "—",
        },
        {
          title: "调查区域",
          width: 160,
          render: (_: unknown, r: Row) => r.data.region || "—",
        },
        {
          title: "案源人",
          width: 100,
          render: (_: unknown, r: Row) => r.data.source_owner_display_name || personDisplayName(r.data.source_owner),
        },
        {
          title: "任务分配人",
          width: 110,
          render: (_: unknown, r: Row) =>
            r.data.assigner_display_name || r.data.assigned_by_display_name || personDisplayName(r.data.assigner || r.data.assigned_by),
        },
      ];
    if (initialTab.startsWith("clue-"))
      return [
        {
          title: "线索编号",
          dataIndex: "serial_no",
          width: 160,
          render: (value: string, r: Row) => (
            <Button type="link" onClick={() => void openInvestigationDetail(r)}>
              {value}
            </Button>
          ),
        },
        {
          title: "案件编号",
          width: 150,
          render: (_: unknown, r: Row) => {
            const caseNo = clueCaseNo(r);
            return caseNo ? (
              <Button
                type="link"
                onClick={() => void openLinkedCase(caseNo)}
              >
                {caseNo}
              </Button>
            ) : (
              "—"
            );
          },
        },
        { title: "调查员", width: 95, render: (_: unknown, r: Row) => r.owner_display_name || personDisplayName(r.owner) },
        {
          title: "调查时间",
          width: 110,
          render: (_: unknown, r: Row) => r.data.investigated_at || "—",
        },
        {
          title: "取证时间",
          width: 110,
          render: (_: unknown, r: Row) => r.data.collected_at || "—",
        },
        {
          title: "侵权方式",
          width: 110,
          render: (_: unknown, r: Row) =>
            r.data.infringement_method || r.data.platform || "—",
        },
        {
          title: "店铺名称",
          width: 180,
          render: (_: unknown, r: Row) => r.data.shop_name || r.title || "—",
        },
        {
          title: "店铺Id",
          width: 120,
          render: (_: unknown, r: Row) => r.data.shop_id || "—",
        },
        {
          title: "调查地址",
          width: 200,
          render: (_: unknown, r: Row) => r.data.address || "—",
        },
        {
          title: "权利人",
          dataIndex: "customer",
          width: 180,
          render: (value: string) =>
            value ? (
              <Button
                type="link"
                onClick={() => void openLinkedCustomer(value)}
              >
                {value}
              </Button>
            ) : (
              "—"
            ),
        },
        {
          title: "权利类型",
          width: 100,
          render: (_: unknown, r: Row) => r.data.right_type || "—",
        },
        {
          title: "案源人",
          width: 95,
          render: (_: unknown, r: Row) => r.data.source_owner_display_name || personDisplayName(r.data.source_owner),
        },
        {
          title: "客户管理人",
          width: 110,
          render: (_: unknown, r: Row) => r.data.customer_manager_display_name || r.data.customer_manager || "—",
        },
        {
          title: "公证书号",
          width: 160,
          render: (_: unknown, r: Row) =>
            r.data.certificate_no || r.data.notary_record_id ? (
              <Button
                type="link"
                onClick={() =>
                  void openLinkedNotary(
                    r.data.notary_record_id,
                    r.data.certificate_no,
                  )
                }
              >
                {r.data.certificate_no || `公证ID：${r.data.notary_record_id}`}
              </Button>
            ) : (
              "—"
            ),
        },
        {
          title: "仓库",
          width: 120,
          render: (_: unknown, r: Row) => r.data.warehouse || "—",
        },
        {
          title: "费用金额",
          width: 105,
          render: (_: unknown, r: Row) => r.data.fee_amount || "—",
        },
      ];
    const base: any[] = [
      {
        title: "业务编号",
        dataIndex: "serial_no",
        width: 170,
        render: (value: string, r: Row) => (
          <Button type="link" onClick={() => void openInvestigationDetail(r)}>
            {value}
          </Button>
        ),
      },
      { title: "标题/事项", dataIndex: "title", width: 240, ellipsis: true },
      {
        title: "客户",
        dataIndex: "customer",
        width: 190,
        ellipsis: true,
        render: (value: string) =>
          value ? (
            <Button type="link" onClick={() => void openLinkedCustomer(value)}>
              {value}
            </Button>
          ) : (
            "—"
          ),
      },
      {
        title: "状态",
        dataIndex: "status",
        width: 100,
        render: (v: string) => <Tag color={statusColors[v] || "blue"}>{v}</Tag>,
      },
      {
        title: "负责人",
        dataIndex: "owner",
        width: 90,
        render: (_: unknown, row: Row) =>
          projectedPersonDisplayName(row.owner_display_name, row.owner),
      },
    ];
    const materialButton = (r: Row) => (
      <Button
        type="link"
        icon={<PaperClipOutlined />}
        onClick={() => openMaterials(r)}
      >
        材料
        {Number(r.data.material_count || 0)
          ? `（${r.data.material_count}）`
          : ""}
      </Button>
    );
    const taskButton = (r: Row) => (
      <Button type="link" icon={<TeamOutlined />} onClick={() => openTasks(r)}>
        任务
      </Button>
    );
    if (tab === "clue")
      base.push(
        {
          title: "调查平台",
          key: "platform",
          width: 100,
          render: (_: unknown, r: Row) => r.data.platform || "-",
        },
        {
          title: "侵权产品",
          key: "product",
          width: 140,
          render: (_: unknown, r: Row) => r.data.product || "-",
        },
        {
          title: "取证信息",
          key: "collection",
          width: 200,
          render: (_: unknown, r: Row) =>
            r.data.collected_at ? (
              <Space orientation="vertical" size={0}>
                <span>{String(r.data.collected_at)}</span>
                <span>{String(r.data.notary_institution || "")}</span>
              </Space>
            ) : (
              "尚未取证"
            ),
        },
        {
          title: "关联公证/案件",
          key: "relation",
          width: 190,
          render: (_: unknown, r: Row) => (
            <Space orientation="vertical" size={0}>
              {r.data.notary_record_id ? (
                <Button
                  className="business-relation-link"
                  type="link"
                  onClick={() =>
                    void openLinkedNotary(
                      r.data.notary_record_id,
                      r.data.certificate_no,
                    )
                  }
                >
                  {r.data.certificate_no ||
                    `公证ID：${r.data.notary_record_id}`}
                </Button>
              ) : (
                <span>未建立公证记录</span>
              )}
              {r.data.converted_case_no && (
                <Button
                  className="business-relation-link"
                  type="link"
                  onClick={() =>
                    void openLinkedCase(String(r.data.converted_case_no))
                  }
                >
                  {String(r.data.converted_case_no)}
                </Button>
              )}
            </Space>
          ),
        },
        {
          title: "操作",
          key: "action",
          fixed: "right",
          width: 420,
          render: (_: unknown, r: Row) => (
            <Space size={0} wrap>
              {["草稿", "已驳回"].includes(r.status) && (
                <Button type="link" onClick={() => submitClue(r)}>
                  提交
                </Button>
              )}
              {investigationActions[String(r.id)]?.review_clue &&
                r.status === "待审批" && (
                  <Button
                    type="link"
                    onClick={() => {
                      setClueReviewing(r);
                      clueReviewForm.setFieldsValue({ approved: true });
                    }}
                  >
                    内部审批
                  </Button>
                )}
              {investigationActions[String(r.id)]?.review_clue &&
                r.status === "待审批" && (
                  <Button type="link" onClick={() => void openTurnOnAudit(r)}>
                    转交审核人
                  </Button>
                )}
              {investigationActions[String(r.id)]?.review_customer_clue &&
                r.status === "待客户审核" && (
                  <Button
                    type="link"
                    onClick={() => {
                      setClueReviewing(r);
                      clueReviewForm.setFieldsValue({ approved: true });
                    }}
                  >
                    客户审核
                  </Button>
                )}
              {r.status === "待取证" && (
                <Button
                  type="link"
                  onClick={() => openSingleCollection(r)}
                >
                  登记取证
                </Button>
              )}
              {["已取证", "已转案件"].includes(r.status) &&
                !r.data.notary_record_id && (
                  <Button type="link" onClick={() => applyNotary(r)}>
                    建立公证
                  </Button>
                )}
              {!["草稿", "待审批", "待客户审核", "已驳回"].includes(
                r.status,
              ) && (
                <Button
                  type="link"
                  onClick={() => {
                    evidenceForm.setFieldsValue({
                      owner: r.owner,
                      source: "调查取证",
                    });
                    setEvidenceSource(r);
                  }}
                >
                  建证据
                </Button>
              )}
              {taskButton(r)}
              {materialButton(r)}
            </Space>
          ),
        },
      );
    if (tab === "notary")
      base.push(
        {
          title: "来源线索",
          key: "clue",
          width: 150,
          render: (_: unknown, r: Row) =>
            r.data.clue_no ? (
              <Button
                type="link"
                onClick={() =>
                  openLinkedInvestigation(String(r.data.clue_no), "clue")
                }
              >
                {r.data.clue_no}
              </Button>
            ) : r.data.missing_clue_guid ? (
              <Tooltip title={`旧系统线索记录已缺失：${r.data.missing_clue_guid}`}>
                <Tag color="orange">旧线索已缺失</Tag>
              </Tooltip>
            ) : (
              "—"
            ),
        },
        {
          title: "审核期限",
          key: "due",
          width: 110,
          render: (_: unknown, r: Row) => r.data.review_due_date || "-",
        },
        {
          title: "公证书编号",
          key: "cert",
          width: 155,
          render: (_: unknown, r: Row) => r.data.certificate_no || "-",
        },
        {
          title: "存放位置",
          key: "storage",
          width: 150,
          render: (_: unknown, r: Row) =>
            r.data.certificate_storage_location || "-",
        },
        {
          title: "关联案件",
          key: "case",
          width: 165,
          render: (_: unknown, r: Row) =>
            r.data.case_no ? (
              <Button
                className="business-relation-link"
                type="link"
                onClick={() => void openLinkedCase(String(r.data.case_no))}
              >
                {String(r.data.case_no)}
              </Button>
            ) : (
              "-"
            ),
        },
        {
          title: "操作",
          key: "action",
          fixed: "right",
          width: 330,
          render: (_: unknown, r: Row) => (
            <Space size={0} wrap>
              {investigationActions[String(r.id)]?.review_notary &&
                r.status === "待审核" && (
                  <Button
                    type="link"
                    onClick={() => {
                      setReviewing(r);
                      reviewForm.setFieldsValue({
                        approved: true,
                        case_type: "民事案件",
                      });
                    }}
                  >
                    审核
                  </Button>
                )}
              {investigationActions[String(r.id)]
                ?.register_notary_certificate &&
                ["等待材料", "待审核", "审核驳回", "审核通过"].includes(
                  r.status,
                ) && (
                  <Button
                    type="link"
                    onClick={() => {
                      certificateForm.resetFields();
                      certificateForm.setFieldsValue({
                        certificate_no: r.data.certificate_no || "",
                        storage_location:
                          r.data.certificate_storage_location || "",
                        warehouse_id: Number(r.data.warehouse_id) || undefined,
                        storage_location_id: Number(r.data.storage_location_id) || undefined,
                        physical_received: Boolean(r.data.physical_received),
                      });
                      setCertificateTarget(r);
                    }}
                  >
                    登记公证书
                  </Button>
                )}
              {taskButton(r)}
              {materialButton(r)}
            </Space>
          ),
        },
      );
    if (tab === "evidence")
      base.push(
        {
          title: "材料来源",
          key: "source",
          width: 140,
          render: (_: unknown, r: Row) => r.data.source || "-",
        },
        {
          title: "关联线索",
          key: "clue",
          width: 150,
          render: (_: unknown, r: Row) =>
            r.data.clue_no ? (
              <Button
                type="link"
                onClick={() =>
                  openLinkedInvestigation(String(r.data.clue_no), "clue")
                }
              >
                {r.data.clue_no}
              </Button>
            ) : r.data.missing_clue_guid ? (
              <Tooltip title={`旧系统线索记录已缺失：${r.data.missing_clue_guid}`}>
                <Tag color="orange">旧线索已缺失</Tag>
              </Tooltip>
            ) : (
              "—"
            ),
        },
        {
          title: "操作",
          key: "action",
          fixed: "right",
          width: 300,
          render: (_: unknown, r: Row) => (
            <Space size={0}>
              {r.status === "待整理" && (
                <Button
                  type="link"
                  onClick={() => evidenceAction(r, "organize")}
                >
                  完成整理
                </Button>
              )}
              {r.status === "已整理" && (
                <Button type="link" onClick={() => evidenceAction(r, "file")}>
                  证据入卷
                </Button>
              )}
              {taskButton(r)}
              {materialButton(r)}
            </Space>
          ),
        },
      );
    return base;
  }, [tab, initialTab, investigationActions, profile]);
  const meta = moduleMeta[tab];
  const canReviewClue = visibleRows.some((row) =>
    Boolean(investigationActions[String(row.id)]?.review_clue),
  );
  const canReviewCustomerClue = visibleRows.some((row) =>
    Boolean(investigationActions[String(row.id)]?.review_customer_clue),
  );
  const isParentTask =
      initialTab.startsWith("investigation-task-") &&
      !initialTab.startsWith("investigation-task-sub-"),
    isSubTask = initialTab.startsWith("investigation-task-sub-"),
    isClue = initialTab.startsWith("clue-"),
    isAuditClue = initialTab.startsWith("clue-audit-"),
    isImport = [
      "notary-import-info",
      "notary-import-storage",
      "notary-import-files",
      "notary-import-invoices",
    ].includes(initialTab),
    isFileQuery = initialTab === "notary-query-files";
  const routeTitles: Record<string, string> = {
    "notary-import-info": "公证信息导入",
    "notary-import-storage": "补充取证信息(公证书号,仓库位置,发票号)文件导入",
    "notary-import-files": "公证书文件导入",
    "notary-import-invoices": "发票文件导入",
    "notary-query-files": "公证书文件列表",
  };
  const pageTitle =
    routeTitles[initialTab] ||
    (isSubTask || isParentTask
      ? "调查任务列表"
      : isClue
        ? "调查线索列表"
        : meta.title);
  const originalButtons: Record<string, string[]> = {
    "investigation-task-published": [
      "查询",
      "刷新",
      "修改",
      "上传调查资料",
      "关闭任务并生成报告",
      "删除",
    ],
    "investigation-task-mine": [
      "查询",
      "刷新",
      "修改",
      "上传调查资料",
    ],
    "investigation-task-overdue": [
      "查询",
      "刷新",
      "修改",
      "上传调查资料",
    ],
    "investigation-task-unassigned": ["查询", "刷新", "新增子任务", "删除"],
    "investigation-task-sub-published": ["查询", "刷新", "修改", "批量删除"],
    "investigation-task-sub-mine": ["查询", "刷新", "新增线索"],
    "clue-my-draft": ["查询", "修改", "提交", "批量提交", "新增文件", "批量删除"],
    "clue-my-pending": ["查询", "修改"],
    "clue-my-customer": ["查询", "修改"],
    "clue-my-collect": ["查询", "修改", "新增调查员", "取证"],
    "clue-my-collected": [
      "查询",
      "修改",
      "建立公证",
      "建立证据目录",
      "申请费用",
      "新增调查员",
      "取证",
      "生成案件",
    ],
    "clue-my-refused": ["查询", "修改", "提交", "批量提交", "新增文件", "批量删除"],
    "clue-my-no-fee": ["查询", "修改", "申请费用"],
    "clue-my-fee": ["查询", "修改"],
    "clue-audit-pending": ["查询", "刷新", "修改", "审批", "转交审核人"],
    "clue-audit-customer": ["查询", "刷新", "修改", "审批"],
  };
  const selectedRows = visibleRows.filter((row) =>
    selectedClues.includes(row.id),
  );
  const selectedRow = selectedRows.length === 1 ? selectedRows[0] : null;
  const isAdminAccount = [profile.role, ...(profile.role_ids || [])].includes("admin");
  const actionLabels = [
    ...(originalButtons[initialTab] || ["查询"]),
    ...(isClue ? ["导出线索", "导出交接清单"] : []),
  ].filter(
    (label) =>
      (label !== "删除" || initialTab !== "investigation-task-unassigned" || isAdminAccount) &&
      (label !== "审批" ||
        (initialTab === "clue-audit-customer"
          ? canReviewCustomerClue
          : canReviewClue)),
  );
  const queryActionLabels = actionLabels.filter((label) => ["查询", "刷新"].includes(label));
  const businessActionLabels = actionLabels.filter((label) => !["查询", "刷新"].includes(label));
  const requireSingleRow = (label: string, handler: (row: Row) => void) => {
    if (!selectedRow) {
      message.warning(
        label === "新增线索" ? "请只勾选一条子任务" : "请只勾选一条记录",
      );
      return;
    }
    handler(selectedRow);
  };
  const originalActionHandlers: Record<string, () => void> = {
    查询: () => setListQuery((x) => ({ ...x })),
    刷新: () => void load(),
    导出线索: () => void exportRows("clues"),
    导出交接清单: () => void exportRows("handover"),
    新建调查任务: () => {
      setCreateContextTask(null);
      setCreateModule("investigation");
      createForm.setFieldsValue({
        serial_no: serial("DC"),
        status: "待分配",
        owner: profile.username || "admin",
        customer: "",
        right_type: "商标",
        customer_review: true,
      });
      setInvestigationCreateOpen(true);
    },
    新增线索: () =>
      requireSingleRow("新增线索", (row) => {
        setCreateContextTask(row);
        setCreateModule("clue");
        createForm.setFieldsValue({
          serial_no: "自动生成",
          status: "草稿",
          owner: row.owner,
          customer: row.customer,
          right_type: row.data.right_type || "商标",
          source_owner: systemPersonValue(row.data.source_owner),
          region: row.data.region || "",
          address: row.data.address || "",
          platform: "",
          product: "",
          infringement_method: "",
          sales_channel: "",
          source: "",
          store_url: "",
          shop_name: "",
          shop_id: "",
          has_product: false,
          product_url: "",
          sale_num: "",
          producer: "",
          indictee: "",
          investigation_assistant: "",
          investigated_at: undefined,
        });
        setClueCreateOpen(true);
      }),
    批量删除: () => batchDeleteSelected(selectedRows),
    删除: () => batchDeleteSelected(selectedRows),
    生成案件: () => void openBatchCases(),
    修改: () => requireSingleRow("修改", openEdit),
    提交: () => requireSingleRow("提交", (row) => void submitClue(row)),
    批量提交: () => openBatchSubmit(),
    转交审核人: () =>
      requireSingleRow("转交审核人", (row) => {
        if (row.status !== "待审批") {
          message.warning("仅待审批线索可转交审核人");
          return;
        }
        if (!investigationActions[String(row.id)]?.review_clue) {
          message.error("当前账号没有该线索的内部审核权限");
          return;
        }
        void openTurnOnAudit(row);
      }),
    审批: () =>
      requireSingleRow("审批", (row) => {
        const actions = investigationActions[String(row.id)];
        const allowed =
          row.status === "待客户审核"
            ? actions?.review_customer_clue
            : actions?.review_clue;
        if (!allowed) {
          message.error("当前账号没有此线索的审核权限");
          return;
        }
        setClueReviewing(row);
        clueReviewForm.setFieldsValue({ approved: true });
      }),
    取证: () =>
      requireSingleRow("取证", openSingleCollection),
    建立公证: () =>
      requireSingleRow("建立公证", (row) => void applyNotary(row)),
    建立证据目录: () =>
      requireSingleRow("建立证据目录", (row) => {
        evidenceForm.setFieldsValue({
          title: `${row.serial_no} 取证材料`,
          owner: row.owner,
          source: "调查取证",
          description: "",
        });
        setEvidenceSource(row);
      }),
    新增文件: () =>
      requireSingleRow("新增文件", (row) => void openMaterials(row)),
    上传调查资料: () =>
      requireSingleRow("上传调查资料", (row) => void openMaterials(row)),
    新增子任务: () =>
      requireSingleRow("新增子任务", (row) => void openTasks(row, true)),
    新增调查员: () => requireSingleRow("新增调查员", openAssign),
    申请费用: () => requireSingleRow("申请费用", (row) => openFee(row)),
    关闭任务并生成报告: () =>
      requireSingleRow(
        "关闭任务并生成报告",
        (row) => void closeInvestigation(row),
      ),
  };
  const runOriginalAction = (label: string) => {
    const handler = originalActionHandlers[label];
    if (!handler) {
      message.error(`调查中心动作未配置真实办理入口：${label}`);
      return;
    }
    handler();
  };
  const filters = isParentTask ? (
    <>
      <Form.Item label="调查编号" name="serial_no">
        <Input />
      </Form.Item>
      <Form.Item label="授权日期" name="authorized_range">
        <DatePicker.RangePicker />
      </Form.Item>
      <Form.Item label="权利人" name="rights_holder">
        <Input />
      </Form.Item>
      <Form.Item label="调查区域" name="region">
        <Input />
      </Form.Item>
    </>
  ) : isSubTask ? (
    <>
      <Form.Item label="任务编号" name="serial_no">
        <Input />
      </Form.Item>
      <Form.Item label="调查日期" name="investigation_range">
        <DatePicker.RangePicker />
      </Form.Item>
      <Form.Item label="调查员" name="investigator">
        <Input />
      </Form.Item>
      <Form.Item label="调查区域" name="region">
        <Input />
      </Form.Item>
      <Form.Item label="权利人" name="rights_holder">
        <Input />
      </Form.Item>
      <Form.Item label="权利类型" name="right_type">
        <Select
          allowClear
          options={["全部", "商标", "专利", "著作权", "不正当竞争"].map(
            (value) => ({ value, label: value }),
          )}
        />
      </Form.Item>
    </>
  ) : isAuditClue ? (
    <>
      <Form.Item label="线索编号" name="serial_no">
        <Input />
      </Form.Item>
      <Form.Item label="侵权方式" name="infringement_method">
        <Select
          allowClear
          options={["电商平台", "实体店铺", "工厂", "其他", "网页链接"].map(
            (value) => ({ value, label: value }),
          )}
        />
      </Form.Item>
      <Form.Item label="权利人" name="rights_holder">
        <Input />
      </Form.Item>
      <Form.Item label="案件状态" name="case_status">
        <Select
          allowClear
          options={["全部", "未生成案件", "已生成案件"].map((value) => ({
            value,
            label: value,
          }))}
        />
      </Form.Item>
      <Form.Item label="店铺名称" name="shop_name">
        <Input />
      </Form.Item>
      <Form.Item label="店铺地址" name="shop_address">
        <Input />
      </Form.Item>
      <Form.Item label="调查员" name="investigator">
        <Input />
      </Form.Item>
      <Form.Item label="调查区域" name="region">
        <Input />
      </Form.Item>
      <Form.Item label="调查日期" name="investigation_range">
        <DatePicker.RangePicker />
      </Form.Item>
      <Form.Item label="取证日期" name="collection_range">
        <DatePicker.RangePicker />
      </Form.Item>
      <Form.Item label="公证书号" name="certificate_no">
        <Input />
      </Form.Item>
      <Form.Item label="仓库位置" name="warehouse">
        <Input />
      </Form.Item>
    </>
  ) : (
    <>
      <Form.Item label="线索编号" name="serial_no">
        <Input />
      </Form.Item>
      <Form.Item label="证物状态" name="evidence_status">
        <Select
          allowClear
          placeholder="请选择"
          options={["未入库", "已入库", "已出库", "已重新入库", "已销毁"].map(
            (value) => ({ value, label: value }),
          )}
        />
      </Form.Item>
      <Form.Item label="调查员" name="investigator">
        <Input />
      </Form.Item>
      <Form.Item label="权利人" name="rights_holder">
        <Input />
      </Form.Item>
      <Form.Item label="案件状态" name="case_status">
        <Select
          allowClear
          options={["全部", "未生成案件", "已生成案件"].map((value) => ({
            value,
            label: value,
          }))}
        />
      </Form.Item>
      <Form.Item label="店铺名称" name="shop_name">
        <Input />
      </Form.Item>
      <Form.Item label="调查区域" name="region">
        <Input />
      </Form.Item>
      <Form.Item label="调查日期" name="investigation_range">
        <DatePicker.RangePicker />
      </Form.Item>
      <Form.Item label="仓库位置" name="warehouse">
        <Input />
      </Form.Item>
      <Form.Item label="公证书号" name="certificate_no">
        <Input />
      </Form.Item>
      <Form.Item label="公证机构" name="notary_institution">
        <Input />
      </Form.Item>
      <Form.Item label="取证日期" name="collection_range">
        <DatePicker.RangePicker />
      </Form.Item>
    </>
  );
  const fileQueryFilters = (
    <>
      <Form.Item label="线索编号" name="serial_no">
        <Input />
      </Form.Item>
      <Form.Item label="调查员" name="investigator">
        <Input />
      </Form.Item>
      <Form.Item label="文书" name="document_type">
        <Input />
      </Form.Item>
      <Form.Item label="权利人" name="rights_holder">
        <Input />
      </Form.Item>
      <Form.Item label="案件编号" name="case_no">
        <Input />
      </Form.Item>
      <Form.Item label="店铺名称" name="shop_name">
        <Input />
      </Form.Item>
      <Form.Item label="处理人" name="handler">
        <Input />
      </Form.Item>
      <Form.Item label="导入日期" name="import_range">
        <DatePicker.RangePicker />
      </Form.Item>
      <Form.Item label="发票号" name="invoice_no">
        <Input />
      </Form.Item>
      <Form.Item label="公证书号" name="certificate_no">
        <Input />
      </Form.Item>
      <Form.Item label="公证机构" name="notary_institution">
        <Input />
      </Form.Item>
      <Form.Item label="取证日期" name="collection_range">
        <DatePicker.RangePicker />
      </Form.Item>
    </>
  );
  const importColumns =
    initialTab === "notary-import-info"
      ? [
          "来源线索编号",
          "公证标题",
          "负责人",
          "审核截止日",
          "公证书编号",
          "签发日期",
          "存放位置",
          "实物已收",
          "说明",
        ]
      : initialTab === "notary-import-storage"
        ? [
            "线索号",
            "调查员",
            "调查时间",
            "侵权方式",
            "店铺名称",
            "调查地址",
            "公证书号",
            "仓库",
            "发票号",
            "案号",
          ]
        : initialTab === "notary-import-files"
          ? [
              "文件名",
              "案号",
              "公证书号",
              "发票号",
              "取证时间",
              "取证机构",
              "落款时间",
              "线索编号",
              "调查员",
              "店铺名称",
              "权利人",
            ]
          : [
              "文件名",
              "公证书号",
              "发票号",
              "取证时间",
              "取证机构",
              "落款时间",
              "线索编号",
              "调查员",
              "店铺名称",
              "权利人",
            ];
  const importRule =
    initialTab === "notary-import-info"
      ? "仅支持 UTF-8 CSV；来源线索必须已完成取证，且尚未生成公证记录。"
      : initialTab === "notary-import-files"
        ? "请选择 PDF，并填写要关联的公证书号；文件名不参与编号匹配。"
        : initialTab === "notary-import-invoices"
          ? "请选择 PDF，并填写要关联的发票号；文件名不参与编号匹配。"
          : "";
  const importAccept = ["notary-import-info", "notary-import-storage"].includes(
    initialTab,
  )
    ? ".csv,text/csv"
    : ".pdf,application/pdf";
  // Every route declares its data-column widths. Calculate the horizontal viewport
  // from those widths and include the selection column, instead of leaving a large
  // blank scroll area on narrow branches or hiding a fixed right action column.
  const tableScrollX =
    columns.reduce(
      (total: number, column: any) =>
        total + (typeof column.width === "number" ? column.width : 160),
      0,
    ) + (isFileQuery ? 0 : 40);
  const investigationDetailItems = investigationDetail
    ? [
        {
          key: "no",
          label: "调查编号",
          children: investigationDetail.serial_no,
        },
        {
          key: "status",
          label: "状态",
          children: (
            <Tag color={statusColors[investigationDetail.status] || "blue"}>
              {investigationDetail.status}
            </Tag>
          ),
        },
        {
          key: "title",
          label: "调查事项",
          children: investigationDetail.title,
          span: 2,
        },
        {
          key: "customer",
          label: "权利人",
          children: investigationDetail.customer ? (
            <Button
              className="business-relation-link"
              type="link"
              onClick={() =>
                void openLinkedCustomer(investigationDetail.customer)
              }
            >
              {investigationDetail.customer}
            </Button>
          ) : (
            "—"
          ),
        },
        {
          key: "right-type",
          label: "权利类型",
          children: investigationDetail.data.right_type || "—",
        },
        {
          key: "owner",
          label: "调查员",
          children: projectedPersonDisplayName(
            investigationDetail.owner_display_name,
            investigationDetail.owner,
          ),
        },
        {
          key: "region",
          label: "调查区域",
          children: investigationDetail.data.region || [investigationDetail.data.province, investigationDetail.data.city, investigationDetail.data.district].filter(Boolean).join(" ") || "—",
        },
        {
          key: "started-at",
          label: "开始时间",
          children: investigationDetail.data.started_at || investigationDetail.data.start_date || investigationDetail.data.authorized_from || "—",
        },
        {
          key: "ended-at",
          label: "结束时间",
          children: investigationDetail.data.ended_at || investigationDetail.data.end_date || investigationDetail.data.deadline || investigationDetail.data.authorized_to || "—",
        },
        {
          key: "source-owner",
          label: "案源人",
          children: projectedPersonDisplayName(
            investigationDetail.data.source_owner_display_name,
            investigationDetail.data.source_owner,
          ),
        },
        {
          key: "assigner",
          label: "任务分配人",
          children:
            projectedPersonDisplayName(
              investigationDetail.data.assigner_display_name ||
                investigationDetail.data.assigned_by_display_name,
              investigationDetail.data.assigner ||
                investigationDetail.data.assigned_by,
            ),
        },
        ...((investigationDetail.data.parent_task_no || investigationDetail.data.investigation_no)
          ? [{
              key: "parent-investigation",
              label: "父调查编号",
              children: <Button className="business-relation-link" type="link" onClick={() => void openLinkedInvestigation(String(investigationDetail.data.parent_task_no || investigationDetail.data.investigation_no), investigationDetail.data.parent_task_no ? "task" : "investigation")}>
                {String(investigationDetail.data.parent_task_no || investigationDetail.data.investigation_no)}
              </Button>,
            }]
          : []),
        ...(investigationDetail.data.source_task_no
          ? [
              {
                key: "source-task",
                label: "来源调查任务",
                children: (
                  <Button
                    className="business-relation-link"
                    type="link"
                    onClick={() =>
                      openLinkedInvestigation(
                        String(investigationDetail.data.source_task_no),
                        "task",
                      )
                    }
                  >
                    {String(investigationDetail.data.source_task_no)}
                  </Button>
                ),
              },
            ]
          : []),
        ...(investigationDetail.data.clue_no
          ? [
              {
                key: "clue",
                label: "关联线索",
                children: (
                  <Button
                    className="business-relation-link"
                    type="link"
                    onClick={() =>
                      openLinkedInvestigation(
                        String(investigationDetail.data.clue_no),
                        "clue",
                      )
                    }
                  >
                    {String(investigationDetail.data.clue_no)}
                  </Button>
                ),
              },
            ]
          : []),
        ...(investigationDetail.data.case_no ||
        investigationDetail.data.converted_case_no
          ? [
              {
                key: "case",
                label: "关联案件",
                children: (
                  <Button
                    className="business-relation-link"
                    type="link"
                    onClick={() =>
                      void openLinkedCase(
                        String(
                          investigationDetail.data.case_no ||
                            investigationDetail.data.converted_case_no,
                        ),
                      )
                    }
                  >
                    {String(
                      investigationDetail.data.case_no ||
                        investigationDetail.data.converted_case_no,
                    )}
                  </Button>
                ),
              },
            ]
          : []),
        ...(investigationDetail.data.certificate_no ||
        investigationDetail.data.notary_record_id
          ? [
              {
                key: "notary",
                label: "关联公证",
                children: (
                  <Button
                    className="business-relation-link"
                    type="link"
                    onClick={() =>
                      void openLinkedNotary(
                        investigationDetail.data.notary_record_id,
                        investigationDetail.data.certificate_no,
                      )
                    }
                  >
                    {String(
                      investigationDetail.data.certificate_no ||
                        `公证ID：${investigationDetail.data.notary_record_id}`,
                    )}
                  </Button>
                ),
              },
            ]
          : []),
        ...(investigationDetail.module === "clue"
          ? [
              {
                key: "infringement",
                label: "侵权方式",
                children:
                  investigationDetail.data.infringement_method ||
                  "—",
              },
              {
                key: "sales-channel",
                label: "销售渠道",
                children:
                  investigationDetail.data.sales_channel ||
                  investigationDetail.data.platform ||
                  "—",
              },
              {
                key: "investigated-at",
                label: "调查日期",
                children: investigationDetail.data.investigated_at || "—",
              },
              {
                key: "store-url",
                label: "店铺链接",
                children: investigationDetail.data.store_url ? (
                  <a
                    href={String(investigationDetail.data.store_url)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {String(investigationDetail.data.store_url)}
                  </a>
                ) : (
                  "—"
                ),
              },
              {
                key: "shop-name",
                label: "店铺名称",
                children: investigationDetail.data.shop_name || investigationDetail.title || "—",
              },
              {
                key: "shop-id",
                label: "店铺Id",
                children: investigationDetail.data.shop_id || "—",
              },
              {
                key: "has-product",
                label: "有无产品",
                children: investigationDetail.data.has_product ? "有" : "无",
              },
              {
                key: "address",
                label: "调查地址",
                children: investigationDetail.data.address || "—",
              },
              {
                key: "platform",
                label: "调查平台",
                children: investigationDetail.data.platform || "—",
              },
              {
                key: "product",
                label: "侵权产品",
                children: investigationDetail.data.product || "—",
              },
              {
                key: "source",
                label: "来源",
                children: investigationDetail.data.source || "—",
              },
              {
                key: "producer",
                label: "生产商",
                children:
                  investigationDetail.data.producer ||
                  investigationDetail.data.producers ||
                  "—",
              },
              {
                key: "indictee",
                label: "主体信息",
                children:
                  investigationDetail.data.indictee ||
                  investigationDetail.data.indictees ||
                  investigationDetail.data.subject ||
                  "—",
              },
              {
                key: "assistant",
                label: "调查辅助",
                children:
                  projectedPersonDisplayName(
                    investigationDetail.data.investigation_assistant_display_name,
                    investigationDetail.data.investigation_assistant ||
                      investigationDetail.data.assistant,
                  ),
              },
              {
                key: "collected-at",
                label: "取证日期",
                children: investigationDetail.data.collected_at || "—",
              },
              {
                key: "notary-institution",
                label: "取证机构",
                children: investigationDetail.data.notary_institution || "—",
              },
              {
                key: "certificate-no",
                label: "公证书号",
                children: investigationDetail.data.certificate_no || "—",
              },
              {
                key: "invoice-no",
                label: "发票号",
                children: investigationDetail.data.invoice_no || "—",
              },
              {
                key: "warehouse",
                label: "证物存放处",
                children:
                  investigationDetail.data.warehouse ||
                  investigationDetail.data.certificate_storage_location ||
                  "—",
              },
              {
                key: "evidence-status",
                label: "证物状态",
                children:
                  investigationDetail.data.evidence_status ||
                  investigationDetail.data.warehouse_status ||
                  investigationDetail.data.storage_status ||
                  "—",
              },
              {
                key: "investigator-remark",
                label: "调查员备注",
                children: investigationDetail.data.investigator_remark || "—",
              },
              {
                key: "review-remark",
                label: "审批备注",
                children: investigationDetail.data.review_comment || "—",
              },
              {
                key: "customer-review-remark",
                label: "客户审核备注",
                children:
                  investigationDetail.data.customer_review_comment || "—",
              },
            ]
          : []),
        {
          key: "description",
          label: "说明",
          children: investigationDetail.description || "—",
          span: 2,
        },
      ]
    : [];
  const taskScopeGroups = taskTarget
    ? investigationTaskScopeGroups(taskTarget.data || {})
    : [];
  const taskSelectedProvince = String(taskProvince || "");
  const taskCityOptions =
    taskScopeGroups.find((group) => group.province === taskSelectedProvince)
      ?.cities || [];
  const taskDistrictOptions = investigationDistrictsForCity(
    taskSelectedProvince,
    String(taskCity || ""),
  );
  const taskAuthorizationScope = String(
    taskTarget?.data.authorization_scope || "未配置",
  ).trim();
  const taskRegionOptions = investigationTaskRegionOptions(taskScopeGroups);
  return (
    <>
      <Modal
        open={Boolean(subtaskActionTarget)}
        title={`${subtaskActionTarget?.action === "accept" ? "接收调查子任务" : "提交调查子任务完成"}：${subtaskActionTarget?.row.serial_no || ""}`}
        okText={
          subtaskActionTarget?.action === "accept" ? "确认接收" : "提交完成"
        }
        cancelText="取消"
        onOk={submitSubtaskAction}
        onCancel={() => {
          setSubtaskActionTarget(null);
          subtaskActionForm.resetFields();
        }}
      >
        <Form form={subtaskActionForm} layout="vertical">
          <Form.Item
            label={
              subtaskActionTarget?.action === "accept"
                ? "接收说明"
                : "办理结果说明"
            }
            name="comment"
            rules={
              subtaskActionTarget?.action === "complete"
                ? [{ required: true, min: 2, message: "请填写办理结果说明" }]
                : []
            }
          >
            <Input.TextArea
              rows={4}
              placeholder={
                subtaskActionTarget?.action === "accept"
                  ? "可填写接收说明"
                  : "请说明本次调查办理结果"
              }
            />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={investigationCreateOpen}
        title="新建调查任务"
        okText="保存调查任务"
        cancelText="取消"
        onOk={() => void create()}
        onCancel={() => {
          setInvestigationCreateOpen(false);
          setCreateContextTask(null);
          setCreateModule(tab);
          createForm.resetFields();
        }}
      >
        <Form form={createForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              label="调查编号"
              name="serial_no"
              rules={[{ required: true, message: "请填写调查编号" }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="负责人/调查员"
              name="owner"
              rules={[{ required: true, message: "请填写负责人" }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                options={systemPersonOptions}
              />
            </Form.Item>
            <Form.Item
              className="span-2"
              label="标题/事项"
              name="title"
              rules={[
                { required: true, min: 2, message: "调查事项至少 2 个字符" },
              ]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="权利人/客户" name="customer">
              <Input />
            </Form.Item>
            <Form.Item label="案源人" name="source_owner">
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                options={systemPersonOptions}
              />
            </Form.Item>
            <Form.Item
              label="调查区域"
              name="region"
              rules={[{ required: true, message: "请填写调查区域" }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="权利类型"
              name="right_type"
              rules={[{ required: true, message: "请选择权利类型" }]}
            >
              <Select
                options={["商标", "专利", "著作权", "不正当竞争"].map(
                  (value) => ({ value, label: value }),
                )}
              />
            </Form.Item>
            <Form.Item
              label="授权开始日期"
              name="authorized_from"
              rules={[{ required: true, message: "请选择授权开始日期" }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="授权结束日期"
              name="authorized_to"
              dependencies={["authorized_from"]}
              rules={[
                { required: true, message: "请选择授权结束日期" },
                {
                  validator: (_, value) => {
                    const start = createForm.getFieldValue("authorized_from");
                    return !start ||
                      !value ||
                      !dayjs(value).isBefore(dayjs(start), "day")
                      ? Promise.resolve()
                      : Promise.reject(
                          new Error("授权结束日期不能早于开始日期"),
                        );
                  },
                },
              ]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="customer_review" valuePropName="checked">
              <Checkbox>线索需要客户审核</Checkbox>
            </Form.Item>
            <Form.Item className="span-2" label="说明" name="description">
              <Input.TextArea rows={3} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
      <Drawer
        open={clueCreateOpen}
        title="线索报备"
        placement="right"
        width={620}
        footer={
          <Space>
            <Button onClick={() => void create(false)}>暂存线索</Button>
            <Button type="primary" onClick={() => void create(true)}>
              提交审批
            </Button>
          </Space>
        }
        onClose={() => {
          setClueCreateOpen(false);
          setCreateContextTask(null);
          setCreateModule(tab);
          setClueFiles([]);
          createForm.resetFields();
        }}
      >
        <Form form={createForm} layout="vertical">
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message="提交审批前请确认主体信息完整"
          />
          <div className="form-grid">
            <Form.Item
              label="线索编号"
              name="serial_no"
            >
              <Input disabled />
            </Form.Item>
            <Form.Item label="调查员" name="owner" rules={[{ required: true }]}>
              <Select
                disabled
                showSearch
                optionFilterProp="label"
                options={systemPersonOptions}
              />
            </Form.Item>
            <Form.Item
              className="span-2"
              label="标题/事项"
              name="title"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="客户" name="customer">
              <Input disabled />
            </Form.Item>
            <Form.Item label="侵权方式" name="infringement_method">
              <Select
                allowClear
                options={CLUE_INFRINGEMENT_METHOD_OPTIONS.map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item
              label="销售渠道"
              name="sales_channel"
              rules={[{ required: true, message: "请选择销售渠道" }]}
            >
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                options={CLUE_SALES_CHANNEL_OPTIONS.map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item
              label="侵权产品"
              name="product"
              rules={[{ required: true, message: "不同产品需分别创建线索" }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="店铺链接" name="store_url">
              <Input placeholder="请输入店铺链接" />
            </Form.Item>
            <Form.Item label="店铺名称" name="shop_name">
              <Input placeholder="请输入店铺名称" />
            </Form.Item>
            <Form.Item label="店铺Id" name="shop_id">
              <Input placeholder="淘宝店铺Id为掌柜名称，拼多多店铺Id为一串数字" />
            </Form.Item>
            <Form.Item label="有无产品" name="has_product">
              <Radio.Group
                options={[
                  { value: true, label: "有" },
                  { value: false, label: "无" },
                ]}
              />
            </Form.Item>
            <Form.Item label="产品链接" name="product_url">
              <Input placeholder="请输入产品链接" />
            </Form.Item>
            <Form.Item label="规模" name="sale_num">
              <Input placeholder="请输入规模" />
            </Form.Item>
            <Form.Item label="调查地址" name="address">
              <Input placeholder="请输入调查地址" />
            </Form.Item>
            <Form.Item label="调查日期" name="investigated_at">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="生产商" name="producer">
              <Input placeholder="生产商" />
            </Form.Item>
            <Form.Item label="主体信息" name="indictee">
              <Input placeholder="主体信息" />
            </Form.Item>
            <Form.Item label="调查辅助员" name="investigation_assistant">
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder="请选择系统人员"
                options={systemPersonOptions}
              />
            </Form.Item>
            <Form.Item label="权利类型" name="right_type">
              <Select
                options={["商标", "专利", "著作权", "不正当竞争"].map(
                  (value) => ({ value, label: value }),
                )}
              />
            </Form.Item>
            <Form.Item label="案源人" name="source_owner">
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                options={systemPersonOptions}
              />
            </Form.Item>
            <Form.Item label="调查区域" name="region">
              <Input />
            </Form.Item>
            <Form.Item label="来源" name="source">
              <Input />
            </Form.Item>
            <Form.Item label="附件">
              <input
                multiple
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.zip,.rar"
                onChange={(event) =>
                  setClueFiles(Array.from(event.target.files || []))
                }
              />
              <Typography.Text type="secondary">
                {clueFiles.length
                  ? `已选择 ${clueFiles.length} 个文件`
                  : "可上传调查线索相关材料"}
              </Typography.Text>
            </Form.Item>
            <Form.Item className="span-2" label="备注" name="description">
              <Input.TextArea rows={3} />
            </Form.Item>
          </div>
        </Form>
      </Drawer>
      {(initialTab === "notary-import-files" ||
        initialTab === "notary-import-invoices") && (
        <Card size="small" style={{ marginBottom: 12 }}>
          <Space>
            <span>
              {initialTab === "notary-import-files" ? "公证书号" : "发票号"}
            </span>
            <Input
              style={{ width: 260 }}
              placeholder={
                initialTab === "notary-import-files"
                  ? "请输入公证书号"
                  : "请输入发票号"
              }
              value={importReference}
              onChange={(e) => setImportReference(e.target.value)}
            />
          </Space>
        </Card>
      )}
      <Card className="panel investigation-original" title={pageTitle}>
        {isImport ? (
          <div className="notary-import-page">
            <div className="notary-file-rule">{importRule}</div>
            <label>请选择上传文件：</label>
            <Space wrap>
              {initialTab === "notary-import-info" && (
                <Button
                  icon={<DownloadOutlined />}
                  onClick={downloadImportTemplate}
                >
                  下载导入模板
                </Button>
              )}
              <label className="notary-upload-button">
                <UploadOutlined /> 选择文件
                <input
                  hidden
                  type="file"
                  accept={importAccept}
                  onChange={(e) => {
                    setImportFile(e.target.files?.[0] || null);
                    setImportResult(null);
                    setImportPreviewRows([]);
                  }}
                />
              </label>
              {importFile && (
                <span className="notary-selected-file">{importFile.name}</span>
              )}
              <Button type="primary" onClick={importRows}>
                上传文件
              </Button>
            </Space>
            {importResult && (
              <Alert
                style={{ marginTop: 12 }}
                type={importResult.failed ? "warning" : "success"}
                showIcon
                title={`成功 ${initialTab === "notary-import-storage" ? ((importResult as any).updated ?? importResult.created) : importResult.created} 条，失败 ${importResult.failed} 条`}
                description={importResult.errors?.slice(0, 8).map((x) => (
                  <div key={`${x.row}-${x.error}`}>
                    第 {x.row} 行：{x.error}
                  </div>
                ))}
              />
            )}
            <Table
              size="small"
              rowKey={(row: any) => String(row.id ?? JSON.stringify(row))}
              dataSource={importPreviewRows}
              locale={{ emptyText: "暂无待导入数据" }}
              columns={importColumns.map((title) => ({
                title,
                dataIndex: title,
              }))}
              scroll={{ x: 1200 }}
              pagination={false}
            />
          </div>
        ) : (
          <>
            <Form
              key={initialTab}
              className="investigation-query"
              onValuesChange={(_, all) => setListQuery(all)}
            >
              {isFileQuery ? fileQueryFilters : filters}
              <div className="investigation-actions">
                {queryActionLabels.map((label) => (
                  <Button
                    key={label}
                    type={label === "查询" ? "primary" : "default"}
                    onClick={() => runOriginalAction(label)}
                  >
                    {label === "审批" && initialTab === "clue-audit-customer"
                      ? "客户审核"
                      : label === "审批" && initialTab === "clue-audit-pending"
                        ? "内部审批"
                        : label}
                  </Button>
                ))}
              </div>
            </Form>
            <Tabs
              className="investigation-hidden-tabs"
              activeKey={tab}
              onChange={(key) => {
                if (onNavigate) {
                  onNavigate(key);
                  return;
                }
                setTab(key as keyof typeof moduleMeta);
                load(key as keyof typeof moduleMeta);
              }}
              items={[
                { key: "clue", label: "线索管理" },
                { key: "notary", label: "公证管理" },
                { key: "evidence", label: "证据管理" },
              ]}
            />
            <Table
              rowKey="id"
              loading={loading}
              size="small"
              columns={columns}
              dataSource={visibleRows}
              rowSelection={
                !isFileQuery
                  ? {
                      selectedRowKeys: selectedClues,
                      onChange: (keys) => setSelectedClues(keys as number[]),
                    }
                  : undefined
              }
              scroll={{ x: tableScrollX, y: "calc(100dvh - 395px)" }}
              pagination={{ pageSize: 20, showTotal: (n) => `共 ${n} 条` }}
              locale={{ emptyText: "没有查询到符合条件的记录" }}
            />
            {businessActionLabels.length > 0 && (
              <div className="investigation-actions investigation-actions-bottom">
                {businessActionLabels.map((label) =>
                  label === "申请费用" ? (
                    <Dropdown
                      key={label}
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "notary-paid", label: "公证费已付" },
                          { key: "notary-fee", label: "新增公证费" },
                          { key: "notary-service-fee", label: "新增公证服务费" },
                        ],
                        onClick: ({ key }) => {
                          const feeType =
                            key === "notary-paid"
                              ? "公证费已付"
                              : key === "notary-service-fee"
                                ? "公证服务费"
                                : "公证费";
                          requireSingleRow(label, (row) => openFee(row, feeType));
                        },
                      }}
                    >
                      <Button>申请费用</Button>
                    </Dropdown>
                  ) : label === "取证" ? (
                    <Dropdown
                      key={label}
                      menu={{
                        items: [
                          { key: "single", label: "单个取证" },
                          { key: "batch", label: "批量取证" },
                        ],
                        onClick: ({ key }) => key === "single"
                          ? runOriginalAction(label)
                          : openBatchCollection(),
                      }}
                    >
                      <Button>取证</Button>
                    </Dropdown>
                  ) : (                    </Dropdown>
                  ) : (
                    <Button key={label} onClick={() => runOriginalAction(label)}>
                      {label === "审批" && initialTab === "clue-audit-customer"
                        ? "客户审核"
                        : label === "审批" && initialTab === "clue-audit-pending"
                          ? "内部审批"
                          : label}
                    </Button>
                  ),
                )}              </div>
            )}
          </>
        )}
      </Card>
      <Modal
        open={createOpen}
        title={`新增${meta.title}`}
        okText="保存"
        cancelText="取消"
        onOk={() => void create()}
        onCancel={() => setCreateOpen(false)}
      >
        <Form form={createForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              label="业务编号"
              name="serial_no"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="状态" name="status" rules={[{ required: true }]}>
              <Select
                options={meta.statuses.map((v) => ({ value: v, label: v }))}
              />
            </Form.Item>
            <Form.Item
              className="span-2"
              label="标题/事项"
              name="title"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="客户" name="customer">
              <Input />
            </Form.Item>
            <Form.Item label="负责人" name="owner">
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                options={systemPersonOptions}
              />
            </Form.Item>
            {tab === "clue" && (
              <>
                <Form.Item label="调查平台" name="platform">
                  <Input />
                </Form.Item>
                <Form.Item
                  label="侵权产品"
                  name="product"
                  rules={[
                    { required: true, message: "不同产品需分别创建线索" },
                  ]}
                >
                  <Input />
                </Form.Item>
              </>
            )}
            {tab === "evidence" && (
              <Form.Item label="材料来源" name="source">
                <Input />
              </Form.Item>
            )}
            <Form.Item className="span-2" label="说明" name="description">
              <Input.TextArea rows={3} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
      <Modal
        open={batchSubmitOpen}
        title={`批量提交线索审批（${selectedRows.length} 条）`}
        okText="确认提交"
        cancelText="取消"
        onOk={submitCluesBatch}
        onCancel={() => setBatchSubmitOpen(false)}
      >
        <Alert
          type="info"
          showIcon
          message="已选线索将作为一个批次提交"
          description="服务端会统一校验全部线索；任一线索不满足提交条件时，本次不会提交任何线索。"
          style={{ marginBottom: 16 }}
        />
        <Form form={batchSubmitForm} layout="vertical">
          <Form.Item label="审批说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(turnOnAuditTarget)}
        title={`转交审核人：${turnOnAuditTarget?.serial_no || ""}`}
        okText="确认转交"
        cancelText="取消"
        confirmLoading={reviewerCandidatesLoading}
        onOk={saveTurnOnAudit}
        onCancel={() => setTurnOnAuditTarget(null)}
      >
        <Form form={turnOnAuditForm} layout="vertical">
          <Form.Item
            label="目标审核人"
            name="reviewer"
            rules={[{ required: true, message: "请选择具备线索审批岗位的审核人" }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              loading={reviewerCandidatesLoading}
              options={reviewerCandidates}
              notFoundContent={
                reviewerCandidatesLoading ? "正在加载审核人" : "没有可用审核人"
              }
            />
          </Form.Item>
          <Form.Item label="转交说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(clueReviewing)}
        title={`${clueReviewing?.status === "待客户审核" ? "客户审核确认" : "线索内部审批"}：${clueReviewing?.serial_no || ""}`}
        okText="提交审核"
        cancelText="取消"
        onOk={reviewClue}
        onCancel={() => setClueReviewing(null)}
      >
        <Form form={clueReviewForm} layout="vertical">
          {clueReviewing?.status === "待客户审核" && (
            <div className="form-grid audit-reference">
              <Form.Item label="上一级审核员">
                <Input
                  value={projectedPersonDisplayName(
                    clueReviewing.data.reviewer_display_name,
                    clueReviewing.data.reviewer,
                  )}
                  readOnly
                />
              </Form.Item>
              <Form.Item label="上一级审核意见">
                <Input.TextArea
                  value={clueReviewing.data.review_comment || "—"}
                  readOnly
                  rows={2}
                />
              </Form.Item>
            </div>
          )}
          <Form.Item
            label="审核结果"
            name="approved"
            rules={[{ required: true }]}
          >
            <Radio.Group>
              <Radio value={true}>
                <CheckCircleOutlined />{" "}
                {clueReviewing?.status === "待客户审核"
                  ? "客户确认通过，进入待取证"
                  : "内部审批通过，进入客户审核或取证"}
              </Radio>
              <Radio value={false}>驳回修改</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item
            label={
              clueReviewing?.status === "待客户审核"
                ? "客户反馈/驳回原因"
                : "审核意见/驳回原因"
            }
            name="comment"
            rules={[{ required: true, min: 2 }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(collectionTarget) || batchCollectionTargets.length > 0}
        title={batchCollectionTargets.length > 0
          ? `批量取证：已选 ${batchCollectionTargets.length} 条线索`
          : `单个取证：${collectionTarget?.serial_no || ""}`}
        okText="确认已取证"
        cancelText="取消"
        onOk={registerCollection}
        onCancel={() => {
          setCollectionTarget(null);
          setBatchCollectionTargets([]);
          setCollectionFiles([]);
        }}
      >
        <Form form={collectionForm} layout="vertical">
          <Form.Item
            label="取证机构"
            name="notary_institution"
            rules={[{ required: true, min: 2 }]}
          >
            <AutoComplete
            options={Array.from(
              new Set([
                ...notaryOfficeOptions.map((item) => item.value),
                ...rows
                  .map((row) => String(row.data.notary_institution || "").trim())
                  .filter(Boolean),
              ]),
            ).map((value) => ({ value }))}
              filterOption={(input, option) =>
                String(option?.value || "").includes(input)
              }
              placeholder="输入关键词选择或填写取证机构"
            />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="公证书号" name="notarization_no">
              <Input />
            </Form.Item>
            <Form.Item label="发票号码" name="invoice_no">
              <Input />
            </Form.Item>
          </div>
          <Form.Item
            label="取证日期"
            name="collected_at"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="warehouse_id" hidden><Input /></Form.Item>
          <Form.Item name="storage_location_id" hidden><Input /></Form.Item>
          <div className="form-grid">
            <Form.Item
              label="证物存放处"
              name="evidence_storage_path"
              rules={[{ required: true, message: "请选择证物存放处" }]}
            >
              <Cascader
                options={collectionStorageOptions}
                placeholder="请选择仓库及库位"
                showSearch
                onChange={(path) => collectionForm.setFieldsValue({
                  warehouse_id: Number(path?.[0]) || undefined,
                  storage_location_id: Number(path?.[1]) || undefined,
                })}
              />
            </Form.Item>
            <Form.Item label="证物状态" name="evidence_status" initialValue="未入库">
              <Select options={["未入库", "已入库", "已出库", "已重新入库", "已销毁"].map((value) => ({ value, label: value }))} />
            </Form.Item>
          </div>
          {batchCollectionTargets.length === 0 && <Form.Item label="证据文件">
            <input
              type="file"
              multiple
              onChange={(event) =>
                setCollectionFiles(Array.from(event.target.files || []))
              }
            />
            {collectionFiles.length > 0 && <div>已选择 {collectionFiles.length} 个文件</div>}
          </Form.Item>}
          <Form.Item label="取证说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(evidenceSource)}
        title={`建立证据目录：${evidenceSource?.serial_no || ""}`}
        okText="创建证据"
        cancelText="取消"
        onOk={createEvidence}
        onCancel={() => setEvidenceSource(null)}
      >
        <Form form={evidenceForm} layout="vertical">
          <Form.Item label="证据标题" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="负责人" name="owner" rules={[{ required: true }]}>
              <Select
                showSearch
                optionFilterProp="label"
                options={systemPersonOptions}
              />
            </Form.Item>
            <Form.Item label="材料来源" name="source">
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="证据说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(reviewing)}
        title={`公证审核：${reviewing?.serial_no || ""}`}
        okText="提交审核"
        cancelText="取消"
        onOk={review}
        onCancel={() => setReviewing(null)}
      >
        <Form form={reviewForm} layout="vertical">
          <Form.Item
            label="审核结果"
            name="approved"
            rules={[{ required: true }]}
          >
            <Radio.Group>
              <Radio value={true}>
                <CheckCircleOutlined /> 通过并自动转案件
              </Radio>
              <Radio value={false}>驳回</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item label="案件类型" name="case_type">
            <Select
              options={["民事案件", "刑事案件", "行政案件", "仲裁案件"].map(
                (v) => ({ value: v, label: v }),
              )}
            />
          </Form.Item>
          <Form.Item label="拟管辖法院" name="court">
            <Input />
          </Form.Item>
          <Form.Item label="审核意见" name="comment">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(certificateTarget)}
        title={`登记公证书：${certificateTarget?.serial_no || ""}`}
        okText="保存登记"
        cancelText="取消"
        onOk={registerCertificate}
        onCancel={() => setCertificateTarget(null)}
      >
        <Form form={certificateForm} layout="vertical">
          <Form.Item
            label="公证书编号"
            name="certificate_no"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="签发日期"
            name="issued_date"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="仓库" name="warehouse_id" rules={[{ required: true, message: "请选择仓库" }]}>
              <Select
                showSearch
                optionFilterProp="label"
                options={warehouseCatalog.filter((warehouse) => warehouse.is_active).map((warehouse) => ({ value: warehouse.id, label: warehouse.name }))}
                onChange={() => certificateForm.setFieldValue("storage_location_id", undefined)}
              />
            </Form.Item>
            <Form.Item label="库位" name="storage_location_id" rules={[{ required: true, message: "请选择库位" }]}>
              <Select showSearch optionFilterProp="label" options={storageLocationOptions(certificateWarehouseId)} />
            </Form.Item>
          </div>
          <Form.Item name="physical_received" valuePropName="checked">
            <Checkbox>纸质公证书实物已收到</Checkbox>
          </Form.Item>
          <Form.Item label="登记说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={importOpen}
        title={`${tab === "notary" ? "公证记录" : "调查线索"}批量导入`}
        okText="开始导入"
        cancelText="关闭"
        onOk={importRows}
        onCancel={() => setImportOpen(false)}
      >
        <Alert
          type="info"
          showIcon
          title={
            tab === "notary"
              ? "仅支持 UTF-8 CSV；来源线索必须存在且尚未生成公证记录。"
              : "仅支持 UTF-8 CSV；每一行只能填写一种侵权产品，重复线索不会导入。"
          }
        />
        <Space orientation="vertical" className="import-box">
          <Button icon={<DownloadOutlined />} onClick={downloadImportTemplate}>
            下载 CSV 模板
          </Button>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => setImportFile(e.target.files?.[0] || null)}
          />
          {importResult && (
            <Alert
              type={importResult.failed ? "warning" : "success"}
              showIcon
              title={`成功 ${importResult.created} 条，失败 ${importResult.failed} 条`}
              description={importResult.errors.slice(0, 8).map((x) => (
                <div key={`${x.row}-${x.error}`}>
                  第 {x.row} 行：{x.error}
                </div>
              ))}
            />
          )}
        </Space>
      </Modal>
      <Modal
        open={batchOpen}
        title={`已取证线索生成案件（已选 ${selectedClues.length} 条）`}
        okText={batchStep === 0 ? "下一步" : "生成案件"}
        cancelText="取消"
        onOk={async () => {
          if (batchStep === 0) {
            try {
              const values = await batchForm.validateFields([
                "client_position",
                "cause_or_charge",
                "case_phase",
                "handling_lawyer",
                "assistant",
                "case_type",
                "court",
              ]);
              setValidatedBatchCaseValues({ ...batchForm.getFieldsValue(true), ...values });
              setBatchStep(1);
            } catch {
              return;
            }
          } else {
            void batchCases();
          }
        }}
        onCancel={() => {
          setBatchOpen(false);
          setBatchStep(0);
          setValidatedBatchCaseValues(null);
          setResolvedClueContracts([]);
        }}
      >
        <Steps current={batchStep} size="small" items={[{ title: "基本信息" }, { title: "生成结果" }]} style={{ marginBottom: 20 }} />
        <Alert
          type="info"
          showIcon
          title="合同由线索来源调查任务自动绑定；每条已取证线索生成一个新案待分配案件。"
          style={{ marginBottom: 15 }}
        />
        <Form form={batchForm} layout="vertical">
          {batchStep === 0 && <>
            <Descriptions size="small" bordered column={1} items={resolvedClueContracts.map((item) => ({ key: item.clue_id, label: `${item.clue_no || "线索"}｜${item.customer || ""}`, children: item.contract ? `${item.contract.serial_no}｜${item.contract.title}` : item.error || "未解析到合同" }))} />
            {resolvedClueContracts.some((item) => !item.contract) && (
              selectedClues.length === 1 && contractOptions.length > 0 ? (
                <>
                  <Form.Item
                    label="补充来源任务合同（可选）"
                    name="source_contract_record_id"
                    style={{ marginTop: 16 }}
                  >
                    <Select
                      showSearch
                      optionFilterProp="label"
                      placeholder="仅列出该客户可用合同"
                      options={contractOptions.map((contract) => ({
                        value: contract.id,
                        label: `${contract.serial_no}｜${contract.title}`,
                      }))}
                    />
                  </Form.Item>
                  <Button onClick={() => void bindMissingSourceContract()}>
                    绑定并自动带入
                  </Button>
                </>
              ) : (
                <Alert
                  type="info"
                  showIcon
                  message="来源调查任务未自动关联合同"
                  description="本次可继续生成案件；案件将保留客户和线索关联，合同关联可在后续补全。"
                  style={{ marginTop: 16 }}
                />
              )
            )}
            <Alert type="info" showIcon title="案件名称默认由客户名称、案由和线索店铺/事项名称组成；调查员默认从线索带入。" style={{ marginTop: 16 }} />
            <Form.Item label="客户诉讼地位" name="client_position" rules={[{ required: true }]} style={{ marginTop: 16 }}>
              <Select options={["原告", "被告", "第三人", "申请人", "被申请人"].map((v) => ({ value: v, label: v }))} />
            </Form.Item>
            <Form.Item label="案由" name="cause_or_charge" rules={[{ required: true, message: "请填写案由" }]}>
              <Input />
            </Form.Item>
            <Form.Item label="案件阶段" name="case_phase" rules={[{ required: true }]}>
              <Select options={["等待公证书", "新案待分配", "文书准备"].map((v) => ({ value: v, label: v }))} />
            </Form.Item>
            <Form.Item label="经办律师" name="handling_lawyer" rules={[{ required: true, message: "请选择经办律师" }]}>
              <Select showSearch optionFilterProp="label" options={systemPersonOptions} placeholder="请选择系统人员" />
            </Form.Item>
            <Form.Item label="律师助理" name="assistant" rules={[{ required: true, message: "请选择律师助理" }]}>
              <Select allowClear showSearch optionFilterProp="label" options={systemPersonOptions} placeholder="请选择系统人员" />
            </Form.Item>
            <Form.Item label="案件类型" name="case_type">
              <Select
                options={["民事案件", "刑事案件", "行政案件", "仲裁案件"].map(
                  (v) => ({ value: v, label: v }),
                )}
              />
            </Form.Item>
            <Form.Item label="拟管辖法院" name="court">
              <Input />
            </Form.Item>
          </>}
          {batchStep === 1 && <Descriptions size="small" bordered column={1} items={[{ key: "status", label: "生成后案件阶段", children: batchForm.getFieldValue("case_phase") || "等待公证书" }, { key: "result", label: "关联规则", children: "客户、合同、线索及来源任务信息将自动带入案件" }]} />}
        </Form>
      </Modal>
      <Modal
        width={780}
        open={materialOpen}
        title={`${materialTarget?.serial_no || ""}｜材料目录`}
        footer={null}
        onCancel={() => setMaterialOpen(false)}
      >
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          scroll={{ x: 720 }}
          dataSource={materials}
          locale={{ emptyText: "尚未上传材料" }}
          columns={[
            {
              title: "目录",
              dataIndex: "category",
              width: 120,
              render: (v: string) => <Tag color="blue">{v}</Tag>,
            },
            {
              title: "文件名",
              dataIndex: "original_name",
              width: 280,
              ellipsis: { showTitle: true },
            },
            {
              title: "大小",
              dataIndex: "size",
              width: 90,
              render: (v: number) => `${(v / 1024).toFixed(1)} KB`,
            },
            {
              title: "上传人",
              dataIndex: "uploader",
              width: 85,
              render: (_: unknown, row: Attachment) =>
                projectedPersonDisplayName(
                  row.uploader_display_name,
                  row.uploader,
                ),
            },
            {
              title: "操作",
              key: "action",
              width: 140,
              render: (_: unknown, r: Attachment) => (
                <Space size={0}>
                  <Button
                    type="link"
                    icon={<DownloadOutlined />}
                    onClick={() => downloadMaterial(r)}
                  >
                    下载
                  </Button>
                  <Button
                    danger
                    type="link"
                    icon={<DeleteOutlined />}
                    onClick={() => deleteMaterial(r)}
                  >
                    删除
                  </Button>
                </Space>
              ),
            },
          ]}
        />
        <Form
          form={materialForm}
          layout="vertical"
          className="material-upload-form"
        >
          <div className="form-grid">
            <Form.Item
              label="材料目录"
              name="category"
              rules={[{ required: true }]}
            >
              <Select
                options={allowedCategories.map((v) => ({ value: v, label: v }))}
              />
            </Form.Item>
            <Form.Item label="批量选择文件" required>
              <input
                multiple
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.zip,.rar"
                onChange={(e) =>
                  setMaterialFiles(Array.from(e.target.files || []))
                }
              />
            </Form.Item>
          </div>
          <Form.Item label="材料说明" name="remark">
            <Input />
          </Form.Item>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={uploadMaterial}
          >
            批量上传{materialFiles.length ? `（${materialFiles.length}）` : ""}
          </Button>
        </Form>
      </Modal>
      <Drawer
        size={760}
        open={Boolean(taskTarget)}
        title={`调查任务：${taskTarget?.serial_no || ""}`}
        onClose={() => {
          setTaskTarget(null);
          setCreatingSubtask(false);
        }}
      >
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          scroll={{ x: 840 }}
          dataSource={tasks}
          columns={[
            { title: "任务编号", dataIndex: "serial_no", width: 165 },
            {
              title: "任务名称",
              dataIndex: "title",
              width: 220,
              ellipsis: { showTitle: true },
            },
            {
              title: "父调查任务",
              dataIndex: "parent_task_no",
              width: 150,
              render: (v: string, row: TaskRow) =>
                v || row.investigation_no || taskTarget?.serial_no || "—",
            },
            {
              title: "调查员",
              dataIndex: "owner",
              width: 90,
              render: (_value: unknown, row: TaskRow) =>
                row.owner_display_name || personDisplayName(row.owner),
            },
            {
              title: "调查区域",
              width: 160,
              render: (_value: unknown, row: TaskRow) =>
                row.data?.region || [row.data?.province, row.data?.city, row.data?.district].filter(Boolean).join(" ") || "—",
            },
            {
              title: "开始时间",
              width: 110,
              render: (_value: unknown, row: TaskRow) => row.data?.start_date || row.data?.authorized_from || "—",
            },
            {
              title: "结束时间",
              width: 110,
              render: (_value: unknown, row: TaskRow) => row.data?.end_date || row.deadline || row.data?.authorized_to || "—",
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 90,
              render: (v: string) => <Tag>{v}</Tag>,
            },
          ]}
        />
        <Card
          size="small"
          title={
            creatingSubtask
              ? "新增子任务"
              : tasks.length
                ? "新增主任务/子任务"
                : "创建首个调查任务"
          }
          style={{ marginTop: 16 }}
        >
          <Form form={taskForm} layout="vertical">
            <Form.Item name="authorization_scope" hidden>
              <Input />
            </Form.Item>
            {creatingSubtask && !tasks.some((task) => !task.parent_task_id) && (
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
                message={`父调查任务：${taskTarget?.serial_no || "当前调查任务"}`}
                description="本次子任务将自动继承当前调查任务的客户、合同、授权范围、授权时间和调查区域。"
              />
            )}
            <Form.Item
              label="任务名称"
              name="title"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            {creatingSubtask && tasks.some((task) => !task.parent_task_id) && (
              <Form.Item
                label="父调查任务"
                name="parent_task_id"
                rules={[{ required: true, message: "请选择父任务" }]}
              >
                <Select
                  options={tasks
                    .filter((task) => !task.parent_task_id)
                    .map((task) => ({
                      value: task.id,
                      label: `${task.serial_no}｜${task.title}`,
                    }))}
                />
              </Form.Item>
            )}
            <div className="form-grid">
              {!isLegacyInvestigationRecord(taskTarget) &&
                !taskTarget?.data.contract_id &&
                !taskTarget?.data.contract_record_id && (
                  <Form.Item
                    label="关联合同"
                    name="contract_record_id"
                    rules={[{ required: true, message: "请绑定与调查客户一致的合同" }]}
                  >
                    <Select
                      showSearch
                      optionFilterProp="label"
                      placeholder="选择后将固定绑定到调查任务"
                      options={contractOptions.map((contract) => ({
                        value: contract.id,
                        label: `${contract.serial_no}｜${contract.title}`,
                      }))}
                    />
                  </Form.Item>
                )}
              <Form.Item
                label="调查员"
                name="owner"
                rules={[{ required: true }]}
              >
                <Select
                  showSearch
                  filterOption={(input, option) =>
                    String(option?.search_text || option?.label || "").toLocaleLowerCase().includes(input.toLocaleLowerCase())
                  }
                  placeholder="请选择系统人员"
                  options={casePeopleOptions.map((item) => ({
                    value: item.username || item.value,
                    label: item.label || item.value,
                    search_text: item.search_text || `${item.label || item.value} ${item.username || item.value}`,
                  }))}
                />
              </Form.Item>
              <Form.Item
                label="开始日期"
                name="start_date"
              >
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item
                label="结束日期"
                name="end_date"
              >
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item
                label="截止日期"
                name="deadline"
                rules={[{ required: true }]}
              >
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item label="优先级" name="priority">
                <Select
                  options={["普通", "紧急", "特急"].map((v) => ({
                    value: v,
                    label: v,
                  }))}
                />
              </Form.Item>
            </div>
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message={`授权区域：${taskAuthorizationScope || "未配置"}`}
              description={`授权时间：${taskTarget?.data.authorized_from || "未配置"} 至 ${taskTarget?.data.authorized_to || "未配置"}`}
            />
            <div className="form-grid">
              <Form.Item
                label="调查省份"
                name="province"
                rules={[{ required: true, message: "请选择授权范围内的调查省份" }]}
              >
                <Select
                  placeholder="请选择授权范围内的省份"
                  options={taskScopeGroups.map((group) => ({
                    value: group.province,
                    label: group.province,
                  }))}
                  onChange={() => taskForm.setFieldsValue({
                    city: undefined,
                    district: undefined,
                    region_path: [],
                  })}
                />
              </Form.Item>
              <Form.Item
                label="调查城市"
                name="city"
                rules={[{ required: true, message: "请选择授权范围内的调查城市" }]}
              >
                <Select
                  placeholder="请选择授权范围内的城市"
                  disabled={!taskSelectedProvince}
                  options={taskCityOptions.map((city) => ({ value: city, label: city }))}
                  onChange={() => taskForm.setFieldsValue({ district: undefined, region_path: [] })}
                />
              </Form.Item>
              <Form.Item
                label="调查区/县"
                name="district"
                rules={[{ required: true, message: "请选择调查城市下的区/县" }]}
              >
                <Select
                  placeholder="请选择调查城市下的区/县"
                  disabled={!taskCity}
                  options={taskDistrictOptions.map((district) => ({ value: district, label: district }))}
                  onChange={(district) => {
                    if (taskSelectedProvince && taskCity) {
                      taskForm.setFieldValue("region_path", [taskSelectedProvince, taskCity, district]);
                    }
                  }}
                />
              </Form.Item>
            </div>
            <Form.Item label="备注" name="description">
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item
              label="调查区域"
              name="region_path"
              rules={[{ required: true, type: "array", min: 3, message: "请选择调查区域" }]}
              extra="按省、市、区/县选择调查区域，系统会自动继承到任务并限制在授权范围内"
            >
              <Cascader
                options={taskRegionOptions}
                placeholder="请选择调查区域"
                showSearch
                expandTrigger="hover"
                onChange={(path) => {
                  const [provinceValue, cityValue, districtValue] = (path || []) as string[];
                  taskForm.setFieldsValue({
                    province: provinceValue || "",
                    city: cityValue || "",
                    district: districtValue || "",
                  });
                }}
              />
            </Form.Item>
            <Space>
              <Button type="primary" onClick={() => void createTask("complete")}>
                完成
              </Button>
              <Button onClick={() => void createTask("continue")}>
                继续分配
              </Button>
            </Space>
          </Form>
        </Card>
      </Drawer>
      <Modal
        width={1040}
        open={Boolean(investigationDetail)}
        title={`调查详情：${investigationDetail?.serial_no || ""}`}
        footer={
          <Button onClick={() => setInvestigationDetail(null)}>关闭</Button>
        }
        onCancel={() => setInvestigationDetail(null)}
      >
        <Descriptions
          bordered
          size="small"
          column={2}
          items={investigationDetailItems}
        />
        {investigationDetail?.module === "clue" && <div className="clue-workspace">
          <Typography.Title level={5}>线索文件</Typography.Title>
          <Table<Attachment>
            rowKey="id"
            size="small"
            loading={clueWorkspaceLoading}
            pagination={false}
            dataSource={clueWorkspace?.clue_files || []}
            columns={[
              { title: "上传人", width: 120, render: (_, row) => row.uploader_display_name || row.uploader || "—" },
              { title: "文件名称", dataIndex: "original_name" },
              { title: "文档日期", width: 150, render: (_, row) => String(row.created_at || "").replace("T", " ").slice(0, 19) || "—" },
              { title: "操作", width: 80, render: (_, row) => <Button type="link" onClick={() => downloadMaterial(row)}>下载</Button> },
            ]}
          />
          <Typography.Title level={5}>取证信息</Typography.Title>
          <Table<ClueEvidenceRow>
            rowKey="id"
            size="small"
            loading={clueWorkspaceLoading}
            pagination={false}
            rowSelection={{ type: "radio", selectedRowKeys: selectedEvidenceId ? [selectedEvidenceId] : [], onChange: (keys) => setSelectedEvidenceId(Number(keys[0]) || null) }}
            dataSource={clueWorkspace?.evidence || []}
            scroll={{ x: 1180 }}
            columns={[
              { title: "取证编号", dataIndex: "serial_no", width: 170 },
              { title: "取证日期", width: 120, render: (_, row) => row.data.collected_at || "—" },
              { title: "取证机构", width: 180, render: (_, row) => row.data.notary_institution || "—" },
              { title: "公证书号", width: 180, render: (_, row) => row.data.notarization_no || row.data.certificate_no || "—" },
              { title: "发票号", width: 140, render: (_, row) => row.data.invoice_no || "—" },
              { title: "证物存放处", width: 180, render: (_, row) => row.data.storage_location || "—" },
              { title: "证物状态", width: 110, render: (_, row) => row.data.storage_state || row.data.evidence_status || row.status || "—" },
              { title: "文件", width: 80, render: (_, row) => row.files?.length || 0 },
            ]}
          />
          <Space style={{ marginTop: 12 }}>
            <Button danger disabled={!selectedEvidence?.can_delete} onClick={() => void deleteSelectedEvidence()}>删除</Button>
            <Button disabled={!selectedEvidence?.can_edit} onClick={openEvidenceEditor}>修改</Button>
          </Space>
        </div>}
      </Modal>
      <Modal
        open={Boolean(editingEvidence)}
        title={`修改取证信息：${editingEvidence?.serial_no || ""}`}
        okText="保存"
        cancelText="取消"
        onOk={() => void saveEvidenceEdit()}
        onCancel={() => { setEditingEvidence(null); evidenceEditForm.resetFields(); }}
      >
        <Form form={evidenceEditForm} layout="vertical">
          <Form.Item label="取证机构" name="notary_institution" rules={[{ required: true, message: "请输入取证机构" }]}>
            <AutoComplete options={notaryOfficeOptions} placeholder="选择或填写取证机构" />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="公证书号" name="certificate_no"><Input /></Form.Item>
            <Form.Item label="取证时间" name="collected_at" rules={[{ required: true, message: "请选择取证时间" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
            <Form.Item label="发票号码" name="invoice_no"><Input /></Form.Item>
            <Form.Item label="证物状态" name="evidence_status"><Select options={["未入库", "已入库", "已出库", "已重新入库", "已销毁"].map(value => ({ value, label: value }))} /></Form.Item>
          </div>
          <Form.Item label="证物存放处" name="storage_location"><Input /></Form.Item>
          <Form.Item label="证据文件"><Input disabled value={editingEvidence?.files?.map(file => file.original_name).join("、") || "无"} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(editTarget)}
        title={`修改调查记录：${editTarget?.serial_no || ""}`}
        okText="保存修改"
        cancelText="取消"
        onOk={saveEdit}
        onCancel={() => setEditTarget(null)}
      >
        <Form form={editForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              label="标题/事项"
              name="title"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="权利人/客户" name="customer">
              <Input />
            </Form.Item>
            <Form.Item
              label="负责人/调查员（请通过分配入口变更）"
              name="owner"
              rules={[{ required: true }]}
            >
              <Select disabled options={systemPersonOptions} />
            </Form.Item>
            <Form.Item label="调查区域" name="region">
              <Input />
            </Form.Item>
            <Form.Item label="权利类型" name="right_type">
              <Select
                allowClear
                options={["商标", "专利", "著作权", "不正当竞争"].map(
                  (value) => ({ value, label: value }),
                )}
              />
            </Form.Item>
            {editTarget?.module === "clue" && (
              <>
                <Form.Item label="侵权方式" name="infringement_method">
                  <Select
                    allowClear
                    options={CLUE_INFRINGEMENT_METHOD_OPTIONS.map((value) => ({
                      value,
                      label: value,
                    }))}
                  />
                </Form.Item>
                <Form.Item label="销售渠道" name="sales_channel">
                  <Select
                    allowClear
                    showSearch
                    optionFilterProp="label"
                    options={CLUE_SALES_CHANNEL_OPTIONS.map((value) => ({
                      value,
                      label: value,
                    }))}
                  />
                </Form.Item>
                <Form.Item label="侵权产品" name="product">
                  <Input />
                </Form.Item>
                <Form.Item label="店铺链接" name="store_url">
                  <Input />
                </Form.Item>
                <Form.Item label="店铺名称" name="shop_name">
                  <Input />
                </Form.Item>
                <Form.Item label="店铺Id" name="shop_id">
                  <Input />
                </Form.Item>
                <Form.Item label="有无产品" name="has_product">
                  <Radio.Group
                    options={[
                      { value: true, label: "有" },
                      { value: false, label: "无" },
                    ]}
                  />
                </Form.Item>
                <Form.Item label="来源" name="source">
                  <Input />
                </Form.Item>
                <Form.Item label="调查地址" name="address">
                  <Input />
                </Form.Item>
                <Form.Item label="调查日期" name="investigated_at">
                  <DatePicker style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item label="生产商" name="producer">
                  <Input />
                </Form.Item>
                <Form.Item label="主体信息" name="indictee">
                  <Input />
                </Form.Item>
                <Form.Item label="调查辅助" name="investigation_assistant">
                  <Select
                    allowClear
                    showSearch
                    optionFilterProp="label"
                    options={systemPersonOptions}
                  />
                </Form.Item>
              </>
            )}
            {editTarget?.module === "task" && (
              <>
                <Form.Item label="截止日期" name="deadline">
                  <DatePicker style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item label="优先级" name="priority">
                  <Select
                    options={["普通", "紧急", "特急"].map((value) => ({
                      value,
                      label: value,
                    }))}
                  />
                </Form.Item>
              </>
            )}
          </div>
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(assignTarget)}
        title={`分配调查员：${assignTarget?.serial_no || ""}`}
        okText="确认分配"
        cancelText="取消"
        onOk={saveAssign}
        onCancel={() => setAssignTarget(null)}
      >
        <Form form={assignForm} layout="vertical">
          <Form.Item
            label="调查员"
            name="investigator"
            rules={[{ required: true, min: 1 }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={systemPersonOptions}
            />
          </Form.Item>
          <Form.Item label="分配说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(feeTarget)}
        title={`申请调查费用：${feeTarget?.serial_no || ""}`}
        okText="创建费用申请"
        cancelText="取消"
        onOk={saveFee}
        onCancel={() => setFeeTarget(null)}
      >
        <Form form={feeForm} layout="vertical">
          <Form.Item
            label="费用类型"
            name="fee_type"
            rules={[{ required: true }]}
          >
            <Select
              options={[
                "调查取证费",
                "公证费已付",
                "公证费",
                "公证服务费",
                "差旅费",
                "购买样品费",
                "其他",
              ].map((value) => ({ value, label: value }))}
            />
          </Form.Item>
          <Form.Item
            label="申请金额"
            name="amount"
            rules={[{ required: true }]}
          >
            <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="费用说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={760}
        open={Boolean(linkedCase)}
        title={`关联案件：${linkedCase?.serial_no || ""}`}
        footer={<Button onClick={() => setLinkedCase(null)}>关闭</Button>}
        onCancel={() => setLinkedCase(null)}
      >
        <Descriptions
          bordered
          size="small"
          column={2}
          items={
            linkedCase
              ? [
                  { key: "no", label: "案号", children: linkedCase.serial_no },
                  {
                    key: "status",
                    label: "阶段",
                    children: <Tag color="blue">{linkedCase.status}</Tag>,
                  },
                  {
                    key: "title",
                    label: "案件名称",
                    children: linkedCase.title,
                    span: 2,
                  },
                  {
                    key: "customer",
                    label: "客户/原告",
                    children: linkedCase.customer,
                  },
                  {
                    key: "opponent",
                    label: "对方当事人",
                    children:
                      linkedCase.data.opponent ||
                      linkedCase.data.defendant ||
                      "—",
                  },
                  {
                    key: "court",
                    label: "法院",
                    children: linkedCase.data.court || "—",
                  },
                  {
                    key: "owner",
                    label: "负责人",
                    children: projectedPersonDisplayName(
                      linkedCase.owner_display_name,
                      linkedCase.owner,
                    ),
                  },
                  {
                    key: "description",
                    label: "说明",
                    children: linkedCase.description || "—",
                    span: 2,
                  },
                ]
              : []
          }
        />
      </Modal>
    </>
  );
}

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Timeline,
  Upload,
} from "antd";
import {
  DownloadOutlined,
  FileDoneOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  ToolOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { consumeBusinessRecordDetailTarget } from "./businessRecordDetailNavigation";
import { formatRequiredDate } from "./formSafety";
import RecordImportButton from "./RecordImportButton";
import "./seal-center.css";

type SealAsset = {
  id: number;
  code: string;
  name: string;
  seal_type: string;
  custodian: string;
  location: string;
  status: string;
  usage_count: number;
  last_used_at?: string;
  remark: string;
};
type SealRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  description: string;
  data: Record<string, any>;
  seal_asset?: SealAsset;
  created_at: string;
  updated_at: string;
};
type Summary = {
  total: number;
  pending: number;
  waiting_stamp: number;
  completed: number;
};
type EventRow = {
  id: number;
  action: string;
  from_status: string;
  to_status: string;
  operator: string;
  comment: string;
  created_at: string;
};
type AttachmentRow = {
  id: number;
  original_name: string;
  category: string;
  size: number;
  uploader: string;
  created_at: string;
};
type RelationRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  data: Record<string, any>;
};
const statusColors: Record<string, string> = {
  草稿: "default",
  待审批: "orange",
  待用印: "blue",
  已用印: "green",
  已归档: "cyan",
  已拒绝: "red",
  已撤回: "default",
};
const sealStatusOptions = [
  { value: "待审批", label: "待审核" },
  { value: "待用印", label: "已审待用印" },
  { value: "已拒绝", label: "审核拒绝" },
  { value: "已撤回", label: "已撤回" },
  { value: "已用印", label: "已用印" },
  { value: "已归档", label: "已归档" },
];
const assetColors: Record<string, string> = {
  可用: "green",
  停用: "default",
  维修: "orange",
  遗失: "red",
};
const sealTypes = [
  "合同章",
  "公章",
  "所函专用章",
  "法人章",
  "发票章",
  "财务专用章",
  "财务三排章",
];

export default function SealCenterPage({
  initialView,
  onNavigate,
}: {
  initialView: string;
  onNavigate?: (route: string) => void;
}) {
  const tabFromView = (v: string) =>
    v.startsWith("seal-audit")
      ? "audit"
      : v.startsWith("seal-admin-")
        ? "admin"
        : v === "seal-admin"
          ? "assets"
          : "my";
  const statusFromView = (v: string): string[] => {
    const routeStatuses: Record<string, string[]> = {
      "seal-my-pending": ["草稿", "待审批"],
      "seal-my-stamping": ["待用印"],
      "seal-my-used": ["已用印", "已归档"],
      "seal-my-refused": ["已拒绝"],
      "seal-my-withdrawn": ["已撤回"],
      "seal-audit-pending": ["待审批"],
      "seal-audit-stamping": ["待用印"],
      "seal-audit-refused": ["已拒绝"],
      "seal-admin-pending": ["待用印"],
      "seal-admin-used": ["已用印"],
      "seal-admin-query": [],
    };
    return routeStatuses[v] || [];
  };
  const [tab, setTab] = useState(tabFromView(initialView));
  const [rows, setRows] = useState<SealRow[]>([]);
  const [assets, setAssets] = useState<SealAsset[]>([]);
  const [cases, setCases] = useState<RelationRow[]>([]);
  const [contracts, setContracts] = useState<RelationRow[]>([]);
  const [customers, setCustomers] = useState<RelationRow[]>([]);
  const [summary, setSummary] = useState<Summary>({
    total: 0,
    pending: 0,
    waiting_stamp: 0,
    completed: 0,
  });
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [query, setQuery] = useState<Record<string, any>>({});
  const [selectedKeys, setSelectedKeys] = useState<(string | number)[]>([]);
  const [editingApplication, setEditingApplication] = useState<SealRow | null>(
    null,
  );
  const [createOpen, setCreateOpen] = useState(false);
  const [assetOpen, setAssetOpen] = useState(false);
  const [editAsset, setEditAsset] = useState<SealAsset | null>(null);
  const [detail, setDetail] = useState<SealRow | null>(null);
  const [history, setHistory] = useState<EventRow[]>([]);
  const [attachments, setAttachments] = useState<AttachmentRow[]>([]);
  const [action, setAction] = useState<{
    type: "approve" | "reject" | "stamp" | "archive";
    row: SealRow;
  } | null>(null);
  const [createForm] = Form.useForm();
  const [assetForm] = Form.useForm();
  const [actionForm] = Form.useForm();
  const [queryForm] = Form.useForm();
  const selectedUseType = Form.useWatch("use_type", createForm);
  const load = async () => {
    setLoading(true);
    try {
      const view = ["admin", "assets"].includes(tab) ? "all" : tab;
      const routeStatuses = statusFromView(initialView);
      const [apps, inventory, caseResult, contractResult, customerResult] =
        await Promise.all([
          api.get("/seals/applications", {
            params: {
              view,
              keyword,
              page_size: 100,
              serial_no: query.serial_no,
              applicant: query.applicant,
              record_status:
                routeStatuses.length === 1
                  ? routeStatuses[0]
                  : query.record_status,
              date_from: query.application_date?.[0]?.format("YYYY-MM-DD"),
              date_to: query.application_date?.[1]?.format("YYYY-MM-DD"),
              case_no: query.case_no,
              contract_no: query.contract_no,
              customer: query.customer,
              use_type: query.use_type,
              file_name: query.file_name,
            },
          }),
          api.get("/seals/assets", {
            params: { keyword: tab === "assets" ? keyword : "" },
          }),
          api.get("/records", { params: { module: "case", page_size: 100 } }),
          api.get("/records", {
            params: { module: "contract", page_size: 100 },
          }),
          api.get("/records", {
            params: { module: "customer", page_size: 100 },
          }),
        ]);
      setRows(apps.data.items);
      setSummary(apps.data.summary);
      setAssets(inventory.data.items);
      setCases(caseResult.data.items);
      setContracts(contractResult.data.items);
      setCustomers(customerResult.data.items);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "用印中心数据加载失败");
    } finally {
      setLoading(false);
    }
  };
  const openCaseDetail = (caseNo: unknown) => {
    const serialNo = String(caseNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前用印申请未关联案件");
      return;
    }
    rememberCaseDetailTarget({ serial_no: serialNo });
    onNavigate?.("case-company");
  };
  const openContractDetail = (contractNo: unknown) => {
    const serialNo = String(contractNo || "").trim();
    if (!serialNo || serialNo === "—") {
      message.warning("当前用印申请未关联合同");
      return;
    }
    rememberContractDetailTarget({ serial_no: serialNo });
    onNavigate?.("contract-company");
  };
  const openCustomerDetail = (customer: unknown, customerNo?: unknown) => {
    const title = String(customer || "").trim();
    const serialNo = String(customerNo || "").trim();
    if (!title && !serialNo) return message.warning("当前申请未关联客户");
    rememberCustomerDetailTarget({ title, serial_no: serialNo });
    onNavigate?.("customer-company");
  };
  useEffect(() => {
    setTab(tabFromView(initialView));
  }, [initialView]);
  useEffect(() => {
    load();
  }, [tab, initialView, query]);
  const availableAssets = useMemo(
    () => assets.filter((x) => x.status === "可用"),
    [assets],
  );
  const visibleRows = useMemo(() => {
    const statuses = statusFromView(initialView);
    let result = statuses.length
      ? rows.filter((row) => statuses.includes(row.status))
      : rows;
    const contains = (v: unknown, k: string) =>
      !query[k] || String(v || "").includes(String(query[k]).trim());
    const dates = query.application_date;
    return result.filter(
      (r) =>
        contains(r.serial_no, "serial_no") &&
        contains(r.owner, "applicant") &&
        contains(r.data.case_no, "case_no") &&
        contains(r.data.contract_no, "contract_no") &&
        contains(r.customer, "customer") &&
        contains(r.data.document_names, "file_name") &&
        (!query.use_type || String(r.data.use_type || "") === query.use_type) &&
        (!dates ||
          (r.created_at.slice(0, 10) >= dates[0].format("YYYY-MM-DD") &&
            r.created_at.slice(0, 10) <= dates[1].format("YYYY-MM-DD"))),
    );
  }, [rows, initialView, query]);
  const createApplication = async () => {
    try {
      const v = await createForm.validateFields();
      const data = {
        ...(editingApplication?.data || {}),
        ...v,
        use_date: formatRequiredDate(v.use_date, "计划用印日期"),
      };
      if (editingApplication)
        await api.patch(`/seals/applications/${editingApplication.id}`, data);
      else await api.post("/seals/applications", data);
      message.success(
        editingApplication ? "用印申请已修改" : "用印申请已保存为草稿",
      );
      setCreateOpen(false);
      setEditingApplication(null);
      createForm.resetFields();
      load();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(
        error?.response?.data?.detail || error?.message || "申请保存失败",
      );
    }
  };
  const openApplication = (row?: SealRow) => {
    setEditingApplication(row || null);
    createForm.resetFields();
    createForm.setFieldsValue(
      row
        ? {
            ...row.data,
            title: row.title,
            customer: row.customer,
            description: row.description,
            use_date: dayjs(row.data.use_date),
          }
        : {
            use_date: dayjs().add(1, "day"),
            copies: 1,
            delivery_method: "现场用印",
            is_electronic_seal: false,
            is_offline_print: false,
          },
    );
    setCreateOpen(true);
  };
  const submit = async (row: SealRow) => {
    try {
      await api.post(`/seals/applications/${row.id}/submit`, {
        comment: "申请人确认材料无误并提交",
      });
      message.success("已提交用印审批");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "提交失败");
    }
  };
  const withdraw = async (row: SealRow) => {
    Modal.confirm({
      title: "撤回用印申请",
      content: `确认撤回 ${row.serial_no}？撤回后该申请将停止审批。`,
      okText: "确认撤回",
      cancelText: "取消",
      okButtonProps: { danger: true },
      async onOk() {
        try {
          await api.post(`/seals/applications/${row.id}/withdraw`, {
            comment: "申请人撤回待审批用印申请",
          });
          message.success("用印申请已撤回");
          load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "撤回失败");
        }
      },
    });
  };
  const removeDraft = async (row: SealRow) => {
    Modal.confirm({
      title: "删除用印草稿",
      content: `确认删除草稿 ${row.serial_no}？仅无附件的草稿可删除。`,
      okText: "确认删除",
      cancelText: "取消",
      okButtonProps: { danger: true },
      async onOk() {
        try {
          await api.delete(`/seals/applications/${row.id}`);
          message.success("用印草稿已删除");
          setSelectedKeys((keys) => keys.filter((key) => key !== row.id));
          load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "删除失败");
        }
      },
    });
  };
  const runAction = async () => {
    if (!action) return;
    const v = await actionForm.validateFields();
    try {
      if (action.type === "approve" || action.type === "reject")
        await api.post(`/seals/applications/${action.row.id}/approve`, {
          approved: action.type === "approve",
          comment: v.comment || "",
        });
      else if (action.type === "stamp")
        await api.post(`/seals/applications/${action.row.id}/stamp`, v);
      else
        await api.post(`/seals/applications/${action.row.id}/archive`, {
          comment: v.comment || "",
        });
      message.success(
        {
          approve: "审批已通过",
          reject: "申请已拒绝",
          stamp: "实际用印已登记",
          archive: "材料已归档",
        }[action.type],
      );
      setAction(null);
      actionForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "操作失败");
    }
  };
  const loadDetailFiles = async (row: SealRow) => {
    try {
      const { data } = await api.get("/attachments", {
        params: { record_id: row.id, category: "用印文件" },
      });
      setAttachments(data.items);
    } catch {
      setAttachments([]);
    }
  };
  const openDetail = async (row: SealRow) => {
    setDetail(row);
    setAttachments([]);
    try {
      const [historyResult] = await Promise.all([
        api.get(`/records/${row.id}/history`),
        loadDetailFiles(row),
      ]);
      setHistory(historyResult.data.items);
    } catch {
      setHistory([]);
    }
  };
  const downloadAttachment = async (item: AttachmentRow) => {
    try {
      const response = await api.get(`/attachments/${item.id}/download`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = item.original_name;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "用印文件下载失败");
    }
  };
  const uploadSealFile = async (file: File) => {
    if (!detail) return;
    const body = new FormData();
    body.append("file", file);
    body.append("record_id", String(detail.id));
    body.append("category", "用印文件");
    try {
      await api.post("/attachments", body);
      message.success(`已上传用印文件：${file.name}`);
      await loadDetailFiles(detail);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "用印文件上传失败");
    }
  };
  const removeSealFile = async (item: AttachmentRow) => {
    try {
      await api.delete(`/attachments/${item.id}`);
      message.success("用印文件已删除");
      if (detail) await loadDetailFiles(detail);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "用印文件删除失败");
    }
  };
  useEffect(() => {
    const target = consumeBusinessRecordDetailTarget("seal");
    if (!target) return;
    void (async () => {
      try {
        const { data } = await api.get(`/records/${target.id}`);
        if (data.module !== "seal") throw new Error("关联记录不是用印申请");
        await openDetail(data);
      } catch (error: any) {
        message.error(
          error?.response?.data?.detail || error?.message || "用印详情加载失败",
        );
      }
    })();
  }, []);
  const packageDownload = async (selected: SealRow[]) => {
    try {
      const res = await api.post(
        "/seals/applications/package-download",
        { application_ids: selected.map((row) => row.id) },
        { responseType: "blob" },
      );
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `用印文件-${dayjs().format("YYYYMMDD")}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已将 ${selected.length} 条用印申请的附件打包为 ZIP`);
    } catch (error: any) {
      if (error?.response?.data instanceof Blob) {
        try {
          const detail = JSON.parse(await error.response.data.text()).detail;
          message.error(detail || "打包下载失败");
          return;
        } catch {}
      }
      message.error(error?.response?.data?.detail || "打包下载失败");
    }
  };
  const saveAsset = async () => {
    const v = await assetForm.validateFields();
    try {
      if (editAsset) await api.patch(`/seals/assets/${editAsset.id}`, v);
      else await api.post("/seals/assets", v);
      message.success(editAsset ? "印章资料已更新" : "印章已入库");
      setAssetOpen(false);
      setEditAsset(null);
      assetForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "印章保存失败");
    }
  };
  const openAsset = (item?: SealAsset) => {
    setEditAsset(item || null);
    assetForm.setFieldsValue(
      item || { seal_type: "公章", custodian: "admin", status: "可用" },
    );
    setAssetOpen(true);
  };
  const displayStatus = (v: string) =>
    sealStatusOptions.find((option) => option.value === v)?.label || v;
  const appColumns = [
    {
      title: "编号",
      dataIndex: "serial_no",
      width: 175,
      render: (v: string, r: SealRow) => (
        <Button type="link" onClick={() => openDetail(r)}>
          {v}
        </Button>
      ),
    },
    { title: "申请人", dataIndex: "owner", width: 90 },
    {
      title: "申请时间",
      dataIndex: "created_at",
      width: 110,
      render: (v: string) => dayjs(v).format("YYYY-M-D"),
    },
    {
      title: "用印状态",
      dataIndex: "status",
      width: 105,
      render: (v: string) => (
        <Tag color={statusColors[v] || "blue"}>{displayStatus(v)}</Tag>
      ),
    },
    {
      title: "用印类型",
      width: 95,
      render: (_: unknown, r: SealRow) =>
        r.data.use_type ||
        (r.data.case_no
          ? "案件用印"
          : r.data.contract_no
            ? "合同用印"
            : "行政用印"),
    },
    {
      title: "印章类型",
      width: 130,
      render: (_: unknown, r: SealRow) =>
        r.seal_asset?.seal_type || r.data.seal_name || "—",
    },
    {
      title: "文件数",
      width: 70,
      render: (_: unknown, r: SealRow) => r.data.copies || 0,
    },
    {
      title: "案号",
      width: 145,
      render: (_: unknown, r: SealRow) =>
        r.data.case_no ? (
          <Button type="link" onClick={() => openCaseDetail(r.data.case_no)}>
            {r.data.case_no}
          </Button>
        ) : (
          "—"
        ),
    },
    {
      title: "合同号",
      width: 145,
      render: (_: unknown, r: SealRow) =>
        r.data.contract_no ? (
          <Button
            type="link"
            onClick={() => openContractDetail(r.data.contract_no)}
          >
            {r.data.contract_no}
          </Button>
        ) : (
          "—"
        ),
    },
    { title: "客户", dataIndex: "customer", width: 190, ellipsis: true, render: (value: string, r: SealRow) => value ? <Button type="link" onClick={() => openCustomerDetail(value, r.data.customer_no)}>{value}</Button> : "—" },
    {
      title: "审核人",
      width: 90,
      render: (_: unknown, r: SealRow) => r.data.approver || "—",
    },
    {
      title: "审核时间",
      width: 110,
      render: (_: unknown, r: SealRow) => r.data.approved_at || "—",
    },
    {
      title: "审核意见",
      width: 180,
      render: (_: unknown, r: SealRow) => r.data.approval_comment || "—",
    },
    {
      title: "",
      key: "actions",
      width: 260,
      render: (_: unknown, r: SealRow) => (
        <Space size={0}>
          <Button type="link" onClick={() => openDetail(r)}>
            查看
          </Button>
          {tab === "my" && r.status === "草稿" && (
            <>
              <Button type="link" onClick={() => submit(r)}>
                提交
              </Button>
              <Button danger type="link" onClick={() => void removeDraft(r)}>
                删除
              </Button>
            </>
          )}
          {tab === "audit" && r.status === "待审批" && (
            <>
              <Button
                type="link"
                onClick={() => {
                  setAction({ type: "approve", row: r });
                  actionForm.resetFields();
                }}
              >
                通过
              </Button>
              <Button
                danger
                type="link"
                onClick={() => {
                  setAction({ type: "reject", row: r });
                  actionForm.resetFields();
                }}
              >
                拒绝
              </Button>
            </>
          )}
          {tab === "admin" && r.status === "已用印" && (
            <Button
              type="link"
              onClick={() => {
                setAction({ type: "archive", row: r });
                actionForm.resetFields();
              }}
            >
              归档
            </Button>
          )}
        </Space>
      ),
    },
  ];
  const assetColumns = [
    { title: "印章编号", dataIndex: "code", width: 130 },
    { title: "印章名称", dataIndex: "name", width: 240 },
    { title: "类别", dataIndex: "seal_type", width: 110 },
    { title: "保管人", dataIndex: "custodian", width: 100 },
    { title: "存放位置", dataIndex: "location", width: 190 },
    {
      title: "累计用印",
      dataIndex: "usage_count",
      width: 95,
      render: (v: number) => `${v} 份`,
    },
    {
      title: "最近使用",
      dataIndex: "last_used_at",
      width: 160,
      render: (v: string) => (v ? dayjs(v).format("YYYY-MM-DD HH:mm") : "—"),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 85,
      render: (v: string) => <Tag color={assetColors[v] || "blue"}>{v}</Tag>,
    },
    {
      title: "操作",
      width: 90,
      fixed: "right" as const,
      render: (_: unknown, r: SealAsset) => (
        <Button type="link" onClick={() => openAsset(r)}>
          维护
        </Button>
      ),
    },
  ];
  const selectedRows = visibleRows.filter((row) =>
    selectedKeys.includes(row.id),
  );
  const selectedRow = selectedRows.length === 1 ? selectedRows[0] : null;
  const routeStatuses = statusFromView(initialView);
  const routeStatus = routeStatuses.length === 1 ? routeStatuses[0] : "";
  const tabItems = [
    { key: "my", label: "我的申请" },
    { key: "audit", label: `用印审批（${summary.pending}）` },
    { key: "admin", label: `行政用印（${summary.waiting_stamp}）` },
    { key: "assets", label: "印章管理" },
  ];
  return (
    <>
      <div className="seal-stats">
        <Card>
          <Statistic title="全部申请" value={summary.total} />
        </Card>
        <Card>
          <Statistic
            title="待审批"
            value={summary.pending}
            styles={{ content: { color: "#f39c12" } }}
          />
        </Card>
        <Card>
          <Statistic
            title="待用印"
            value={summary.waiting_stamp}
            styles={{ content: { color: "#3c8dbc" } }}
          />
        </Card>
        <Card>
          <Statistic
            title="已完成"
            value={summary.completed}
            styles={{ content: { color: "#00a65a" } }}
          />
        </Card>
      </div>
      <Card
        className="panel seal-original-panel"
        title={tab === "assets" ? "印章资产管理" : "用印申请列表"}
      >
        {tab !== "assets" && (
          <Form form={queryForm} className="seal-query" onFinish={setQuery}>
            <Form.Item label="申请编号" name="serial_no">
              <Input />
            </Form.Item>
            <Form.Item label="申请人" name="applicant">
              <Input />
            </Form.Item>
            <Form.Item label="申请日期" name="application_date">
              <DatePicker.RangePicker />
            </Form.Item>
            <Form.Item label="案件编号" name="case_no">
              <Input />
            </Form.Item>
            <Form.Item label="合同编号" name="contract_no">
              <Input />
            </Form.Item>
            <Form.Item label="客户名称" name="customer">
              <Input />
            </Form.Item>
            <Form.Item label="用印状态">
              <Select
                disabled
                value={routeStatus || undefined}
                placeholder="请选择"
                options={sealStatusOptions}
              />
            </Form.Item>
            <Form.Item label="用印类型" name="use_type">
              <Select
                allowClear
                placeholder="请选择"
                options={["合同用印", "案件用印", "行政用印"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item label="文件名称" name="file_name">
              <Input />
            </Form.Item>
            <div className="seal-query-actions">
              <Button type="primary" htmlType="submit">
                查询
              </Button>
            </div>
          </Form>
        )}
        <Tabs
          className="seal-original-tabs"
          activeKey={tab}
          onChange={setTab}
          items={tabItems}
        />
        {tab === "assets" ? (
          <>
            <div className="seal-asset-toolbar">
              <span>印章资产台账</span>
              <Space>
                <Input
                  allowClear
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                  onPressEnter={load}
                  placeholder="编号、名称、类别或保管人"
                />
                <Button icon={<ReloadOutlined />} onClick={load}>
                  刷新
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => openAsset()}
                >
                  新增印章
                </Button>
              </Space>
            </div>
            <Table
              rowKey="id"
              loading={loading}
              size="small"
              columns={assetColumns.map((column: any) =>
                column.title === "操作"
                  ? { ...column, fixed: undefined }
                  : column,
              )}
              dataSource={assets}
              scroll={{ x: 1240 }}
              pagination={{ pageSize: 20, showTotal: (n) => `共 ${n} 枚印章` }}
              locale={{ emptyText: "暂无印章资产，请由管理员新增入库" }}
            />
          </>
        ) : (
          <Table
            rowKey="id"
            loading={loading}
            size="small"
            rowSelection={{
              selectedRowKeys: selectedKeys,
              onChange: (keys) => setSelectedKeys(keys as (string | number)[]),
            }}
            columns={appColumns}
            dataSource={visibleRows}
            scroll={{ x: 1850 }}
            pagination={{ pageSize: 20, showTotal: (n) => `共 ${n} 条记录` }}
            locale={{
              emptyText:
                initialView === "seal-my-pending" ? (
                  <span>
                    没有查询到符合条件的记录，可以去{" "}
                    <Button
                      className="seal-empty-link"
                      type="link"
                      onClick={() => openApplication()}
                    >
                      申请用印
                    </Button>
                    。
                  </span>
                ) : (
                  "没有查询到符合条件的记录"
                ),
            }}
            footer={
              visibleRows.length &&
              [
                "seal-my-pending",
                "seal-my-stamping",
                "seal-admin-pending",
              ].includes(initialView)
                ? () => (
                    <div className="seal-table-actions">
                      {initialView === "seal-my-pending" && (
                        <>
                          <Button onClick={() => openApplication()}>
                            申请用印
                          </Button>
                          <Button
                            disabled={
                              !selectedRow || selectedRow.status !== "草稿"
                            }
                            onClick={() =>
                              selectedRow && openApplication(selectedRow)
                            }
                          >
                            修改
                          </Button>
                          <Button
                            disabled={
                              !selectedRow || selectedRow.status !== "草稿"
                            }
                            onClick={() => selectedRow && submit(selectedRow)}
                          >
                            提交
                          </Button>
                          <Button
                            disabled={
                              !selectedRow || selectedRow.status !== "待审批"
                            }
                            onClick={() => selectedRow && withdraw(selectedRow)}
                          >
                            撤回
                          </Button>
                        </>
                      )}
                      {initialView === "seal-my-stamping" && (
                        <Button
                          disabled={!selectedRow}
                          onClick={() => selectedRow && withdraw(selectedRow)}
                        >
                          撤回
                        </Button>
                      )}
                      {initialView === "seal-admin-pending" && (
                        <>
                          <Button
                            disabled={!selectedRow}
                            onClick={() => {
                              if (selectedRow) {
                                setAction({ type: "stamp", row: selectedRow });
                                actionForm.setFieldsValue({
                                  actual_copies: selectedRow.data.copies,
                                  operator: "admin",
                                });
                              }
                            }}
                          >
                            标记用印
                          </Button>
                          <Button
                            disabled={!selectedRows.length}
                            onClick={() => packageDownload(selectedRows)}
                          >
                            打包下载
                          </Button>
                        </>
                      )}
                    </div>
                  )
                : undefined
            }
          />
        )}
      </Card>
      <Modal
        open={createOpen}
        title={editingApplication ? "修改用印申请" : "申请用印"}
        width={760}
        okText="保存草稿"
        cancelText="取消"
        onOk={createApplication}
        onCancel={() => {
          setCreateOpen(false);
          setEditingApplication(null);
        }}
      >
        <Form form={createForm} layout="vertical">
          <div className="seal-form-grid">
            <Form.Item
              label="申请标题"
              name="title"
              rules={[{ required: true }]}
            >
              <Input placeholder="例如：民事起诉状用印" />
            </Form.Item>
            <Form.Item label="客户/单位" name="customer">
              <Select
                showSearch
                allowClear
                optionFilterProp="label"
                options={customers.map((x) => ({
                  value: x.title || x.customer,
                  label: `${x.title || x.customer}｜${x.serial_no}`,
                }))}
              />
            </Form.Item>
            <Form.Item
              label="关联案号"
              name="case_no"
              rules={selectedUseType === "案件用印" ? [{ required: true, message: "案件用印必须选择关联案件" }] : []}
            >
              <Select showSearch allowClear optionFilterProp="label" options={cases.map((x) => ({ value: x.serial_no, label: `${x.serial_no}｜${x.title}` }))} />
            </Form.Item>
            <Form.Item
              label="关联合同号"
              name="contract_no"
              rules={selectedUseType === "合同用印" ? [{ required: true, message: "合同用印必须选择关联合同" }] : []}
            >
              <Select showSearch allowClear optionFilterProp="label" options={contracts.map((x) => ({ value: x.serial_no, label: `${x.serial_no}｜${x.customer}｜${x.title}` }))} />
            </Form.Item>
            <Form.Item
              label="用印类型"
              name="use_type"
              rules={[{ required: true }]}
            >
              <Select
                options={["合同用印", "案件用印", "行政用印"].map((x) => ({
                  value: x,
                  label: x,
                }))}
              />
            </Form.Item>
            <Form.Item
              label="选择印章"
              name="seal_asset_id"
              rules={[{ required: true }]}
            >
              <Select
                options={availableAssets.map((x) => ({
                  value: x.id,
                  label: `${x.name}（${x.code}）`,
                }))}
              />
            </Form.Item>
            <Form.Item
              label="计划用印日期"
              name="use_date"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="用印份数"
              name="copies"
              rules={[{ required: true }]}
            >
              <InputNumber min={1} max={999} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="办理方式" name="delivery_method">
              <Select
                options={["现场用印", "邮寄用印", "外带用印"].map((x) => ({
                  value: x,
                  label: x,
                }))}
              />
            </Form.Item>
            <Form.Item label="是否电子印章" name="is_electronic_seal">
              <Select
                options={[
                  { value: true, label: "是" },
                  { value: false, label: "否" },
                ]}
              />
            </Form.Item>
            <Form.Item label="是否打印盖章" name="is_offline_print">
              <Select
                options={[
                  { value: true, label: "需要" },
                  { value: false, label: "不需要" },
                ]}
              />
            </Form.Item>
          </div>
          <Alert
            type="info"
            showIcon
            title="请先保存草稿，再在用印详情中上传真实用印文件；未上传文件不能提交审批。"
            style={{ marginBottom: 12 }}
          />
          <Form.Item
            label="用印用途"
            name="purpose"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="申请说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={assetOpen}
        title={editAsset ? "维护印章资料" : "新增印章入库"}
        okText="保存"
        cancelText="取消"
        onOk={saveAsset}
        onCancel={() => setAssetOpen(false)}
      >
        <Form form={assetForm} layout="vertical">
          <Form.Item label="印章编号" name="code" rules={[{ required: true }]}>
            <Input disabled={Boolean(editAsset)} />
          </Form.Item>
          <Form.Item label="印章名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="seal-form-grid">
            <Form.Item
              label="印章类别"
              name="seal_type"
              rules={[{ required: true }]}
            >
              <Select
                options={sealTypes.map((x) => ({ value: x, label: x }))}
              />
            </Form.Item>
            <Form.Item
              label="保管人"
              name="custodian"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="存放位置" name="location">
              <Input />
            </Form.Item>
            {editAsset && (
              <Form.Item label="状态" name="status">
                <Select
                  options={["可用", "停用", "维修", "遗失"].map((x) => ({
                    value: x,
                    label: x,
                  }))}
                />
              </Form.Item>
            )}
          </div>
          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(action)}
        title={
          {
            approve: "审批通过",
            reject: "审批拒绝",
            stamp: "登记实际用印",
            archive: "归档用印材料",
          }[action?.type || "approve"]
        }
        okText="确认"
        cancelText="取消"
        onOk={runAction}
        onCancel={() => setAction(null)}
      >
        <Form form={actionForm} layout="vertical">
          {action?.type === "stamp" && (
            <>
              <Form.Item
                label="实际用印份数"
                name="actual_copies"
                rules={[{ required: true }]}
              >
                <InputNumber
                  min={1}
                  max={action.row.data.copies}
                  style={{ width: "100%" }}
                />
              </Form.Item>
              <Form.Item
                label="用印操作人"
                name="operator"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                label="归档号"
                name="archive_no"
                rules={[{ required: true }]}
              >
                <Input placeholder="例如：YY-2026-0042" />
              </Form.Item>
            </>
          )}
          <Form.Item
            label="审批/操作意见"
            name="comment"
            rules={
              action?.type === "reject"
                ? [{ required: true, message: "拒绝时必须填写原因" }]
                : []
            }
          >
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Drawer
        open={Boolean(detail)}
        size={640}
        title={`用印详情：${detail?.serial_no || ""}`}
        onClose={() => {
          setDetail(null);
          setAttachments([]);
        }}
      >
        {detail && (
          <>
            <Descriptions
              bordered
              size="small"
              column={2}
              items={[
                {
                  key: "title",
                  label: "申请标题",
                  children: detail.title,
                  span: 2,
                },
                {
                  key: "customer",
                  label: "客户",
                  children: detail.customer ? <Button type="link" onClick={() => openCustomerDetail(detail.customer, detail.data.customer_no)}>{detail.customer}</Button> : "—",
                },
                {
                  key: "case",
                  label: "关联案号",
                  children: detail.data.case_no ? (
                    <Button
                      type="link"
                      onClick={() => openCaseDetail(detail.data.case_no)}
                    >
                      {detail.data.case_no}
                    </Button>
                  ) : (
                    "—"
                  ),
                },
                {
                  key: "contract",
                  label: "关联合同号",
                  children: detail.data.contract_no ? (
                    <Button
                      type="link"
                      onClick={() =>
                        openContractDetail(detail.data.contract_no)
                      }
                    >
                      {detail.data.contract_no}
                    </Button>
                  ) : (
                    "—"
                  ),
                },
                {
                  key: "seal",
                  label: "印章",
                  children: detail.seal_asset?.name || detail.data.seal_name,
                },
                {
                  key: "copies",
                  label: "申请份数",
                  children: detail.data.copies,
                },
                {
                  key: "electronic",
                  label: "电子印章",
                  children: detail.data.is_electronic_seal ? "是" : "否",
                },
                {
                  key: "print",
                  label: "打印盖章",
                  children: detail.data.is_offline_print ? "需要" : "不需要",
                },
                {
                  key: "purpose",
                  label: "用途",
                  children: detail.data.purpose,
                  span: 2,
                },
                {
                  key: "method",
                  label: "办理方式",
                  children: detail.data.delivery_method,
                },
                {
                  key: "date",
                  label: "计划日期",
                  children: detail.data.use_date,
                },
                {
                  key: "actual",
                  label: "实际份数",
                  children: detail.data.actual_copies || "—",
                },
                {
                  key: "archive",
                  label: "归档号",
                  children: detail.data.archive_no || "—",
                },
                {
                  key: "status",
                  label: "当前状态",
                  children: (
                    <Tag color={statusColors[detail.status]}>
                      {detail.status}
                    </Tag>
                  ),
                },
                { key: "owner", label: "申请人", children: detail.owner },
              ]}
            />
            <h3 className="seal-history-title">
              <FileDoneOutlined /> 用印文件
            </h3>
            {detail.status === "草稿" && (
              <Upload
                multiple
                showUploadList={false}
                beforeUpload={(file) => {
                  void uploadSealFile(file as File);
                  return Upload.LIST_IGNORE;
                }}
              >
                <Button icon={<UploadOutlined />}>上传用印文件</Button>
              </Upload>
            )}
            <Table
              size="small"
              rowKey="id"
              style={{ marginTop: 10 }}
              pagination={false}
              locale={{
                emptyText: "暂无用印文件；提交审批前请上传至少一个文件",
              }}
              dataSource={attachments}
              columns={[
                {
                  title: "文件名称",
                  dataIndex: "original_name",
                  ellipsis: true,
                },
                { title: "上传人", dataIndex: "uploader", width: 90 },
                {
                  title: "上传时间",
                  dataIndex: "created_at",
                  width: 145,
                  render: (value: string) =>
                    dayjs(value).format("YYYY-MM-DD HH:mm"),
                },
                {
                  title: "操作",
                  width: 130,
                  render: (_: unknown, item: AttachmentRow) => (
                    <Space size={0}>
                      <Button
                        type="link"
                        icon={<DownloadOutlined />}
                        onClick={() => void downloadAttachment(item)}
                      >
                        下载
                      </Button>
                      {detail.status === "草稿" && (
                        <Button
                          type="link"
                          danger
                          onClick={() => void removeSealFile(item)}
                        >
                          删除
                        </Button>
                      )}
                    </Space>
                  ),
                },
              ]}
            />
            <h3 className="seal-history-title">
              <FileDoneOutlined /> 流程记录
            </h3>
            <Timeline
              items={history.map((x) => ({
                color: x.to_status === "已拒绝" ? "red" : "green",
                children: (
                  <div>
                    <b>{x.action}</b>{" "}
                    <Tag>
                      {x.from_status || "创建"} → {x.to_status}
                    </Tag>
                    <div>
                      {x.operator} ·{" "}
                      {dayjs(x.created_at).format("YYYY-MM-DD HH:mm")}
                    </div>
                    {x.comment && <small>{x.comment}</small>}
                  </div>
                ),
              }))}
            />
          </>
        )}
      </Drawer>
    </>
  );
}

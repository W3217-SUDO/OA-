import { useEffect, useMemo, useState } from "react";
import type { Key } from "react";
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Progress,
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
  CheckCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FileAddOutlined,
  FolderOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  StopOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "./api";
import { formatRequiredDate } from "./formSafety";
import RecordImportButton from "./RecordImportButton";
import "./document-center.css";

type RecordRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
  description?: string;
  data: Record<string, any>;
};
type Attachment = {
  id: number;
  record_id: number | null;
  record_no: string;
  record_title: string;
  category: string;
  original_name: string;
  content_type: string;
  size: number;
  uploader: string;
  remark: string;
  created_at: string;
};
type Template = {
  id: number;
  name: string;
  category: string;
  version: string;
  description: string;
  fields: string[];
  is_active: boolean;
};
type HistoryEvent = {
  id: number;
  action: string;
  from_status: string;
  to_status: string;
  operator: string;
  comment: string;
  created_at: string;
};
const archiveCategories = ["委托材料", "证据材料", "诉讼文书", "裁判文书"];
const allCategories = [
  ...archiveCategories,
  "收文附件",
  "发文附件",
  "合同附件",
  "财务凭证",
  "普通附件",
];
const fileSize = (n: number) =>
  n >= 1048576
    ? `${(n / 1048576).toFixed(2)} MB`
    : `${Math.max(1, Math.round(n / 1024))} KB`;

type ReceiptRow = RecordRow & {
  data: Record<string, any> & {
    case_no?: string;
    plaintiff?: string;
    defendant?: string;
    court_no?: string;
    court_name?: string;
    document_date?: string;
    uploaded_at?: string;
    import_status?: string;
    uploader?: string;
    hearing_lawyer?: string;
    assistant?: string;
    brand_manager?: string;
    case_manager?: string;
    handling_lawyer?: string;
  };
};

export default function DocumentCenterPage({
  initialView,
}: {
  initialView: string;
}) {
  const profile = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("user") || "{}");
    } catch {
      return {};
    }
  }, []);
  const first =
    initialView === "documents-template"
      ? "templates"
      : initialView === "documents-archive"
        ? "archive"
        : initialView === "documents-files"
          ? "files"
          : initialView === "documents-official"
            ? "official"
            : initialView === "documents-my"
              ? "my-receipts"
              : initialView === "documents-company"
                ? "company-receipts"
                : "documents";
  const [tab, setTab] = useState(first);
  const [documents, setDocuments] = useState<RecordRow[]>([]);
  const [cases, setCases] = useState<RecordRow[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [summary, setSummary] = useState({
    documents: 0,
    pending_receipt: 0,
    received: 0,
    attachments: 0,
    archive_materials: 0,
    templates: 0,
  });
  const [loading, setLoading] = useState(false);
  const [documentOpen, setDocumentOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [templateOpen, setTemplateOpen] = useState(false);
  const [viewing, setViewing] = useState<RecordRow | null>(null);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [actionStatus, setActionStatus] = useState("");
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [uploadTarget, setUploadTarget] = useState<RecordRow | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [documentForm] = Form.useForm();
  const [uploadForm] = Form.useForm();
  const [templateForm] = Form.useForm();
  const [actionForm] = Form.useForm();
  const [receiptForm] = Form.useForm();
  const [receiptQuery, setReceiptQuery] = useState<Record<string, any>>({});
  const [selectedReceiptKeys, setSelectedReceiptKeys] = useState<Key[]>([]);
  const [receiptDateOpen, setReceiptDateOpen] = useState(false);
  const [receiptDate, setReceiptDate] = useState<ReturnType<typeof dayjs> | null>(
    null,
  );
  const load = async () => {
    setLoading(true);
    try {
      const [docRes, caseRes, fileRes, templateRes, summaryRes] =
        await Promise.all([
          api.get("/records", {
            params: { module: "document", page_size: 100 },
          }),
          api.get("/records", { params: { module: "case", page_size: 100 } }),
          api.get("/attachments"),
          api.get("/templates"),
          api.get("/documents/summary"),
        ]);
      setDocuments(docRes.data.items);
      setCases(caseRes.data.items);
      setAttachments(fileRes.data.items);
      setTemplates(templateRes.data.items);
      setSummary(summaryRes.data);
    } catch {
      message.error("收发文数据加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    setTab(first);
    load();
  }, [initialView]);
  const createDocument = async () => {
    const v = await documentForm.validateFields();
    try {
      await api.post("/records", {
        module: "document",
        serial_no: `SW${Date.now()}`,
        title: v.title,
        customer: v.customer || "",
        status: "待登记",
        owner: v.owner || profile.username || "admin",
        department: profile.department || "上海分所",
        description: v.description || "",
        data: {
          direction: v.direction,
          document_date: v.document_date?.format("YYYY-MM-DD") || "",
          case_no: v.case_no || "",
          sender: v.sender || "",
        },
      });
      message.success("收发文草稿已保存，请完成登记");
      setDocumentOpen(false);
      documentForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "登记失败");
    }
  };
  const openUpload = (target?: RecordRow, category?: string) => {
    setUploadTarget(target || null);
    setFile(null);
    uploadForm.setFieldsValue({
      record_id: target?.id,
      category: category || "普通附件",
      remark: "",
    });
    setUploadOpen(true);
  };
  const upload = async () => {
    const v = await uploadForm.validateFields();
    if (!file) {
      message.warning("请选择文件");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    if (v.record_id) form.append("record_id", String(v.record_id));
    form.append("category", v.category);
    form.append("remark", v.remark || "");
    try {
      const officialImport = tab === "official" && !v.record_id;
      await api.post(officialImport ? "/documents/official/upload" : "/attachments", form);
      message.success(officialImport ? "官文已上传并生成收文记录" : "文件上传成功");
      setUploadOpen(false);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "上传失败");
    }
  };
  const download = async (row: Attachment) => {
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
      message.error("下载失败");
    }
  };
  const deleteFile = async (id: number) => {
    try {
      await api.delete(`/attachments/${id}`);
      message.success("附件已删除");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const saveTemplate = async () => {
    const v = await templateForm.validateFields();
    try {
      if (editingTemplate)
        await api.patch(`/templates/${editingTemplate.id}`, {
          ...v,
          fields: v.fields || [],
        });
      else await api.post("/templates", { ...v, fields: v.fields || [] });
      message.success(editingTemplate ? "模板已更新" : "模板已创建");
      setTemplateOpen(false);
      setEditingTemplate(null);
      templateForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "模板保存失败");
    }
  };
  const editTemplate = (row: Template) => {
    setEditingTemplate(row);
    templateForm.setFieldsValue({
      name: row.name,
      category: row.category,
      version: row.version,
      description: row.description,
      fields: row.fields,
    });
    setTemplateOpen(true);
  };
  const toggleTemplate = async (row: Template) => {
    try {
      await api.patch(`/templates/${row.id}`, { is_active: !row.is_active });
      message.success(row.is_active ? "模板已停用" : "模板已启用");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "状态修改失败");
    }
  };
  const deleteTemplate = async (id: number) => {
    try {
      await api.delete(`/templates/${id}`);
      message.success("模板已删除");
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const openDocument = async (row: RecordRow) => {
    setViewing(row);
    try {
      const { data } = await api.get(`/records/${row.id}/history`);
      setHistory(data.items);
    } catch {
      message.error("流程记录加载失败");
    }
  };
  const startAction = (row: RecordRow, toStatus: string) => {
    setViewing(row);
    setActionStatus(toStatus);
    actionForm.resetFields();
    actionForm.setFieldsValue({ action_date: dayjs(), handler: profile.display_name || profile.username || "管理者" });
  };
  const submitAction = async () => {
    if (!viewing) return;
    const v = await actionForm.validateFields();
    try {
      const { data } = await api.post(`/documents/${viewing.id}/transition`, {
        to_status: actionStatus,
        action_date: formatRequiredDate(v.action_date, "办理日期"),
        handler: v.handler || "",
        archive_no: v.archive_no || "",
        archive_location: v.archive_location || "",
        comment: v.comment || "",
      });
      message.success(
        actionStatus === "待签收"
          ? "登记完成"
          : actionStatus === "已签收"
            ? data.data.direction === "发文"
              ? "已确认送达"
              : "已确认签收"
            : "文档已归档",
      );
      setActionStatus("");
      setViewing(data);
      const result = await api.get(`/records/${data.id}/history`);
      setHistory(result.data.items);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "办理失败");
    }
  };
  const documentAction = (r: RecordRow) =>
    r.status === "待登记" ? (
      <Button type="link" onClick={() => startAction(r, "待签收")}>
        完成登记
      </Button>
    ) : r.status === "待签收" ? (
      <Button
        type="link"
        icon={<CheckCircleOutlined />}
        onClick={() => startAction(r, "已签收")}
      >
        {r.data.direction === "发文" ? "确认送达" : "确认签收"}
      </Button>
    ) : r.status === "已签收" ? (
      <Button
        type="link"
        icon={<FolderOutlined />}
        onClick={() => startAction(r, "已归档")}
      >
        归档
      </Button>
    ) : null;
  const documentColumns = [
    {
      title: "文号",
      dataIndex: "serial_no",
      width: 160,
      render: (v: string, r: RecordRow) => (
        <a onClick={() => openDocument(r)}>{v}</a>
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
    { title: "客户", dataIndex: "customer", width: 170 },
    {
      title: "关联案号",
      key: "case",
      width: 145,
      render: (_: unknown, r: RecordRow) => r.data.case_no || "—",
    },
    {
      title: "来文/送达单位",
      key: "sender",
      width: 160,
      render: (_: unknown, r: RecordRow) => r.data.sender || "—",
    },
    { title: "负责人", dataIndex: "owner", width: 90 },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (v: string) => (
        <Tag
          color={v === "已归档" ? "green" : v === "已签收" ? "blue" : "orange"}
        >
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
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => openDocument(r)}
          >
            详情
          </Button>
          <Button
            type="link"
            icon={<UploadOutlined />}
            onClick={() =>
              openUpload(
                r,
                r.data.direction === "发文" ? "发文附件" : "收文附件",
              )
            }
          >
            附件
          </Button>
          {documentAction(r)}
        </Space>
      ),
    },
  ];
  const fileColumns = [
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
      render: (v: string) => v || "公共文件",
    },
    {
      title: "关联业务",
      dataIndex: "record_title",
      width: 220,
      ellipsis: true,
    },
    { title: "大小", dataIndex: "size", width: 90, render: fileSize },
    { title: "上传人", dataIndex: "uploader", width: 90 },
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
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => download(r)}
          >
            下载
          </Button>
          <Popconfirm
            title="确定删除此附件？"
            onConfirm={() => deleteFile(r.id)}
          >
            <Button danger type="link" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];
  const templateColumns = [
    { title: "模板名称", dataIndex: "name", width: 220 },
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
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => editTemplate(r)}
          >
            编辑
          </Button>
          <Popconfirm
            title={`确定${r.is_active ? "停用" : "启用"}此模板？`}
            onConfirm={() => toggleTemplate(r)}
          >
            <Button type="link" icon={<StopOutlined />}>
              {r.is_active ? "停用" : "启用"}
            </Button>
          </Popconfirm>
          <Popconfirm
            title="确定删除此模板？"
            onConfirm={() => deleteTemplate(r.id)}
          >
            <Button danger type="link" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];
  const archiveRows = useMemo(
    () =>
      cases.map((c) => {
        const categories = new Set(
          attachments
            .filter((a) => a.record_id === c.id)
            .map((a) => a.category),
        );
        const done = archiveCategories.filter((x) => categories.has(x)).length;
        return {
          ...c,
          categories,
          done,
          percent: (done / archiveCategories.length) * 100,
        };
      }),
    [cases, attachments],
  );
  const archiveColumns = [
    { title: "案号", dataIndex: "serial_no", width: 155 },
    { title: "案件名称", dataIndex: "title", width: 250 },
    { title: "客户", dataIndex: "customer", width: 190 },
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
          onClick={() => openUpload(r, "委托材料")}
        >
          上传材料
        </Button>
      ),
    },
  ];
  const receiptRows = useMemo<ReceiptRow[]>(() => {
    const live = documents
      .filter((d) => (d.data.direction || "收文") === "收文")
      .map(
        (d) =>
          ({
            ...d,
            data: {
              ...d.data,
              case_no: d.data.case_no || d.serial_no,
              plaintiff: d.data.plaintiff || d.customer,
              defendant: d.data.defendant || d.data.sender || "—",
              court_no: d.data.court_no || "—",
              court_name: d.data.court_name || d.data.sender || "—",
              document_date: d.data.document_date || d.data.received_at || "",
              uploaded_at: d.data.uploaded_at || d.data.registered_at || "",
              uploader: d.data.uploader || d.owner,
              import_status: d.data.import_status || "已导入",
              hearing_lawyer: d.data.hearing_lawyer || d.owner,
              assistant: d.data.assistant || "—",
              brand_manager: d.data.brand_manager || "—",
              case_manager: d.data.case_manager || "—",
              handling_lawyer: d.data.handling_lawyer || d.owner,
            },
          }) as ReceiptRow,
      );
    return live;
  }, [documents]);
  const searchedReceipts = useMemo(
    () =>
      receiptRows.filter((r) => {
        const q = receiptQuery,
          d = r.data;
        const names = [profile.username, profile.display_name].filter(Boolean);
        if (tab === "my-receipts" && !names.includes(d.uploader || r.owner))
          return false;
        const contains = (value: unknown, key: string) =>
          !q[key] ||
          String(value || "")
            .toLowerCase()
            .includes(String(q[key]).trim().toLowerCase());
        const ur = q.upload_range,
          rr = q.receipt_range,
          ud = d.uploaded_at || "",
          rd = d.document_date || "";
        return (
          contains(d.case_no, "case_no") &&
          contains(r.title, "file_name") &&
          contains(d.court_no, "court_no") &&
          contains(d.court_name, "court_name") &&
          contains(d.plaintiff, "plaintiff") &&
          contains(d.defendant, "defendant") &&
          contains(d.hearing_lawyer, "hearing_lawyer") &&
          contains(d.case_manager, "case_manager") &&
          contains(d.handling_lawyer, "handling_lawyer") &&
          contains(d.assistant, "assistant") &&
          contains(r.title, "document_name") &&
          (!q.import_status || d.import_status === q.import_status) &&
          (!ur ||
            (ud >= ur[0].format("YYYY-MM-DD") &&
              ud <= ur[1].format("YYYY-MM-DD"))) &&
          (!rr ||
            (rd >= rr[0].format("YYYY-MM-DD") &&
              rd <= rr[1].format("YYYY-MM-DD")))
        );
      }),
    [receiptRows, receiptQuery, profile, tab],
  );
  const showReceipt = (r: ReceiptRow) => openDocument(r);
  const officialColumns = [
    {
      title: "案号",
      key: "case_no",
      width: 145,
      render: (_: unknown, r: ReceiptRow) => (
        <a onClick={() => showReceipt(r)}>{r.data.case_no}</a>
      ),
    },
    {
      title: "原告",
      key: "plaintiff",
      width: 210,
      render: (_: unknown, r: ReceiptRow) => r.data.plaintiff || "—",
    },
    {
      title: "被告",
      key: "defendant",
      width: 245,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.defendant || "—",
    },
    {
      title: "文件名称",
      dataIndex: "title",
      width: 430,
      ellipsis: true,
      render: (v: string, r: ReceiptRow) => (
        <a onClick={() => showReceipt(r)}>{v}</a>
      ),
    },
    {
      title: "文件日期",
      key: "document_date",
      width: 105,
      render: (_: unknown, r: ReceiptRow) => r.data.document_date || "—",
    },
    {
      title: "上传日期",
      key: "uploaded_at",
      width: 105,
      render: (_: unknown, r: ReceiptRow) => r.data.uploaded_at || "—",
    },
    {
      title: "上传人",
      key: "uploader",
      width: 90,
      render: (_: unknown, r: ReceiptRow) => r.data.uploader || r.owner,
    },
    {
      title: "状态",
      key: "import_status",
      width: 80,
      render: (_: unknown, r: ReceiptRow) => (
        <span className="receipt-imported">
          {r.data.import_status || "已导入"}
        </span>
      ),
    },
  ];
  const receivedColumns = [
    {
      title: "收文日",
      key: "document_date",
      width: 100,
      render: (_: unknown, r: ReceiptRow) => r.data.document_date || "—",
    },
    {
      title: "案号",
      key: "case_no",
      width: 145,
      render: (_: unknown, r: ReceiptRow) => (
        <a onClick={() => showReceipt(r)}>{r.data.case_no}</a>
      ),
    },
    {
      title: "法院案号",
      key: "court_no",
      width: 180,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.court_no || "—",
    },
    {
      title: "原告",
      key: "plaintiff",
      width: 200,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.plaintiff || "—",
    },
    {
      title: "被告",
      key: "defendant",
      width: 220,
      ellipsis: true,
      render: (_: unknown, r: ReceiptRow) => r.data.defendant || "—",
    },
    { title: "文件名称", dataIndex: "title", width: 350, ellipsis: true },
    {
      title: "上传日期",
      key: "uploaded_at",
      width: 100,
      render: (_: unknown, r: ReceiptRow) => r.data.uploaded_at || "—",
    },
    {
      title: "开庭律师",
      key: "hearing_lawyer",
      width: 90,
      render: (_: unknown, r: ReceiptRow) => r.data.hearing_lawyer || "—",
    },
    {
      title: "律师助理",
      key: "assistant",
      width: 90,
      render: (_: unknown, r: ReceiptRow) => r.data.assistant || "—",
    },
    {
      title: "品牌管理人",
      key: "brand_manager",
      width: 100,
      render: (_: unknown, r: ReceiptRow) => r.data.brand_manager || "—",
    },
  ];
  const isReceiptView = [
    "official",
    "my-receipts",
    "company-receipts",
  ].includes(tab);
  const receiptSearch = () => setReceiptQuery(receiptForm.getFieldsValue());
  const clearReceiptSearch = () => {
    receiptForm.resetFields();
    setReceiptQuery({});
  };
  const selectedFormalReceipts = receiptRows.filter(
    (row) => row.id > 0 && selectedReceiptKeys.includes(row.id),
  );
  const deleteSelectedReceipts = async () => {
    if (!selectedFormalReceipts.length) {
      message.warning("请选择需要删除的正式收文记录");
      return;
    }
    try {
      await Promise.all(
        selectedFormalReceipts.map((row) => api.delete(`/records/${row.id}`)),
      );
      message.success(`已删除 ${selectedFormalReceipts.length} 条正式收文记录`);
      setSelectedReceiptKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除收文记录失败");
    }
  };
  const exportOfficialReceipts = async () => {
    const source = selectedFormalReceipts.length
      ? selectedFormalReceipts
      : searchedReceipts;
    try {
      const response = await api.get("/documents/official/export", {
        params: { ids: source.map((row) => row.id).join(",") },
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "官文收文.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "官文导出失败");
    }
  };
  const openReceiptDateEditor = () => {
    if (selectedFormalReceipts.length !== 1) {
      message.warning("请选择一条正式收文记录修改收文日期");
      return;
    }
    const current = selectedFormalReceipts[0].data.document_date;
    setReceiptDate(current ? dayjs(current) : dayjs());
    setReceiptDateOpen(true);
  };
  const saveReceiptDate = async () => {
    const target = selectedFormalReceipts[0];
    if (!target || !receiptDate) {
      message.warning("请选择收文日期");
      return;
    }
    const date = receiptDate.format("YYYY-MM-DD");
    try {
      await api.patch(`/records/${target.id}`, {
        data: {
          ...target.data,
          document_date: date,
          received_at: date,
        },
      });
      message.success("收文日期已修改");
      setReceiptDateOpen(false);
      setSelectedReceiptKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "修改收文日期失败");
    }
  };
  const receiptPanel = isReceiptView ? (
    <Card
      className="panel receipt-original-panel"
      title={
        tab === "official"
          ? "官文收文"
          : tab === "my-receipts"
            ? "我的收文"
            : "公司收文"
      }
    >
      <Form
        form={receiptForm}
        className="receipt-query-form"
        onFinish={receiptSearch}
      >
        {tab === "official" ? (
          <div className="receipt-filter-grid official">
            <Form.Item label="案件编号" name="case_no">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="文件名称" name="file_name">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="导入状态" name="import_status">
              <Select
                allowClear
                placeholder="请选择"
                options={["未导入", "已导入"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item label="上传日期" name="upload_range">
              <DatePicker.RangePicker />
            </Form.Item>
          </div>
        ) : (
          <div className="receipt-filter-grid">
            <Form.Item label="案件编号" name="case_no">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="法院案号" name="court_no">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="法院名称" name="court_name">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="收文日期" name="receipt_range">
              <DatePicker.RangePicker />
            </Form.Item>
            <Form.Item label="原告" name="plaintiff">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="被告" name="defendant">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="开庭律师" name="hearing_lawyer">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="上传日期" name="upload_range">
              <DatePicker.RangePicker />
            </Form.Item>
            <Form.Item label="客户管理人" name="case_manager">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="经办律师" name="handling_lawyer">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="律师助理" name="assistant">
              <Input allowClear />
            </Form.Item>
            <Form.Item label="文件名称" name="document_name">
              <Input allowClear />
            </Form.Item>
          </div>
        )}
        <div className="receipt-query-actions">
          <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>
            查询
          </Button>
          {tab === "official" && (
            <Button icon={<UploadOutlined />} onClick={() => openUpload(undefined, "收文附件")}>
              上传
            </Button>
          )}
        </div>
      </Form>
      <Table
        rowKey="id"
        loading={loading}
        size="small"
        className="receipt-table"
        rowSelection={{
          selectedRowKeys: selectedReceiptKeys,
          onChange: (keys) => setSelectedReceiptKeys(keys),
        }}
        columns={tab === "official" ? officialColumns : receivedColumns}
        dataSource={searchedReceipts}
        scroll={{ x: tab === "official" ? 1450 : 1800 }}
        pagination={{
          pageSize: 15,
          showTotal: (total) => `共 ${total} 条记录`,
          showSizeChanger: false,
        }}
      />
      <div className="receipt-footer-actions">
        {tab === "official" ? (
          <>
            <Popconfirm
              title="确定删除选中的收文记录？"
              description={
                selectedFormalReceipts.length
                  ? `将永久删除 ${selectedFormalReceipts.length} 条正式记录及其附件。`
                  : "请先选择需要删除的正式收文记录。"
              }
              onConfirm={deleteSelectedReceipts}
            >
              <Button
                danger
                size="small"
                icon={<DeleteOutlined />}
                disabled={!selectedReceiptKeys.length}
              >
                删除
              </Button>
            </Popconfirm>
            <Button
              size="small"
              icon={<EditOutlined />}
              disabled={!selectedReceiptKeys.length}
              onClick={openReceiptDateEditor}
            >
              修改收文日期
            </Button>
            <Button
              size="small"
              icon={<DownloadOutlined />}
              disabled={!searchedReceipts.length}
              onClick={exportOfficialReceipts}
            >
              {selectedFormalReceipts.length ? "导出选中" : "导出查询结果"}
            </Button>
          </>
        ) : (<>
          <Button size="small" icon={<EditOutlined />} disabled={selectedReceiptKeys.length!==1} onClick={openReceiptDateEditor}>修改收文日期</Button>
          <Button size="small" disabled={selectedReceiptKeys.length!==1} onClick={()=>{const row=receiptRows.find(item=>selectedReceiptKeys.includes(item.id));if(row)showReceipt(row)}}>更多操作</Button>
        </>)}
      </div>
    </Card>
  ) : null;
  return (
    <>
      {isReceiptView ? (
        receiptPanel
      ) : (
        <>
          <div className="document-stats">
            <Card>
              <Statistic title="收发文" value={summary.documents} />
            </Card>
            <Card>
              <Statistic
                title="待签收"
                value={summary.pending_receipt}
                styles={{ content: { color: "#f39c12" } }}
              />
            </Card>
            <Card>
              <Statistic
                title="已签收"
                value={summary.received}
                styles={{ content: { color: "#3c8dbc" } }}
              />
            </Card>
            <Card>
              <Statistic title="文件附件" value={summary.attachments} />
            </Card>
            <Card>
              <Statistic
                title="归档材料"
                value={summary.archive_materials}
                styles={{ content: { color: "#00a65a" } }}
              />
            </Card>
            <Card>
              <Statistic title="文书模板" value={summary.templates} />
            </Card>
          </div>
          <Card
            className="panel"
            title="收发文台"
            extra={
              <Space>
                {tab === "documents" && (
                  <RecordImportButton module="document" onImported={load} />
                )}
                <Button icon={<ReloadOutlined />} onClick={load}>
                  刷新
                </Button>
                {tab === "documents" && (
                  <Button
                    type="primary"
                    icon={<FileAddOutlined />}
                    onClick={() => {
                      documentForm.setFieldsValue({
                        direction: "收文",
                        owner: profile.username || "admin",
                        document_date: dayjs(),
                      });
                      setDocumentOpen(true);
                    }}
                  >
                    登记收发文
                  </Button>
                )}
                {tab === "files" && (
                  <Button
                    type="primary"
                    icon={<UploadOutlined />}
                    onClick={() => openUpload()}
                  >
                    上传文件
                  </Button>
                )}
                {tab === "templates" && (
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => {
                      setEditingTemplate(null);
                      templateForm.resetFields();
                      templateForm.setFieldsValue({
                        version: "1.0",
                        category: "诉讼文书",
                      });
                      setTemplateOpen(true);
                    }}
                  >
                    新增模板
                  </Button>
                )}
              </Space>
            }
          >
            <Tabs
              activeKey={tab}
              onChange={setTab}
              items={[
                { key: "documents", label: "收发文登记" },
                { key: "files", label: "文件附件" },
                { key: "templates", label: "文书模板" },
                { key: "archive", label: "案件归档材料" },
              ]}
            />
            {tab === "documents" ? (
              <Table
                rowKey="id"
                loading={loading}
                size="small"
                columns={documentColumns}
                dataSource={documents}
                scroll={{ x: 1400 }}
              />
            ) : tab === "files" ? (
              <Table
                rowKey="id"
                loading={loading}
                size="small"
                columns={fileColumns}
                dataSource={attachments}
                scroll={{ x: 1450 }}
              />
            ) : tab === "templates" ? (
              <Table
                rowKey="id"
                loading={loading}
                size="small"
                columns={templateColumns}
                dataSource={templates}
                scroll={{ x: 1200 }}
              />
            ) : (
              <Table
                rowKey="id"
                loading={loading}
                size="small"
                columns={archiveColumns}
                dataSource={archiveRows}
                scroll={{ x: 1300 }}
              />
            )}
          </Card>
        </>
      )}
      <Modal
        open={receiptDateOpen}
        title={`修改收文日期：${selectedFormalReceipts[0]?.serial_no || ""}`}
        okText="保存"
        cancelText="取消"
        onOk={saveReceiptDate}
        onCancel={() => setReceiptDateOpen(false)}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          title="修改后会同步更新正式收文记录，并写入操作日志。"
          style={{ marginBottom: 16 }}
        />
        <DatePicker
          value={receiptDate}
          onChange={setReceiptDate}
          format="YYYY-MM-DD"
          style={{ width: "100%" }}
        />
      </Modal>
      <Modal
        open={documentOpen}
        title="登记收发文"
        okText="保存草稿"
        cancelText="取消"
        onOk={createDocument}
        onCancel={() => setDocumentOpen(false)}
      >
        <Form form={documentForm} layout="vertical">
          <Alert
            type="info"
            showIcon
            title="保存后先进入待登记；核对资料并上传附件后点击“完成登记”。"
            style={{ marginBottom: 16 }}
          />
          <Form.Item label="文件名称" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="收发类型"
              name="direction"
              rules={[{ required: true }]}
            >
              <Select
                options={["收文", "发文"].map((v) => ({ value: v, label: v }))}
              />
            </Form.Item>
            <Form.Item
              label="文件日期"
              name="document_date"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} format="YYYY-MM-DD" />
            </Form.Item>
            <Form.Item label="负责人" name="owner">
              <Input />
            </Form.Item>
            <Form.Item label="客户" name="customer">
              <Input />
            </Form.Item>
            <Form.Item label="关联案号" name="case_no">
              <Select
                allowClear
                showSearch
                options={cases.map((c) => ({
                  value: c.serial_no,
                  label: `${c.serial_no}｜${c.title}`,
                }))}
              />
            </Form.Item>
            <Form.Item label="来文/送达单位" name="sender">
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="备注" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={uploadOpen}
        title={`上传文件${uploadTarget ? `：${uploadTarget.serial_no}` : ""}`}
        okText="开始上传"
        cancelText="取消"
        onOk={upload}
        onCancel={() => setUploadOpen(false)}
      >
        <Form form={uploadForm} layout="vertical">
          <Form.Item label="关联业务" name="record_id">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={[...cases, ...documents].map((r) => ({
                value: r.id,
                label: `${r.serial_no}｜${r.title}`,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="材料分类"
            name="category"
            rules={[{ required: true }]}
          >
            <Select
              options={allCategories.map((v) => ({ value: v, label: v }))}
            />
          </Form.Item>
          <Form.Item label="选择文件" required>
            <Upload
              beforeUpload={(f) => {
                setFile(f);
                return false;
              }}
              maxCount={1}
              onRemove={() => setFile(null)}
            >
              <Button icon={<UploadOutlined />}>选择文件（最大 20MB）</Button>
            </Upload>
          </Form.Item>
          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={templateOpen}
        title={editingTemplate ? "编辑文书模板" : "新增文书模板"}
        okText="保存模板"
        cancelText="取消"
        onOk={saveTemplate}
        onCancel={() => {
          setTemplateOpen(false);
          setEditingTemplate(null);
        }}
      >
        <Form form={templateForm} layout="vertical">
          <Form.Item label="模板名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="模板分类"
              name="category"
              rules={[{ required: true }]}
            >
              <Select
                options={[
                  "诉讼文书",
                  "非诉文书",
                  "合同文书",
                  "归档文书",
                  "内部表单",
                ].map((v) => ({ value: v, label: v }))}
              />
            </Form.Item>
            <Form.Item label="版本" name="version">
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="模板字段" name="fields">
            <Select
              mode="tags"
              tokenSeparators={[",", "，"]}
              placeholder="输入字段名后回车"
            />
          </Form.Item>
          <Form.Item label="模板说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(actionStatus)}
        title={
          actionStatus === "待签收"
            ? "完成收发文登记"
            : actionStatus === "已签收"
              ? viewing?.data.direction === "发文"
                ? "确认文件送达"
                : "确认文件签收"
              : "文档归档"
        }
        okText="确认提交"
        cancelText="取消"
        onOk={submitAction}
        onCancel={() => setActionStatus("")}
        destroyOnHidden
      >
        <Form form={actionForm} layout="vertical">
          <Alert
            type="info"
            showIcon
            title={
              actionStatus === "待签收"
                ? "登记完成后进入待签收，后续不能直接修改流程状态。"
                : actionStatus === "已签收"
                  ? "请登记实际签收/送达人和日期，完成后可进入归档。"
                  : "归档编号用于纸质及电子档案定位，归档后流程办结。"
            }
            style={{ marginBottom: 16 }}
          />
          <Form.Item
            label="办理日期"
            name="action_date"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} format="YYYY-MM-DD" />
          </Form.Item>
          {actionStatus === "已签收" && (
            <Form.Item
              label={
                viewing?.data.direction === "发文" ? "送达确认人" : "签收人"
              }
              name="handler"
              rules={[{ required: true, message: "请填写人员" }]}
            >
              <Input />
            </Form.Item>
          )}
          {actionStatus === "已归档" && (
            <>
              <Form.Item
                label="归档编号"
                name="archive_no"
                rules={[{ required: true, message: "请填写归档编号" }]}
              >
                <Input />
              </Form.Item>
              <Form.Item label="存放位置" name="archive_location">
                <Input placeholder="例如：上海档案室 A-03-12" />
              </Form.Item>
            </>
          )}
          <Form.Item label="办理说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Drawer
        size={720}
        open={Boolean(viewing) && !actionStatus}
        title={`收发文详情：${viewing?.serial_no || ""}`}
        onClose={() => setViewing(null)}
        extra={viewing && documentAction(viewing)}
      >
        {viewing && (
          <>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="文件名称" span={2}>
                {viewing.title}
              </Descriptions.Item>
              <Descriptions.Item label="收发类型">
                <Tag
                  color={viewing.data.direction === "发文" ? "blue" : "green"}
                >
                  {viewing.data.direction}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={viewing.status === "已归档" ? "green" : "blue"}>
                  {viewing.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="客户/主体" span={2}>
                {viewing.customer || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="关联案号">
                {viewing.data.case_no || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="来文/送达单位">
                {viewing.data.sender || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="负责人">
                {viewing.owner}
              </Descriptions.Item>
              <Descriptions.Item label="登记日期">
                {viewing.data.registered_at || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="签收/送达日期">
                {viewing.data.signed_at || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="签收/确认人">
                {viewing.data.signer || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="归档编号">
                {viewing.data.archive_no || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="存放位置">
                {viewing.data.archive_location || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>
                {viewing.description || "—"}
              </Descriptions.Item>
            </Descriptions>
            <Card
              size="small"
              title={`关联附件（${attachments.filter((a) => a.record_id === viewing.id).length}）`}
              style={{ marginTop: 16 }}
              extra={
                <Button
                  type="link"
                  icon={<UploadOutlined />}
                  onClick={() =>
                    openUpload(
                      viewing,
                      viewing.data.direction === "发文"
                        ? "发文附件"
                        : "收文附件",
                    )
                  }
                >
                  上传附件
                </Button>
              }
            >
              <Table
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={attachments.filter(
                  (a) => a.record_id === viewing.id,
                )}
                columns={[
                  {
                    title: "文件名",
                    dataIndex: "original_name",
                    ellipsis: true,
                  },
                  { title: "分类", dataIndex: "category", width: 100 },
                  { title: "上传人", dataIndex: "uploader", width: 80 },
                  {
                    title: "操作",
                    width: 70,
                    render: (_: unknown, r: Attachment) => (
                      <Button type="link" onClick={() => download(r)}>
                        下载
                      </Button>
                    ),
                  },
                ]}
              />
            </Card>
            <Card size="small" title="办理记录" style={{ marginTop: 16 }}>
              <Timeline
                items={history.map((x) => ({
                  color: x.to_status === "已归档" ? "green" : "blue",
                  children: (
                    <div>
                      <b>{x.action}</b>
                      {x.from_status && (
                        <span>
                          　{x.from_status} → {x.to_status}
                        </span>
                      )}
                      <div style={{ color: "#999", fontSize: 12 }}>
                        {x.operator} ·{" "}
                        {new Date(x.created_at).toLocaleString("zh-CN")}
                      </div>
                      {x.comment && <div>{x.comment}</div>}
                    </div>
                  ),
                }))}
              />
            </Card>
          </>
        )}
      </Drawer>
    </>
  );
}

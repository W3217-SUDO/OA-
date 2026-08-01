import { useEffect, useMemo, useRef, useState } from "react";
import type { Key } from "react";
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Dropdown,
  Form,
  Input,
  InputNumber,
  List,
  message,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Upload,
} from "antd";
import {
  CommentOutlined,
  DeleteOutlined,
  DownloadOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import type { UploadFile } from "antd";
import dayjs, { Dayjs } from "dayjs";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { consumeTaskDetailTarget } from "./taskDetailNavigation";
import { formatRequiredDate } from "./formSafety";
import "./task-center.css";

type TaskRow = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  workflow_status: string;
  owner: string;
  description: string;
  deadline: string;
  days_remaining: number | null;
  priority: string;
  source: string;
  reminder_due: boolean;
  reminder_text: string;
  initiator: string;
  collaborators: string[];
  case_no: string;
  plaintiff: string;
  defendant: string;
  case_stage: string;
  department: string;
  created_at: string;
  updated_at: string;
  verified_at: string;
  rejected_reason: string;
  handoff_recipient: string;
  handoff_auto_complete_at: string;
  completion_auto_confirm_at: string;
  auto_completed: boolean;
  performance_impact?: { overdue?: boolean; overdue_days?: number; penalty_points?: number };
  exception_request?: { action?: string; status?: string; reason?: string };
  latest_unread_message: string;
  latest_unread_sender: string;
  latest_unread_at: string;
  unread_count: number;
  latest_unread_notification_id?: number;
};
type Summary = {
  total: number;
  pending: number;
  processing: number;
  awaiting_confirmation: number;
  due_soon: number;
  overdue: number;
  reminders: number;
};

const appendSelectedUploadFiles = (body: FormData, files: UploadFile[]) => {
  let appended = 0;
  for (const file of files) {
    // Ant Design passes an RcFile directly to beforeUpload, while a controlled
    // Upload list may later wrap it as originFileObj. Support both shapes so a
    // selected file can never become a text-only "successful" feedback.
    const source = file.originFileObj || (file as unknown as File);
    if (source && typeof (source as Blob).arrayBuffer === "function") {
      body.append("files", source);
      appended += 1;
    }
  }
  return appended;
};
type HistoryItem = {
  id: number;
  action: string;
  operator: string;
  comment: string;
  from_status: string;
  to_status: string;
  created_at: string;
  unread?: boolean;
};
type TaskFeedbackAttachment = {
  id: number;
  original_name: string;
  category: string;
  uploader: string;
  created_at: string;
  size: number;
  remark?: string;
};
type TaskSort = {
  field: "created_at" | "deadline" | "days_remaining" | "updated_at";
  order: "ascend" | "descend";
} | null;
type CaseRecord = {
  id: number;
  serial_no: string;
  title: string;
  customer: string;
  status: string;
  owner: string;
};
type DialogAction = "reject" | "resend";
type FeeAction = "lawFee" | "platformFee" | "internalFee";
type FeeSubtype = "官费" | "第三方费用" | "代理费" | "其他费用" | "内部费用";
type CaseBatchAction = "hearing_lawyer" | "handling_lawyers" | "assistant" | "case_stage";
type TaskBatchLifecycleAction = "accept" | "complete" | "confirm" | "handoff" | "withdraw";
type TaskQuery = {
  priority?: string;
  serial_no?: string;
  title?: string;
  description?: string;
  initiator?: string;
  case_no?: string;
  source?: string;
  owner?: string;
  plaintiff?: string;
  defendant?: string;
  created_range?: [Dayjs, Dayjs];
  deadline_range?: [Dayjs, Dayjs];
};
type StatusTab = { key: string; label: string; statuses: string[] };

const EMPTY_SUMMARY: Summary = {
  total: 0,
  pending: 0,
  processing: 0,
  awaiting_confirmation: 0,
  due_soon: 0,
  overdue: 0,
  reminders: 0,
};
const statusColors: Record<string, string> = {
  待接收: "orange",
  待处理: "orange",
  处理中: "blue",
  待确认: "purple",
  已完成: "green",
  已验收: "green",
  已逾期: "red",
  已拒绝: "red",
  已停止: "default",
  已撤回: "default",
};
const createdTabs: StatusTab[] = [
  {
    key: "active",
    label: "进行中",
    statuses: ["待接收", "待处理", "处理中", "已逾期"],
  },
  { key: "finished", label: "进行中-已完成", statuses: ["已完成", "待确认"] },
  { key: "rejected", label: "进行中-拒绝", statuses: ["已拒绝"] },
  { key: "stopped", label: "进行中-已停止", statuses: ["已停止"] },
  { key: "withdrawn", label: "进行中-已撤回", statuses: ["已撤回"] },
  { key: "accepted", label: "已验收", statuses: ["已验收"] },
];
const receivedTabs: StatusTab[] = [
  { key: "pending", label: "待处理", statuses: ["待接收", "待处理"] },
  {
    key: "processing",
    label: "进行中",
    statuses: ["处理中", "已逾期"],
  },
  { key: "finished", label: "完成", statuses: ["已完成", "待确认", "已验收"] },
  { key: "stopped", label: "停止", statuses: ["已停止", "已撤回", "已拒绝"] },
];
const collaboratingTabs: StatusTab[] = [
  { key: "active", label: "进行中", statuses: ["待接收", "待处理", "处理中", "已逾期"] },
  { key: "finished", label: "完成", statuses: ["已完成", "待确认", "已验收"] },
];

const formatTaskDate = (value?: string) =>
  value ? dayjs(value).format("YYYY-M-D") : "";
const formatTaskDateTime = (value?: string) =>
  value ? dayjs(value).format("YYYY-M-D H:m:s") : "";
const contains = (value: unknown, query?: string) =>
  !query?.trim() ||
  String(value || "")
    .toLowerCase()
    .includes(query.trim().toLowerCase());

export default function TaskCenterPage({
  initialView,
  onNavigate,
}: {
  initialView: string;
  onNavigate?: (route: string) => void;
}) {
  const profile = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("user") || "{}");
    } catch {
      return {};
    }
  }, []);
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [, setSummary] = useState<Summary>(EMPTY_SUMMARY);
  const [taskMeta, setTaskMeta] = useState({
    total: 0,
    page: 1,
    pageSize: 15,
    statusCounts: {} as Record<string, number>,
  });
  const [loading, setLoading] = useState(false);
  const loadRequestRef = useRef(0);
  const [statusTab, setStatusTab] = useState("");
  const [queryForm] = Form.useForm<TaskQuery>();
  const [query, setQuery] = useState<TaskQuery>({});
  const [taskSort, setTaskSort] = useState<TaskSort>(null);
  const [selectedKeys, setSelectedKeys] = useState<Key[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [handoff, setHandoff] = useState<TaskRow | null>(null);
  const [dialog, setDialog] = useState<{
    row: TaskRow;
    action: DialogAction;
  } | null>(null);
  const [communication, setCommunication] = useState<TaskRow | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [feedbackAttachments, setFeedbackAttachments] = useState<TaskFeedbackAttachment[]>([]);
  const [taskMaterialAttachments, setTaskMaterialAttachments] = useState<TaskFeedbackAttachment[]>([]);
  const [feedbackFiles, setFeedbackFiles] = useState<UploadFile[]>([]);
  const [taskMaterialFiles, setTaskMaterialFiles] = useState<UploadFile[]>([]);
  const [createMaterialFiles, setCreateMaterialFiles] = useState<UploadFile[]>([]);
  const [caseContext, setCaseContext] = useState<{ mode: "tasks" | "logs"; record: CaseRecord } | null>(null);
  const [caseTasks, setCaseTasks] = useState<TaskRow[]>([]);
  const [caseHistory, setCaseHistory] = useState<HistoryItem[]>([]);
  const [caseContextLoading, setCaseContextLoading] = useState(false);
  const [createForm] = Form.useForm();
  const [handoffForm] = Form.useForm();
  const [dialogForm] = Form.useForm();
  const [commentForm] = Form.useForm();
  const [feeAction, setFeeAction] = useState<FeeAction | null>(null);
  const [feeSubtype, setFeeSubtype] = useState<FeeSubtype | null>(null);
  const [documentAction, setDocumentAction] = useState<"authorization" | "lawFirmLetter" | "identity" | "settlement" | null>(null);
  const [caseBatchAction, setCaseBatchAction] = useState<CaseBatchAction | null>(null);
  const [taskBatchAction, setTaskBatchAction] = useState<TaskBatchLifecycleAction | null>(null);
  const [feeForm] = Form.useForm();
  const [batchForm] = Form.useForm();
  const [taskBatchForm] = Form.useForm();
  const [documentForm] = Form.useForm();
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const taskActionLockRef = useRef(false);
  const beginTaskAction = () => {
    if (taskActionLockRef.current) return false;
    taskActionLockRef.current = true;
    setActionSubmitting(true);
    return true;
  };
  const endTaskAction = () => {
    taskActionLockRef.current = false;
    setActionSubmitting(false);
  };

  const isPersonalView = initialView.startsWith("task-my");
  const isCreated = initialView.endsWith("-created");
  const isAccepted = initialView.endsWith("-accepted");
  const isCollaborating = initialView.endsWith("-collaborating");
  const isUnread = initialView === "task-my-unread";
  const isReminder = initialView === "task-reminders";
  const canManageInitiatedTask = isPersonalView && isCreated;
  const canManageAcceptedTask =
    (isPersonalView && isAccepted) ||
    (profile.role === "admin" && initialView === "task-company-accepted");
  const canManageCompanyCreatedTask =
    profile.role === "admin" && initialView === "task-company-created";
  const hideTaskFooter =
    taskMeta.total === 0 &&
    (isCreated ||
      isCollaborating ||
      isReminder ||
      initialView === "task-dept-created" ||
      initialView === "task-dept-accepted" ||
      initialView === "task-company-created" ||
      initialView === "task-company-accepted");
  const tabs = isCreated ? createdTabs : isCollaborating ? collaboratingTabs : receivedTabs;
  const isTaskParticipant = (row: TaskRow) =>
    profile.role === "admin" ||
    [row.owner, row.initiator, ...(row.collaborators || [])].includes(profile.username);
  const canWithdrawTask = (row?: TaskRow | null) =>
    Boolean(
      row &&
        (profile.role === "admin" || row.initiator === profile.username) &&
        ["待接收", "待处理", "处理中"].includes(row.workflow_status || row.status),
    );
  const canReviewTaskException = (row?: TaskRow | null) =>
    Boolean(
      row &&
        (profile.role === "admin" ||
          row.initiator === profile.username ||
          (profile.role === "manager" && profile.department === row.department)),
    );
  const loadTaskFeedback = async (row: TaskRow) => {
    if (!isTaskParticipant(row)) {
      setHistory([]);
      setFeedbackAttachments([]);
      setTaskMaterialAttachments([]);
      return;
    }
    const [historyResult, feedbackResult, materialResult] = await Promise.allSettled([
      api.get(`/tasks/${row.id}/history`),
      api.get("/attachments", { params: { record_id: row.id, category: "任务反馈附件" } }),
      api.get("/attachments", { params: { record_id: row.id, category: "任务资料附件" } }),
    ]);
    if (historyResult.status === "fulfilled") {
      setHistory(historyResult.value.data.items || []);
    } else {
      setHistory([]);
      const error: any = historyResult.reason;
      message.error(error?.response?.data?.detail || "沟通记录加载失败，请稍后重试");
    }
    if (feedbackResult.status === "fulfilled") {
      setFeedbackAttachments(feedbackResult.value.data.items || []);
    } else {
      setFeedbackAttachments([]);
      const error: any = feedbackResult.reason;
      message.error(error?.response?.data?.detail || "任务反馈附件加载失败，请稍后重试");
    }
    if (materialResult.status === "fulfilled") {
      setTaskMaterialAttachments(materialResult.value.data.items || []);
    } else {
      setTaskMaterialAttachments([]);
      const error: any = materialResult.reason;
      message.error(error?.response?.data?.detail || "任务资料附件加载失败，请稍后重试");
    }
  };

  const load = async (
    nextQuery: TaskQuery = query,
    nextStatusTab = statusTab || tabs[0].key,
    page = 1,
    pageSize = taskMeta.pageSize,
    nextSort: TaskSort = taskSort,
  ) => {
    const requestId = ++loadRequestRef.current;
    const scope = isPersonalView
      ? "mine"
      : initialView.startsWith("task-dept")
        ? "department"
        : initialView.startsWith("task-company")
          ? "company"
          : "default";
    setLoading(true);
    try {
      const currentTab = tabs.find((item) => item.key === nextStatusTab) || tabs[0];
      const relation = isCreated
        ? "initiated"
        : isAccepted
          ? "owned"
          : isCollaborating
            ? "collaborating"
            : "owned";
      const { data } = await api.get(isUnread ? "/tasks/unread-messages" : "/tasks", {
        params: {
          scope: isUnread ? undefined : scope,
          relation: isUnread ? undefined : relation,
          statuses: isUnread ? undefined : currentTab.statuses.join(","),
          reminder_only: isReminder || undefined,
          priority: nextQuery.priority === "一般" ? "普通" : nextQuery.priority || "",
          serial_no: nextQuery.serial_no || "",
          title: nextQuery.title || "",
          description: nextQuery.description || "",
          initiator: nextQuery.initiator || "",
          case_no: nextQuery.case_no || "",
          source: nextQuery.source || "",
          owner: nextQuery.owner || "",
          plaintiff: nextQuery.plaintiff || "",
          defendant: nextQuery.defendant || "",
          created_from: nextQuery.created_range?.[0]?.format("YYYY-MM-DD"),
          created_to: nextQuery.created_range?.[1]?.format("YYYY-MM-DD"),
          deadline_from: nextQuery.deadline_range?.[0]?.format("YYYY-MM-DD"),
          deadline_to: nextQuery.deadline_range?.[1]?.format("YYYY-MM-DD"),
          page,
          page_size: pageSize,
          sort_by: nextSort?.field || undefined,
          sort_order: nextSort?.order === "ascend" ? "asc" : nextSort?.order === "descend" ? "desc" : undefined,
        },
      });
      if (requestId === loadRequestRef.current) {
        setTasks(data.items);
        setSummary(data.summary || EMPTY_SUMMARY);
        setTaskMeta({
          total: data.total || 0,
          page: data.page || page,
          pageSize: data.page_size || pageSize,
          statusCounts: data.status_counts || {},
        });
        const target = consumeTaskDetailTarget();
        if (target) {
          let targetRow = (data.items as TaskRow[]).find((row) =>
            (target.id && row.id === target.id) ||
            (target.serial_no && row.serial_no === target.serial_no),
          );
          if (!targetRow && target.serial_no) {
            const taskRes = await api.get("/tasks", { params: { serial_no: target.serial_no, page_size: 20 } });
            targetRow = (taskRes.data.items as TaskRow[]).find((row) => row.serial_no === target.serial_no);
          }
          if (targetRow) {
            setCommunication(targetRow);
            commentForm.resetFields();
            setFeedbackFiles([]);
            setTaskMaterialFiles([]);
            await loadTaskFeedback(targetRow);
          } else {
            message.warning("未找到关联任务或当前账号无权查看");
          }
        }
      }
    } catch (error: any) {
      if (requestId === loadRequestRef.current) {
        message.error(error?.response?.data?.detail || "任务中心数据加载失败");
      }
    } finally {
      if (requestId === loadRequestRef.current) setLoading(false);
    }
  };

  useEffect(() => {
    const firstTab = (isCreated ? createdTabs : isCollaborating ? collaboratingTabs : receivedTabs)[0].key;
    setStatusTab(firstTab);
    setSelectedKeys([]);
    queryForm.resetFields();
    setQuery({});
    setTaskSort(null);
    void load({}, firstTab, 1, 15, null);
  }, [initialView]);

  const scopedTasks = useMemo(() => {
    const names = [profile.username, profile.display_name].filter(Boolean);
    // Department/company ranges are authoritative server-side scopes. Applying
    // the personal relationship filter again here would collapse those pages
    // back to the current user's tasks.
    if (!isPersonalView) return tasks;
    if (isCreated) return tasks.filter((row) => names.includes(row.initiator));
    if (isAccepted)
      return profile.role === "admin"
        ? tasks
        : tasks.filter((row) => names.includes(row.owner));
    if (isCollaborating)
      return profile.role === "admin"
        ? tasks
        : tasks.filter((row) =>
            (row.collaborators || []).some((name) => names.includes(name)),
          );
    return tasks;
  }, [tasks, isPersonalView, isCreated, isAccepted, isCollaborating, profile]);

  const counts = useMemo(
    () =>
      Object.fromEntries(
        tabs.map((item) => [
          item.key,
          Object.keys(taskMeta.statusCounts).length
            ? item.statuses.reduce(
                (sum, status) => sum + Number(taskMeta.statusCounts[status] || 0),
                0,
              )
            : scopedTasks.filter((row) => item.statuses.includes(row.status)).length,
        ]),
      ),
    [tabs, scopedTasks, taskMeta.statusCounts],
  );
  const filteredTasks = useMemo(() => {
    const current = tabs.find((item) => item.key === statusTab) || tabs[0];
    if (Object.keys(taskMeta.statusCounts).length) return tasks;
    return scopedTasks.filter((row) => {
      if (!isUnread && !current.statuses.includes(row.status)) return false;
      if (
        query.priority &&
        !contains(
          row.priority,
          query.priority === "一般" ? "普通" : query.priority,
        )
      )
        return false;
      if (!contains(row.serial_no, query.serial_no)) return false;
      if (!contains(row.title, query.title)) return false;
      if (!contains(row.description, query.description)) return false;
      if (!contains(row.initiator, query.initiator)) return false;
      if (!contains(row.case_no, query.case_no)) return false;
      if (!contains(row.source, query.source)) return false;
      if (!contains(row.owner, query.owner)) return false;
      if (!contains(row.plaintiff, query.plaintiff)) return false;
      if (!contains(row.defendant, query.defendant)) return false;
      const created = dayjs(row.created_at);
      const deadline = dayjs(row.deadline);
      if (
        query.created_range &&
        (created.isBefore(query.created_range[0], "day") ||
          created.isAfter(query.created_range[1], "day"))
      )
        return false;
      if (
        query.deadline_range &&
        (deadline.isBefore(query.deadline_range[0], "day") ||
          deadline.isAfter(query.deadline_range[1], "day"))
      )
        return false;
      return true;
    });
  }, [scopedTasks, tabs, statusTab, query, tasks, taskMeta.statusCounts]);
  const selectedRows = useMemo(
    // The API has already applied the requested relation and data scope. In
    // particular admins may receive historical tasks whose initiator name no
    // longer matches the active account profile; filtering again here makes a
    // visibly selected row unusable for its permitted batch workflow.
    () => tasks.filter((row) => selectedKeys.includes(row.id)),
    [tasks, selectedKeys],
  );
  const selected = selectedRows.length === 1 ? selectedRows[0] : null;
  const createTask = async () => {
    const values = await createForm.validateFields();
    if (!beginTaskAction()) return;
    try {
      const { data: createdTask } = await api.post("/tasks", {
        ...values,
        collaborators: values.collaborators || [],
        deadline: formatRequiredDate(values.deadline, "截止日期"),
      });
      if (createMaterialFiles.length) {
        const materialBody = new FormData();
        if (!appendSelectedUploadFiles(materialBody, createMaterialFiles)) {
          throw new Error("未读取到已选择的任务资料附件");
        }
        try {
          await api.post(`/tasks/${createdTask.id}/materials`, materialBody);
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "任务已发起，但任务资料附件上传失败");
          setCreateMaterialFiles([]);
          setCreateOpen(false);
          createForm.resetFields();
          void load();
          return;
        }
      }
      message.success(createMaterialFiles.length ? "任务及资料附件已发起，等待负责人接收" : "任务已发起，等待负责人接收");
      setCreateOpen(false);
      createForm.resetFields();
      setCreateMaterialFiles([]);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "任务创建失败");
    } finally {
      endTaskAction();
    }
  };
  const submitHandoff = async () => {
    if (!handoff) return;
    const values = await handoffForm.validateFields();
    if (!beginTaskAction()) return;
    try {
      await api.post(`/tasks/${handoff.id}/handoff`, values);
      message.success("任务已交接，5 日内未重新开始将自动完成");
      setHandoff(null);
      handoffForm.resetFields();
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "交接失败");
    } finally {
      endTaskAction();
    }
  };
  const simpleAction = async (
    row: TaskRow,
    type: "accept" | "restart" | "complete" | "confirm",
  ) => {
    const labels = {
      accept: "任务已接收",
      restart: "任务已重新开始",
      complete: "已提交完成，等待发起人确认",
      confirm: "任务已验收",
    };
    if (!beginTaskAction()) return;
    try {
      await api.post(`/tasks/${row.id}/${type}`, { comment: labels[type] });
      message.success(labels[type]);
      setSelectedKeys([]);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "操作失败");
    } finally {
      endTaskAction();
    }
  };
  const requestTaskWithdrawal = (row: TaskRow) => {
    let reason = "";
    Modal.confirm({
      title: `撤回任务：${row.serial_no}`,
      content: <Input.TextArea rows={4} placeholder="请填写撤回原因" onChange={(event) => { reason = event.target.value; }} />,
      okText: "确认撤回",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: async () => {
        if (!reason.trim()) {
          message.warning("请填写撤回原因");
          throw new Error("撤回原因不能为空");
        }
        if (!beginTaskAction()) return;
        try {
          await api.post(`/tasks/${row.id}/withdraw`, { comment: reason.trim() });
          message.success("任务已撤回");
          setSelectedKeys([]);
          if (communication?.id === row.id) setCommunication(null);
          await load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || "撤回任务失败");
          throw error;
        } finally {
          endTaskAction();
        }
      },
    });
  };
  const requestTaskException = (row: TaskRow, action: "挂起" | "取消") => {
    let reason = "";
    Modal.confirm({
      title: `申请任务${action}：${row.serial_no}`,
      content: <Input.TextArea rows={4} placeholder={`请填写申请${action}的原因`} onChange={(event) => { reason = event.target.value; }} />,
      okText: "提交审批",
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.post(`/tasks/${row.id}/exception-request`, { action, reason });
          message.success(`任务${action}申请已提交`);
          await load();
        } catch (error: any) {
          message.error(error?.response?.data?.detail || `任务${action}申请失败`);
          throw error;
        }
      },
    });
  };
  const reviewTaskException = async (row: TaskRow, approved: boolean) => {
    try {
      await api.post(`/tasks/${row.id}/exception-review`, { approved, comment: approved ? "同意特殊处理申请" : "不同意特殊处理申请" });
      message.success(approved ? "任务特殊处理申请已通过" : "任务特殊处理申请已驳回");
      setSelectedKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "任务特殊处理审批失败");
    }
  };
  const openDialog = (row: TaskRow, action: DialogAction) => {
    setDialog({ row, action });
    dialogForm.resetFields();
    if (action === "resend")
      dialogForm.setFieldsValue({ recipient: row.owner });
  };
  const submitDialog = async () => {
    if (!dialog) return;
    const values = await dialogForm.validateFields();
    if (!beginTaskAction()) return;
    try {
      await api.post(
        `/tasks/${dialog.row.id}/${dialog.action}`,
        dialog.action === "resend"
          ? { recipient: values.recipient, comment: values.comment }
          : { comment: values.comment },
      );
      message.success(
        dialog.action === "reject"
          ? "任务已拒绝并反馈发起人"
          : "任务已重新派发",
      );
      setDialog(null);
      setSelectedKeys([]);
      load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "操作失败");
    } finally {
      endTaskAction();
    }
  };
  const openCommunication = async (row: TaskRow) => {
    setCommunication(row);
    commentForm.resetFields();
    setFeedbackFiles([]);
    setTaskMaterialFiles([]);
    if (isUnread && isTaskParticipant(row)) {
      try {
        await api.post(`/tasks/${row.id}/messages/read`);
        window.dispatchEvent(new Event("sunhold:notifications-updated"));
        setSelectedKeys((keys) => keys.filter((key) => key !== row.id));
        await load(query, statusTab, taskMeta.page, taskMeta.pageSize, taskSort);
      } catch (error: any) {
        message.error(error?.response?.data?.detail || "未读消息标记已读失败");
      }
    }
    await loadTaskFeedback(row);
  };
  const closeCommunication = () => {
    setCommunication(null);
    setFeedbackFiles([]);
    setTaskMaterialFiles([]);
  };
  const resolveLinkedCase = async (row: TaskRow) => {
    if (!row.case_no) {
      message.warning("当前任务未关联案件");
      return null;
    }
    try {
      const { data } = await api.get("/records", {
        params: { module: "case", keyword: row.case_no, page_size: 100 },
      });
      const record = (data.items as CaseRecord[]).find(
        (item) => item.serial_no === row.case_no,
      );
      if (!record) message.warning("未找到关联案件或当前账号无权查看");
      return record || null;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联案件加载失败");
      return null;
    }
  };
  const openCaseDetail = async (row: TaskRow) => {
    const record = await resolveLinkedCase(row);
    if (!record) return;
    rememberCaseDetailTarget({ id: record.id, serial_no: record.serial_no });
    onNavigate?.("case-company");
  };
  const openCaseContext = async (row: TaskRow, mode: "tasks" | "logs") => {
    setCaseContextLoading(true);
    try {
      const record = await resolveLinkedCase(row);
      if (!record) return;
      if (mode === "tasks") {
        const { data } = await api.get(`/cases/${record.id}/tasks`);
        setCaseTasks(data.items);
        setCaseHistory([]);
      } else {
        const { data } = await api.get(`/records/${record.id}/history`);
        setCaseHistory(data.items);
        setCaseTasks([]);
      }
      setCaseContext({ mode, record });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联案件信息加载失败");
    } finally {
      setCaseContextLoading(false);
    }
  };
  const addComment = async () => {
    if (!communication) return;
    if (!isTaskParticipant(communication)) {
      message.warning("只有任务参与人可以提交反馈");
      return;
    }
    const values = await commentForm.validateFields();
    if (!beginTaskAction()) return;
    try {
      const body = new FormData();
      body.append("comment", values.comment.trim());
      if (feedbackFiles.length && !appendSelectedUploadFiles(body, feedbackFiles)) {
        throw new Error("未读取到已选择的反馈附件");
      }
      const { data } = await api.post(`/tasks/${communication.id}/feedback`, body);
      const uploaded = (data.attachments || []) as TaskFeedbackAttachment[];
      message.success(uploaded.length ? `反馈和 ${uploaded.length} 个附件已一起保存` : "反馈已保存");
      commentForm.resetFields();
      setFeedbackFiles([]);
      await loadTaskFeedback(communication);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "沟通记录保存失败");
    } finally {
      endTaskAction();
    }
  };
  const downloadTaskAttachment = async (item: TaskFeedbackAttachment) => {
    try {
      const response = await api.get(`/attachments/${item.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = item.original_name;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "附件下载失败");
    }
  };
  const deleteTaskAttachment = (item: TaskFeedbackAttachment, categoryLabel: "任务反馈附件" | "任务资料附件") => {
    Modal.confirm({
      title: `删除${categoryLabel}`,
      content: `确定删除“${item.original_name}”吗？此操作不可恢复。`,
      okText: "删除",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await api.delete(`/attachments/${item.id}`);
          message.success(`${categoryLabel}已删除`);
          if (communication) await loadTaskFeedback(communication);
        } catch (error: any) {
          message.error(error?.response?.data?.detail || `删除${categoryLabel}失败`);
          throw error;
        }
      },
    });
  };
  const uploadTaskMaterials = async () => {
    if (!communication || !taskMaterialFiles.length) {
      message.warning("请先选择任务资料附件");
      return;
    }
    if (!beginTaskAction()) return;
    try {
      const body = new FormData();
      if (!appendSelectedUploadFiles(body, taskMaterialFiles)) {
        throw new Error("未读取到已选择的任务资料附件");
      }
      const { data } = await api.post(`/tasks/${communication.id}/materials`, body);
      message.success(`已上传 ${(data.attachments || []).length} 个任务资料附件`);
      setTaskMaterialFiles([]);
      await loadTaskFeedback(communication);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "任务资料附件上传失败");
    } finally {
      endTaskAction();
    }
  };
  const markHistoryUnread = async (item: HistoryItem) => {
    if (!communication || !beginTaskAction()) return;
    try {
      await api.post(`/tasks/${communication.id}/history/${item.id}/mark-unread`);
      window.dispatchEvent(new Event("sunhold:notifications-updated"));
      message.success("已标记为未读");
      setHistory((items) =>
        items.map((historyItem) =>
          historyItem.id === item.id ? { ...historyItem, unread: true } : historyItem,
        ),
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "标记未读失败");
    } finally {
      endTaskAction();
    }
  };
  const requireOne = (action: (row: TaskRow) => void) => {
    if (!selected) {
      message.warning(
        selectedRows.length > 1 ? "此操作只能选择一条任务" : "请先选择一条任务",
      );
      return;
    }
    action(selected);
  };
  const acceptSelectedTask = () => {
    if (!selected) {
      message.warning(selectedRows.length > 1 ? "接受任务只能选择一条任务" : "请先选择一条待接受任务");
      return;
    }
    const workflowStatus = selected.workflow_status || selected.status;
    if (!["待接收", "待处理"].includes(workflowStatus)) {
      message.warning("只有待接收或待处理的任务可以接受");
      return;
    }
    void simpleAction(selected, selected.handoff_auto_complete_at ? "restart" : "accept");
  };
  const markSelectedUnreadTasksRead = async () => {
    if (!selectedRows.length) {
      message.warning("请先勾选需要标记已读的任务");
      return;
    }
    if (!beginTaskAction()) return;
    try {
      const { data } = await api.post("/tasks/messages/batch-read", {
        task_ids: selectedRows.map((row) => row.id),
      });
      message.success(`已标记 ${data.updated} 条消息为已读`);
      setSelectedKeys([]);
      window.dispatchEvent(new Event("sunhold:notifications-updated"));
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量标记已读失败");
    } finally {
      endTaskAction();
    }
  };
  const taskBatchLabels: Record<TaskBatchLifecycleAction, string> = {
    accept: "批量接收任务",
    complete: "批量提交完成",
    confirm: "批量验收任务",
    handoff: "批量交接任务",
    withdraw: "批量撤回任务",
  };
  const openTaskBatchLifecycle = (action: TaskBatchLifecycleAction) => {
    if (!selectedRows.length) {
      message.warning("请先勾选需要处理的任务");
      return;
    }
    taskBatchForm.resetFields();
    setTaskBatchAction(action);
  };
  const submitTaskBatchLifecycle = async () => {
    if (!taskBatchAction || !selectedRows.length) return;
    const values = await taskBatchForm.validateFields();
    if (!beginTaskAction()) return;
    try {
      const { data } = await api.post("/tasks/batch-lifecycle", {
        task_ids: selectedRows.map((row) => row.id),
        action: taskBatchAction,
        recipient: values.recipient || "",
        comment: values.comment || "",
      });
      message.success(`${taskBatchLabels[taskBatchAction]}成功：${data.updated} 条`);
      setTaskBatchAction(null);
      setSelectedKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || `${taskBatchLabels[taskBatchAction]}失败`);
    } finally {
      endTaskAction();
    }
  };

  const standardColumns: any[] = [
    {
      title: "任务编号",
      dataIndex: "serial_no",
      width: 200,
      ellipsis: true,
      render: (value: string, row: TaskRow) => (
        <Button
          className="task-cell-link task-table-identifier"
          type="link"
          title={value || ""}
          onClick={() => openCommunication(row)}
        >
          {value}
        </Button>
      ),
    },
    {
      title: "案号编号",
      dataIndex: "case_no",
      width: 180,
      ellipsis: true,
      render: (value: string, row: TaskRow) =>
        value ? (
          <Button className="business-relation-link task-table-identifier" type="link" title={value} onClick={() => void openCaseDetail(row)}>
            {value}
          </Button>
        ) : "",
    },
    {
      title: "原告",
      dataIndex: "plaintiff",
      width: 160,
      ellipsis: true,
      render: (value: string) => value || "",
    },
    {
      title: "被告",
      dataIndex: "defendant",
      width: 160,
      ellipsis: true,
      render: (value: string) => value || "",
    },
    {
      title: "案件阶段",
      dataIndex: "case_stage",
      width: 105,
      render: (value: string) => value || "",
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      onCell: (row: TaskRow) => ({
        className: ["已完成", "待确认", "已验收"].includes(row.status)
          ? "task-status-cell task-status-cell-finished"
          : row.status === "已拒绝"
            ? "task-status-cell task-status-cell-rejected"
            : ["已停止", "已撤回"].includes(row.status)
              ? "task-status-cell task-status-cell-stopped"
              : "task-status-cell",
      }),
      render: (value: string) => {
        const createdStatusLabels: Record<string, string> = {
          已拒绝: "进行中(已拒绝)",
          已停止: "进行中(已停止)",
          已撤回: "进行中(已撤回)",
        };
        return <span>{isCreated ? createdStatusLabels[value] || value : value}</span>;
      },
    },
    {
      title: "优先级",
      dataIndex: "priority",
      width: 78,
      render: (value: string) => (value === "普通" ? "一般" : value || ""),
    },
    {
      title: "标题",
      dataIndex: "title",
      width: 220,
      ellipsis: true,
      onCell: () => ({ className: "task-title-cell" }),
    },
    {
      title: "发起时间",
      dataIndex: "created_at",
      width: 142,
      sorter: true,
      sortOrder: taskSort?.field === "created_at" ? taskSort.order : null,
      render: formatTaskDate,
    },
    {
      title: "截止时间",
      dataIndex: "deadline",
      width: 110,
      sorter: true,
      sortOrder: taskSort?.field === "deadline" ? taskSort.order : null,
      render: formatTaskDate,
    },
    {
      title: "剩余天数",
      dataIndex: "days_remaining",
      width: 82,
      align: "center",
      sorter: true,
      sortOrder: taskSort?.field === "days_remaining" ? taskSort.order : null,
      render: (value: number | null) => (value == null ? "" : `${value}/天`),
    },
    {
      title: isCreated && statusTab === "accepted" ? "验收日期" : "最后更新时间",
      dataIndex: "updated_at",
      width: 142,
      sorter: true,
      sortOrder: taskSort?.field === "updated_at" ? taskSort.order : null,
      render: (value: string, row: TaskRow) =>
        formatTaskDateTime(isCreated && statusTab === "accepted" ? row.verified_at : value),
    },
    {
      title: "发起人",
      dataIndex: "initiator",
      width: 95,
      render: (value: string) => value || "",
    },
    {
      title: "负责人",
      dataIndex: "owner",
      width: 95,
      render: (value: string) => value || "",
    },
  ];
  const unreadColumns: any[] = [
    { title: "任务编号", dataIndex: "serial_no", width: 200, ellipsis: true, render: (value: string, row: TaskRow) => { const label = `(${row.source || "人工"})${String(value || "").replace(/^\([^)]*\)/, "")}`; return <Button className="task-cell-link task-table-identifier" type="link" title={label} onClick={() => openCommunication(row)}>{label}</Button> } },
    { title: "关联案号", dataIndex: "case_no", width: 180, ellipsis: true, render: (value: string, row: TaskRow) => value ? <Button className="business-relation-link task-table-identifier" type="link" title={value} onClick={() => void openCaseDetail(row)}>{value}</Button> : "—" },
    { title: "未读内容", dataIndex: "latest_unread_message", width: 360, ellipsis: true, render: (value: string) => value || "—" },
    { title: "发送人", dataIndex: "latest_unread_sender", width: 140, ellipsis: true, render: (value: string) => value || "—" },
    { title: "发送时间", dataIndex: "latest_unread_at", width: 165, sorter: true, sortOrder: taskSort?.field === "updated_at" ? taskSort.order : null, render: (value: string) => value ? formatTaskDateTime(value) : "—" },
    { title: "任务状态", dataIndex: "status", width: 105, ellipsis: true, render: (value: string) => value || "—" },
    { title: "负责人", dataIndex: "owner", width: 120, ellipsis: true, render: (value: string) => value || "—" },
  ];
  const columns = isUnread ? unreadColumns : standardColumns;
  const openCreateTask = () => {
    createForm.setFieldsValue({ owner: profile.username || "admin", priority: "普通", source: "人工", collaborators: [], deadline: dayjs().add(7, "day") });
    setCreateOpen(true);
  };
  useEffect(() => {
    const raw = window.sessionStorage.getItem("sunhold:task-create-context");
    if (!raw) return;
    try {
      const context = JSON.parse(raw) as { case_no?: string; customer?: string; title?: string };
      if (!context.case_no) return;
      createForm.setFieldsValue({
        title: context.title || `案件任务—${context.case_no}`,
        owner: profile.username || "admin",
        priority: "普通",
        source: "案件任务",
        collaborators: [],
        deadline: dayjs().add(7, "day"),
        case_no: context.case_no,
        customer: context.customer || "",
      });
      setCreateOpen(true);
    } catch {
      // A malformed transient workspace context must not prevent task access.
    } finally {
      window.sessionStorage.removeItem("sunhold:task-create-context");
    }
  }, [createForm, initialView, profile.username]);
  const feeLabels = { lawFee: "新增律所费用", platformFee: "新增平台费用", internalFee: "新增内部费用" } as const;
  const documentLabels = { authorization: "授权委托书", lawFirmLetter: "律所函", identity: "身份证明", settlement: "结算提成表" } as const;
  const openFee = (key: FeeAction, subtype: FeeSubtype) => requireOne((row) => {
    feeForm.resetFields();
    feeForm.setFieldsValue({ amount: undefined, expense_date: dayjs(), applicant: profile.display_name || profile.username || row.owner, description: "" });
    setFeeAction(key);
    setFeeSubtype(subtype);
  });
  const submitFee = async () => {
    if (!feeAction || !feeSubtype || !selected) return;
    const values = await feeForm.validateFields();
    const label = feeLabels[feeAction];
    if (!beginTaskAction()) return;
    let createdFeeId: number | null = null;
    try {
      const expenseScope = feeAction === "lawFee" ? "律所" : feeAction === "platformFee" ? "平台" : "内部";
      const feeType = feeSubtype === "官费" ? "官方费用" : feeSubtype === "代理费" ? "代理费" : feeAction === "internalFee" ? "内部费用" : "其他费用";
      const { data: createdFee } = await api.post("/finance/fees", {
        title: `${label}-${feeSubtype}-${selected.case_no || selected.serial_no}`,
        customer: selected.customer,
        amount: values.amount,
        fee_type: feeType,
        expense_scope: expenseScope,
        expense_subtype: feeSubtype,
        case_no: selected.case_no || "",
        handler: profile.username || selected.owner,
        description: values.description || "",
      });
      createdFeeId = createdFee.id;
      await api.post(`/finance/fees/${createdFee.id}/submit`, {
        comment: `来源任务 ${selected.serial_no}；申请人 ${values.applicant}；费用日期 ${formatRequiredDate(values.expense_date, "费用日期")}`,
      });
      message.success(`${label}已登记并进入待审批`);
      setFeeAction(null);
      setFeeSubtype(null);
    } catch (error: any) {
      const detail = error?.response?.data?.detail || "费用登记失败";
      message.error(createdFeeId ? `${detail}；费用草稿已保留，可到费用页继续处理` : detail);
    } finally { endTaskAction(); }
  };
  const caseBatchLabels: Record<CaseBatchAction, string> = {
    hearing_lawyer: "修改开庭律师",
    handling_lawyers: "修改经办律师",
    assistant: "修改律师助理",
    case_stage: "修改案件阶段",
  };
  const selectedCaseNos = Array.from(new Set(selectedRows.map((row) => row.case_no.trim()).filter(Boolean)));
  const openCaseBatch = (action: CaseBatchAction) => {
    if (!selectedCaseNos.length) return message.warning("请选择案件.");
    batchForm.resetFields();
    setCaseBatchAction(action);
  };
  const submitCaseBatch = async () => {
    if (!caseBatchAction) return;
    const values = await batchForm.validateFields();
    if (!beginTaskAction()) return;
    try {
      await api.post("/cases/batch-update", {
        case_nos: selectedCaseNos,
        [caseBatchAction]: values[caseBatchAction],
        comment: values.comment || "",
      });
      message.success(`已批量修改 ${selectedCaseNos.length} 个案件`);
      setCaseBatchAction(null);
      setSelectedKeys([]);
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "案件批量修改失败");
    } finally { endTaskAction(); }
  };
  const openDocument = (key: keyof typeof documentLabels) => requireOne(() => {
    documentForm.resetFields();
    documentForm.setFieldsValue({ title: `${documentLabels[key]}-${selected?.case_no || selected?.serial_no}`, instruction: "请依据案件已有资料生成，缺失信息标记为待补充。" });
    setDocumentAction(key);
  });
  const submitDocument = async () => {
    if (!documentAction || !selected) return;
    const values = await documentForm.validateFields();
    if (!beginTaskAction()) return;
    try {
      const templateName = documentLabels[documentAction];
      const templateResponse = await api.get("/templates");
      let template = templateResponse.data.items.find((item: any) => item.is_active !== false && String(item.name).includes(templateName));
      if (!template) {
        const fieldMap: Record<string, string[]> = {
          authorization: ["委托人", "受托人", "委托事项", "委托权限", "委托期限"],
          lawFirmLetter: ["收函单位", "案件基本信息", "律师意见", "联系方式"],
          identity: ["主体信息", "法定代表人或负责人", "身份证明事项", "签章"],
          settlement: ["案件信息", "费用明细", "提成计算", "复核意见"],
        };
        const created = await api.post("/templates", { name: templateName, category: documentAction === "settlement" ? "内部表单" : "诉讼文书", version: "1.0", description: "由任务中心生成文书使用", fields: fieldMap[documentAction] });
        template = created.data;
      }
      const caseResponse = await api.get("/records", { params: { module: "case", keyword: selected.case_no, page_size: 100 } });
      const caseRecord = caseResponse.data.items.find((item: any) => item.serial_no === selected.case_no);
      if (!caseRecord) throw new Error("当前任务未关联可访问的案件，无法生成文书");
      const generated = await api.post("/agent/documents", { template_id: template.id, record_id: caseRecord.id, title: values.title, instruction: values.instruction || "" });
      const download = await api.get(`/agent/documents/${generated.data.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(download.data), link = document.createElement("a");
      link.href = url; link.download = `${values.title}.docx`; link.click(); URL.revokeObjectURL(url);
      message.success(`${templateName}已生成并下载，生成记录已保留`);
      setDocumentAction(null);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.message || "文书生成失败");
    } finally { endTaskAction(); }
  };
  const exportTaskPrintTable = async () => {
    const source = selectedRows.length ? selectedRows : filteredTasks;
    if (!source.length) {
      message.warning("当前没有可导出的任务");
      return;
    }
    if (!beginTaskAction()) return;
    try {
      const response = await api.get("/tasks/print-export", {
        params: { ids: source.map((row) => row.id).join(",") },
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "案件任务打印表.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "导出失败");
    } finally {
      endTaskAction();
    }
  };
  const moreAction = (key: string) => {
    const [feeKey, subtype] = key.split(":") as [FeeAction, FeeSubtype];
    if (["lawFee", "platformFee"].includes(feeKey) && subtype) return openFee(feeKey, subtype);
    if (key === "internalFee") return openFee("internalFee", "内部费用");
    if (key.startsWith("caseBatch:")) return openCaseBatch(key.slice("caseBatch:".length) as CaseBatchAction);
    if (key === "authorization" || key === "lawFirmLetter" || key === "identity" || key === "settlement") return openDocument(key);
    if (key === "caseTasks") return requireOne((row) => openCaseContext(row, "tasks"));
    if (key === "logs") return requireOne((row) => openCaseContext(row, "logs"));
    if (key === "export") return void exportTaskPrintTable();
  };

  return (
    <>
      <Card
        className="task-original-panel task-original-standard"
        title="任务列表"
      >
        {!isUnread && <div className="task-status-tabs">
          {tabs.map((item) => (
            <button
              key={item.key}
              type="button"
              className={statusTab === item.key ? "active" : ""}
              onClick={() => {
                setStatusTab(item.key);
                setSelectedKeys([]);
                void load(query, item.key, 1, taskMeta.pageSize);
              }}
            >
              {item.label}({counts[item.key] || 0})
            </button>
          ))}
        </div>}

        <Form<TaskQuery>
          form={queryForm}
          className="task-query"
          colon
          onFinish={(values) => {
            setQuery(values);
            setSelectedKeys([]);
            void load(values, statusTab, 1, taskMeta.pageSize);
          }}
        >
          <Form.Item label="优先级" name="priority">
            <Select
              allowClear
              placeholder="请选择"
              options={["一般", "重要"].map((value) => ({
                value,
                label: value,
              }))}
            />
          </Form.Item>
          <Form.Item label="任务编号" name="serial_no">
            <Input />
          </Form.Item>
          <Form.Item label="任务标题" name="title">
            <Input />
          </Form.Item>
          <Form.Item label="任务内容" name="description">
            <Input />
          </Form.Item>
          <Form.Item label="发起人" name="initiator">
            <Input />
          </Form.Item>
          <Form.Item label="案件编号" name="case_no">
            <Input />
          </Form.Item>
          <Form.Item label="任务类型" name="source">
            <Select
              allowClear
              placeholder="请选择"
              options={["自动", "人工"].map((value) => ({
                value,
                label: value,
              }))}
            />
          </Form.Item>
          <Form.Item label="发起日期" name="created_range">
            <DatePicker.RangePicker />
          </Form.Item>
          <Form.Item label="负责人" name="owner">
            <Input />
          </Form.Item>
          <Form.Item label="原告" name="plaintiff">
            <Input />
          </Form.Item>
          <Form.Item label="被告" name="defendant">
            <Input />
          </Form.Item>
          <Form.Item label="截止日期" name="deadline_range">
            <DatePicker.RangePicker />
          </Form.Item>
          <div className="task-query-submit">
            <Button type="primary" htmlType="submit">
              查询
            </Button>
            <Button
              htmlType="button"
              onClick={() => {
                queryForm.resetFields();
                setQuery({});
                setTaskSort(null);
                setSelectedKeys([]);
                void load({}, statusTab, 1, taskMeta.pageSize, null);
              }}
            >
              重置
            </Button>
          </div>
        </Form>
        <Table<TaskRow>
          className={`task-original-table${isUnread ? " task-unread-table" : ""}`}
          rowKey="id"
          loading={loading}
          size="small"
          bordered
          columns={columns}
          dataSource={filteredTasks}
          tableLayout="fixed"
          scroll={{ x: isUnread ? 1270 : 1900 }}
          rowSelection={
            {
              selectedRowKeys: selectedKeys,
              onChange: setSelectedKeys,
            }
          }
          locale={{ emptyText: "没有查询到符合条件的记录 。" }}
          pagination={
            hideTaskFooter
              ? false
              : {
                  current: taskMeta.page,
                  total: taskMeta.total,
                  pageSize: taskMeta.pageSize,
                  pageSizeOptions: [10, 15, 20, 50, 100, 200],
                  showTotal: (total) => `共有${total}条，每页显示`,
                  showSizeChanger: true,
                }
          }
          onChange={(pagination, _filters, sorter, extra) => {
            if (extra.action !== "paginate" && extra.action !== "sort") return;
            const activeSorter = Array.isArray(sorter) ? sorter[0] : sorter;
            const allowedFields = ["created_at", "deadline", "days_remaining", "updated_at"];
            const nextSort =
              activeSorter?.order && allowedFields.includes(String(activeSorter.field))
                ? {
                    field: String(activeSorter.field) as NonNullable<TaskSort>["field"],
                    order: activeSorter.order as NonNullable<TaskSort>["order"],
                  }
                : null;
            setTaskSort(nextSort);
            setSelectedKeys([]);
            void load(
              query,
              statusTab,
              extra.action === "sort" ? 1 : pagination.current || 1,
              pagination.pageSize || taskMeta.pageSize,
              nextSort,
            );
          }}
        />

        {!hideTaskFooter && (
          <div className="task-bottom-actions">
            <Space size={5} wrap>
              {isUnread && (
                <Button loading={actionSubmitting} onClick={() => void markSelectedUnreadTasksRead()}>标记已读</Button>
              )}
              {canManageInitiatedTask && <Button onClick={openCreateTask}>新增任务</Button>}
              {canWithdrawTask(selected) && <Button danger onClick={() => selected && requestTaskWithdrawal(selected)}>撤回任务</Button>}
              {(canManageInitiatedTask || canManageCompanyCreatedTask) && selected?.status === "已拒绝" && (
                <Button onClick={() => openDialog(selected, "resend")}>重新派发</Button>
              )}
              {(canManageInitiatedTask || canManageCompanyCreatedTask) && ["已完成", "待确认"].includes(selected?.workflow_status || selected?.status || "") && (
                <>
                  <Button onClick={() => selected && void simpleAction(selected, "confirm")}>确认完成</Button>
                  {!selected?.auto_completed && (
                    <Button onClick={() => selected && void simpleAction(selected, "restart")}>退回重启</Button>
                  )}
                </>
              )}
              {canManageAcceptedTask && <Button onClick={acceptSelectedTask}>接受任务</Button>}
              {canManageAcceptedTask && ["待接收", "待处理"].includes(selected?.workflow_status || selected?.status || "") && (
                  <Button onClick={() => selected && openDialog(selected, "reject")}>拒绝任务</Button>
              )}
              {canManageAcceptedTask && (selected?.workflow_status || selected?.status) === "处理中" && (
                <>
                  <Button onClick={() => selected && void simpleAction(selected, "complete")}>完成任务</Button>
                  <Button onClick={() => selected && requestTaskException(selected, "挂起")}>申请挂起</Button>
                  <Button danger onClick={() => selected && requestTaskException(selected, "取消")}>申请取消</Button>
                  <Button
                    onClick={() => {
                      setHandoff(selected);
                      handoffForm.setFieldsValue({ recipient: "", comment: "" });
                    }}
                  >
                    转交任务
                  </Button>
                </>
              )}
              {selectedRows.length > 1 && (canManageAcceptedTask || canManageInitiatedTask || canManageCompanyCreatedTask) && (
                <Dropdown
                  trigger={["click"]}
                  menu={{
                    items: [
                      ...(canManageAcceptedTask ? [
                        { key: "accept", label: "批量接收任务" },
                        { key: "complete", label: "批量提交完成" },
                        { key: "handoff", label: "批量交接任务" },
                      ] : []),
                      ...((canManageInitiatedTask || canManageCompanyCreatedTask) ? [
                        { key: "confirm", label: "批量验收任务" },
                        { key: "withdraw", label: "批量撤回任务", danger: true },
                      ] : []),
                    ],
                    onClick: ({ key }) => openTaskBatchLifecycle(key as TaskBatchLifecycleAction),
                  }}
                >
                  <Button>批量任务流转</Button>
                </Dropdown>
              )}
              {(canManageAcceptedTask || canManageCompanyCreatedTask) && selected?.workflow_status === "已停止" && selected?.exception_request?.action === "挂起" && <Button onClick={() => void simpleAction(selected, "restart")}>恢复挂起任务</Button>}
              {selected?.exception_request?.status === "待审批" && canReviewTaskException(selected) && <><Button onClick={() => void reviewTaskException(selected, true)}>通过特殊处理</Button><Button danger onClick={() => void reviewTaskException(selected, false)}>驳回特殊处理</Button></>}
              {selected?.performance_impact?.overdue && <Tag color="red">超期 {selected.performance_impact.overdue_days} 天，绩效影响 {selected.performance_impact.penalty_points} 分</Tag>}
              {canManageCompanyCreatedTask && (selected?.workflow_status || selected?.status) === "处理中" && (
                <>
                  <Button
                    onClick={() =>
                      requireOne((row) => void simpleAction(row, "complete"))
                    }
                  >
                    完成任务
                  </Button>
                  <Button
                    onClick={() =>
                      requireOne((row) => {
                        setHandoff(row);
                        handoffForm.setFieldsValue({ recipient: "", comment: "" });
                      })
                    }
                  >
                    转交任务
                  </Button>
                </>
              )}
              <Dropdown
                trigger={["click"]}
                menu={{
                  items: [
                    {
                      key: "lawFee",
                      label: "新增律所费用",
                      children: ["官费", "第三方费用", "代理费", "其他费用"].map((subtype) => ({
                        key: `lawFee:${subtype}`,
                        label: subtype,
                      })),
                    },
                    {
                      key: "platformFee",
                      label: "新增平台费用",
                      children: ["官费", "第三方费用", "代理费", "其他费用"].map((subtype) => ({
                        key: `platformFee:${subtype}`,
                        label: subtype,
                      })),
                    },
                    { key: "internalFee", label: "新增内部费用" },
                    ...(["admin", "manager"].includes(profile.role)
                      ? [{
                          key: "batch",
                          label: "批量修改",
                          children: (Object.entries(caseBatchLabels) as [CaseBatchAction, string][]).map(([action, label]) => ({
                            key: `caseBatch:${action}`,
                            label,
                          })),
                        }]
                      : []),
                    { key: "authorization", label: "生成授权委托书" },
                    { key: "lawFirmLetter", label: "生成律所函" },
                    { key: "identity", label: "生成身份证明" },
                    { key: "settlement", label: "生成结算提成表" },
                    { key: "caseTasks", label: "案件任务" },
                    { key: "logs", label: "案件日志" },
                    { key: "export", label: "导出案件打印表" },
                  ],
                  onClick: ({ key }) => moreAction(key),
                }}
              >
                <Button>更多操作</Button>
              </Dropdown>
            </Space>
          </div>
        )}
      </Card>

      <Modal
        open={Boolean(feeAction)}
        title={feeAction ? `${feeLabels[feeAction]}${feeSubtype ? ` - ${feeSubtype}` : ""}` : "新增费用"}
        okText="保存并提交审批"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={submitFee}
        onCancel={() => { setFeeAction(null); setFeeSubtype(null); }}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          message={<Space size={4}>关联任务：{selected ? <Button className="business-relation-link" type="link" onClick={() => void openCommunication(selected)}>{selected.serial_no}</Button> : "-"}；关联案件：{selected?.case_no ? <Button className="business-relation-link" type="link" onClick={() => void openCaseDetail(selected)}>{selected.case_no}</Button> : "-"}</Space>}
          style={{ marginBottom: 16 }}
        />
        <Form form={feeForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="费用金额" name="amount" rules={[{ required: true, message: "请输入费用金额" }]}>
              <InputNumber min={0.01} precision={2} style={{ width: "100%" }} addonAfter="元" />
            </Form.Item>
            <Form.Item label="费用日期" name="expense_date" rules={[{ required: true }]}>
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="申请人" name="applicant" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="费用说明" name="description" rules={[{ required: true, message: "请填写费用说明" }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(caseBatchAction)}
        title={`${caseBatchAction ? caseBatchLabels[caseBatchAction] : "批量修改"}（已选 ${selectedCaseNos.length} 个案件）`}
        okText="确认修改"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={submitCaseBatch}
        onCancel={() => setCaseBatchAction(null)}
        destroyOnHidden
      >
        <Alert type="warning" showIcon message={`将同时修改案件：${selectedCaseNos.join("、")}`} style={{ marginBottom: 16 }} />
        <Form form={batchForm} layout="vertical">
          {caseBatchAction === "hearing_lawyer" && <Form.Item label="开庭律师" name="hearing_lawyer" rules={[{ required: true, message: "请输入开庭律师" }]}><Input /></Form.Item>}
          {caseBatchAction === "handling_lawyers" && <Form.Item label="经办律师" name="handling_lawyers" rules={[{ required: true, message: "请输入经办律师" }]}><Select mode="tags" tokenSeparators={[",", "，"]} /></Form.Item>}
          {caseBatchAction === "assistant" && <Form.Item label="律师助理" name="assistant" rules={[{ required: true, message: "请输入律师助理" }]}><Input /></Form.Item>}
          {caseBatchAction === "case_stage" && <Form.Item label="案件阶段" name="case_stage" rules={[{ required: true, message: "请输入案件阶段" }]}><Input /></Form.Item>}
          <Form.Item label="修改说明" name="comment"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(documentAction)}
        title={documentAction ? `生成${documentLabels[documentAction]}` : "生成文书"}
        okText="生成并下载"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={submitDocument}
        onCancel={() => setDocumentAction(null)}
        destroyOnHidden
      >
        <Alert type="info" showIcon message="系统将使用关联案件资料和对应模板生成 Word 文书；Dify 未配置时仍会生成可编辑的字段提纲。" style={{ marginBottom: 16 }} />
        <Form form={documentForm} layout="vertical">
          <Form.Item label="文书标题" name="title" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="生成要求" name="instruction"><Input.TextArea rows={4} /></Form.Item>
        </Form>
      </Modal>
      <Modal
        open={createOpen}
        title="新增任务"
        okText="发起任务"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={createTask}
        onCancel={() => setCreateOpen(false)}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item label="任务内容" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="负责人" name="owner" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item
              label="截止日期"
              name="deadline"
              rules={[{ required: true }]}
            >
              <DatePicker
                style={{ width: "100%" }}
                disabledDate={(date) =>
                  date.isBefore(dayjs(), "day") ||
                  date.isAfter(dayjs().add(30, "day"), "day")
                }
              />
            </Form.Item>
            <Form.Item label="优先级" name="priority">
              <Select
                options={["普通", "重要", "紧急"].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            <Form.Item label="任务来源" name="source">
              <Select
                options={[
                  "自动",
                  "人工",
                  "案件任务",
                  "合同任务",
                  "客户任务",
                  "公证书交接任务",
                ].map((value) => ({ value, label: value }))}
              />
            </Form.Item>
          </div>
          <Form.Item label="协作人" name="collaborators">
            <Select
              mode="tags"
              tokenSeparators={[",", "，"]}
              placeholder="输入账号后回车，可添加多人"
            />
          </Form.Item>
          <Form.Item label="关联案号" name="case_no">
            <Input />
          </Form.Item>
          <Form.Item label="客户" name="customer">
            <Input />
          </Form.Item>
          <Form.Item label="任务说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item label="任务资料附件（可多选，单个不超过 20MB）">
            <Upload
              multiple
              fileList={createMaterialFiles}
              beforeUpload={(file) => {
                setCreateMaterialFiles((items) => [...items, file]);
                return false;
              }}
              onRemove={(file) => setCreateMaterialFiles((items) => items.filter((item) => item.uid !== file.uid))}
            >
              <Button icon={<UploadOutlined />}>选择任务资料附件</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(handoff)}
        title={`任务转交：${handoff?.serial_no || ""}`}
        okText="确认转交"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={submitHandoff}
        onCancel={() => setHandoff(null)}
      >
        <Alert
          type="warning"
          showIcon
          message="转交后 5 天内接收人未开始，系统按交接规则自动完成。"
        />
        <Form form={handoffForm} layout="vertical" style={{ marginTop: 18 }}>
          <Form.Item
            label="接收人"
            name="recipient"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="转交说明" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(dialog)}
        title={dialog?.action === "reject" ? "拒绝任务" : "重新派发任务"}
        okText="确认"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={submitDialog}
        onCancel={() => setDialog(null)}
      >
        <Form form={dialogForm} layout="vertical">
          {dialog?.action === "resend" && (
            <Form.Item
              label="新负责人"
              name="recipient"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
          )}
          <Form.Item
            label={dialog?.action === "reject" ? "拒绝理由" : "派发说明"}
            name="comment"
            rules={[{ required: true }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(taskBatchAction)}
        title={`${taskBatchAction ? taskBatchLabels[taskBatchAction] : "批量任务流转"}（已选 ${selectedRows.length} 条）`}
        okText="确认执行"
        cancelText="取消"
        confirmLoading={actionSubmitting}
        onOk={() => void submitTaskBatchLifecycle()}
        onCancel={() => setTaskBatchAction(null)}
        destroyOnHidden
      >
        <Alert
          type={taskBatchAction === "withdraw" ? "warning" : "info"}
          showIcon
          message={taskBatchAction === "handoff"
            ? "所有任务将转交给同一接收人；交接后 5 天内未重新开始会自动完成。"
                : taskBatchAction === "withdraw"
                  ? "仅任务发起人或管理员可撤回；任一任务不符合条件时整批不会提交。"
                  : taskBatchAction === "confirm"
                    ? "仅任务发起人或管理员可验收待确认任务；任一任务不符合条件时整批不会提交。"
                  : "系统将逐条核验负责人、状态和权限；任一任务不符合条件时整批不会提交。"}
          style={{ marginBottom: 16 }}
        />
        <Form form={taskBatchForm} layout="vertical">
          {taskBatchAction === "handoff" && (
            <Form.Item label="接收人" name="recipient" rules={[{ required: true, message: "请输入接收人" }]}>
              <Input />
            </Form.Item>
          )}
          <Form.Item
            label={taskBatchAction === "withdraw" ? "撤回原因" : "操作说明"}
            name="comment"
            rules={taskBatchAction === "withdraw" ? [{ required: true, message: "请填写撤回原因" }] : []}
          >
            <Input.TextArea rows={4} placeholder={taskBatchAction === "withdraw" ? "请填写撤回原因" : "可选，写入每条任务的流转记录"} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        width={900}
        open={Boolean(caseContext)}
        title={`${caseContext?.mode === "tasks" ? "案件任务" : "案件日志"}：${caseContext?.record.serial_no || ""}`}
        footer={<Button onClick={() => setCaseContext(null)}>关闭</Button>}
        onCancel={() => setCaseContext(null)}
        loading={caseContextLoading}
      >
        {caseContext?.mode === "tasks" ? (
          <Table<TaskRow>
            className="task-case-context-table"
            rowKey="id"
            size="small"
            pagination={false}
            tableLayout="fixed"
            scroll={{ x: 820 }}
            dataSource={caseTasks}
            locale={{ emptyText: "当前案件暂无任务" }}
            columns={[
              { title: "任务编号", dataIndex: "serial_no", width: 200, ellipsis: true },
              { title: "任务名称", dataIndex: "title", width: 280, ellipsis: true },
              { title: "负责人", dataIndex: "owner", width: 100 },
              { title: "截止日期", dataIndex: "deadline", width: 115 },
              { title: "状态", dataIndex: "status", width: 95, render: (value: string) => <Tag color={statusColors[value] || "blue"}>{value}</Tag> },
            ]}
          />
        ) : (
          <List
            className="task-history"
            dataSource={caseHistory}
            locale={{ emptyText: "当前案件暂无流转日志" }}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={<Space><Tag>{item.action}</Tag><b>{item.operator}</b><span>{new Date(item.created_at).toLocaleString("zh-CN")}</span></Space>}
                  description={<><div>{item.from_status && item.to_status ? `${item.from_status} → ${item.to_status}` : ""}</div><p>{item.comment || "-"}</p></>}
                />
              </List.Item>
            )}
          />
        )}
      </Modal>
      <Modal
        width={760}
        open={Boolean(communication)}
        title="案件任务"
        footer={<Button onClick={closeCommunication}>关闭</Button>}
        onCancel={closeCommunication}
      >
        <div className="task-detail-flow" aria-label="任务流程">
          {[
            "任务已分派",
            "任务处理中",
            "任务完成",
            "任务已验收",
          ].map((label, index) => {
            const flowIndex: Record<string, number> = {
              待接收: 0,
              待处理: 0,
              已拒绝: 0,
              已停止: 0,
              已撤回: 0,
              处理中: 1,
              已逾期: 1,
              待确认: 2,
              已完成: 2,
              已验收: 3,
            };
            const statusIndex = flowIndex[
              communication?.workflow_status || communication?.status || ""
            ] ?? 0;
            return (
              <span key={label} className={index <= statusIndex ? "active" : ""}>
                {label}
              </span>
            );
          })}
        </div>
        <div className="task-detail-meta">
          <span><b>任务标题：</b>{communication?.title || "-"}</span>
          <span><b>任务编号：</b>{communication?.serial_no?.replace(/^\([^)]*\)/, "") || "-"}</span>
          <span><b>当前负责人：</b>{communication?.owner || "-"}</span>
          <span><b>发布人：</b>{communication?.initiator || "-"}</span>
          <span><b>关联案号：</b>{communication?.case_no ? <Button className="business-relation-link" type="link" onClick={() => void openCaseDetail(communication)}>{communication.case_no}</Button> : "-"}</span>
          <span><b>截止日期：</b>{communication?.deadline || "-"}</span>
          <span><b>状态：</b><Tag color={statusColors[communication?.status || ""] || "blue"}>{communication?.status || "-"}</Tag></span>
          <span><b>当前协作人：</b>{communication?.collaborators?.join(",") || "-"}</span>
        </div>
        {communication && canWithdrawTask(communication) && (
          <div className="task-detail-actions">
            <Button danger onClick={() => requestTaskWithdrawal(communication)}>撤回任务</Button>
          </div>
        )}
        {communication && isTaskParticipant(communication) ? <>
          <div className="task-detail-section-title">沟通记录</div>
          <List
            className="task-history"
            dataSource={[...history].reverse()}
            locale={{ emptyText: "暂无沟通或流转记录" }}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button
                    key="mark-unread"
                    type="link"
                    size="small"
                    disabled={actionSubmitting || item.unread}
                    onClick={() => void markHistoryUnread(item)}
                  >
                    {item.unread ? "已标记未读" : "标记未读"}
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color={item.action === "任务沟通" ? "blue" : "default"}>{item.action}</Tag>
                      <b>{item.operator}</b>
                      <span>{new Date(item.created_at).toLocaleString("zh-CN")}</span>
                    </Space>
                  }
                  description={<><div>{item.from_status && item.to_status && `${item.from_status} → ${item.to_status}`}</div><p>{item.comment || "-"}</p></>}
                />
              </List.Item>
            )}
          />
          <div className="task-detail-section-title">任务资料附件</div>
          <Table
            size="small"
            rowKey="id"
            pagination={false}
            locale={{ emptyText: "暂无任务资料附件" }}
            dataSource={taskMaterialAttachments}
            columns={[
              { title: "文件名", dataIndex: "original_name", ellipsis: true },
              { title: "上传人", dataIndex: "uploader", width: 110 },
              { title: "上传时间", dataIndex: "created_at", width: 168, render: (value: string) => formatTaskDateTime(value) },
              {
                title: "操作",
                width: 150,
                render: (_: unknown, item: TaskFeedbackAttachment) => (
                  <Space size={0}>
                    <Button type="link" icon={<DownloadOutlined />} onClick={() => void downloadTaskAttachment(item)}>下载</Button>
                    {(profile.role === "admin" || item.uploader === profile.username) && (
                      <Button danger type="link" icon={<DeleteOutlined />} onClick={() => deleteTaskAttachment(item, "任务资料附件")}>删除</Button>
                    )}
                  </Space>
                ),
              },
            ]}
          />
          <Upload
            multiple
            fileList={taskMaterialFiles}
            beforeUpload={(file) => {
              setTaskMaterialFiles((items) => [...items, file]);
              return false;
            }}
            onRemove={(file) => setTaskMaterialFiles((items) => items.filter((item) => item.uid !== file.uid))}
            style={{ marginTop: 12 }}
          >
            <Button icon={<UploadOutlined />}>选择任务资料附件</Button>
          </Upload>
          <Button type="primary" loading={actionSubmitting} disabled={!taskMaterialFiles.length} onClick={() => void uploadTaskMaterials()} style={{ marginLeft: 8 }}>
            上传任务资料
          </Button>
          <div className="task-detail-section-title">任务反馈附件</div>
          <Table
            size="small"
            rowKey="id"
            pagination={false}
            locale={{ emptyText: "暂无任务反馈附件" }}
            dataSource={feedbackAttachments}
            columns={[
              { title: "文件名", dataIndex: "original_name", ellipsis: true },
              { title: "上传人", dataIndex: "uploader", width: 110 },
              { title: "上传时间", dataIndex: "created_at", width: 168, render: (value: string) => formatTaskDateTime(value) },
              {
                title: "操作",
                width: 150,
                render: (_: unknown, item: TaskFeedbackAttachment) => (
                  <Space size={0}>
                    <Button type="link" icon={<DownloadOutlined />} onClick={() => void downloadTaskAttachment(item)}>下载</Button>
                    {(profile.role === "admin" || item.uploader === profile.username) && (
                      <Button danger type="link" icon={<DeleteOutlined />} onClick={() => deleteTaskAttachment(item, "任务反馈附件")}>删除</Button>
                    )}
                  </Space>
                ),
              },
            ]}
          />
          <Form form={commentForm} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item label="反馈内容" name="comment" rules={[{ required: true, message: "请输入反馈内容" }]}>
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item label="反馈附件（可多选，单个不超过 20MB）">
              <Upload
                multiple
                fileList={feedbackFiles}
                beforeUpload={(file) => {
                  setFeedbackFiles((items) => [...items, file]);
                  return false;
                }}
                onRemove={(file) => setFeedbackFiles((items) => items.filter((item) => item.uid !== file.uid))}
              >
                <Button icon={<UploadOutlined />}>选择反馈附件</Button>
              </Upload>
            </Form.Item>
            <Button type="primary" icon={<CommentOutlined />} loading={actionSubmitting} onClick={addComment}>提交反馈</Button>
          </Form>
        </> : <Alert type="info" showIcon message="当前任务仅供查看" description="只有发起人、负责人、协作人和管理员可以查看沟通记录、提交反馈或标记未读。" />}
      </Modal>
    </>
  );
}

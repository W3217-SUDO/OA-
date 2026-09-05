import { useEffect, useMemo, useRef, useState } from "react";
import type { Key } from "react";
import { Button, Form, message, Modal, Input, Space } from "antd";
import type { UploadFile } from "antd";
import dayjs, { Dayjs } from "dayjs";
import { api } from "../api";
import { rememberCaseDetailTarget } from "../caseDetailNavigation";
import { consumeTaskDetailTarget } from "../taskDetailNavigation";
import { formatRequiredDate } from "../formSafety";
import { getCaseTaskCreateDefaults } from "../taskCaseCreateDefaults.mjs";
import "../task-center.css";

import type {
  TaskRow,
  DirectoryUser,
  Summary,
  HistoryItem,
  TaskFeedbackAttachment,
  TaskSort,
  CaseRecord,
  PeopleOption,
  DialogAction,
  FeeAction,
  FeeSubtype,
  CaseBatchAction,
  TaskBatchLifecycleAction,
  TaskQuery,
  StatusTab,
} from "./types";

import {
  CASE_CONTEXT_TASK_DEFAULT_PAGE,
  CASE_CONTEXT_TASK_DEFAULT_PAGE_SIZE,
  EMPTY_SUMMARY,
  createdTabs,
  receivedTabs,
  collaboratingTabs,
  appendSelectedUploadFiles,
  normalizeCaseContextTaskPageState,
  contains,
  statusColors,
  taskCreationMode,
  taskCaseNos,
  taskDataValues,
  taskStartedAt,
  taskEndedAt,
  formatTaskDate,
  formatTaskDateTime,
  formatTaskScheduleTime,
  visiblePersonName,
  visibleOptionalPersonName,
  visibleCollaboratorNames,
} from "./constants";

import TaskList from "./TaskList";
import TaskDetail from "./TaskDetail";
import TaskCreateModal from "./TaskCreateModal";
import {
  HandoffModal,
  DialogModal,
  TaskBatchModal,
  FeeModal,
  CaseBatchModal,
  DocumentModal,
  CaseContextModal,
} from "./TaskActionModals";

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

  // ─── State ──────────────────────────────────────────────────────────────
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [peopleOptions, setPeopleOptions] = useState<PeopleOption[]>([]);
  const [, setSummary] = useState<Summary>(EMPTY_SUMMARY);
  const [taskMeta, setTaskMeta] = useState({
    total: 0,
    page: 1,
    pageSize: 15,
    statusCounts: {} as Record<string, number>,
  });
  const [loading, setLoading] = useState(false);
  const loadRequestRef = useRef(0);
  const dashboardTaskTabRef = useRef({
    tab: sessionStorage.getItem("sunhold:dashboard-task-tab") || "",
    appliedView: "",
  });
  const [statusTab, setStatusTab] = useState("");
  const [queryForm] = Form.useForm<TaskQuery>();
  const [query, setQuery] = useState<TaskQuery>({});
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [taskSort, setTaskSort] = useState<TaskSort>(null);
  const [selectedKeys, setSelectedKeys] = useState<Key[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [handoff, setHandoff] = useState<TaskRow | null>(null);
  const [handoffDirectory, setHandoffDirectory] = useState<DirectoryUser[]>([]);
  const [handoffDirectoryLoading, setHandoffDirectoryLoading] = useState(false);
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
  const [caseTaskContextMeta, setCaseTaskContextMeta] = useState({
    total: 0,
    page: CASE_CONTEXT_TASK_DEFAULT_PAGE,
    pageSize: CASE_CONTEXT_TASK_DEFAULT_PAGE_SIZE,
    pages: 0,
  });
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

  // ─── Action lock helpers ───────────────────────────────────────────────
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

  // ─── View / permission flags ───────────────────────────────────────────
  const isPersonalView = initialView.startsWith("task-my");
  const isCreated = initialView.endsWith("-created");
  const isAccepted = initialView.endsWith("-accepted");
  const isCollaborating = initialView.endsWith("-collaborating");
  const isUnread = initialView === "task-my-unread";
  const isReminder = initialView === "task-reminders";
  const canManageInitiatedTask = isPersonalView && isCreated;
  const canManageAcceptedTask =
    (isPersonalView && isAccepted) ||
    initialView === "task-company-accepted";
  const canManageCompanyCreatedTask =
    initialView === "task-company-created";
  const isInitiatedTaskContext = canManageInitiatedTask || canManageCompanyCreatedTask;
  const isAcceptedTaskContext = canManageAcceptedTask;
  const hideTaskFooter =
    taskMeta.total === 0 &&
    (isCreated ||
      isAccepted ||
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
        isInitiatedTaskContext &&
        row.initiator === profile.username &&
        ["待接收", "待处理", "处理中", "进行中"].includes(row.workflow_status || row.status),
    );

  const canReviewTaskException = (row?: TaskRow | null) =>
    Boolean(
      row &&
        (profile.role === "admin" ||
          row.initiator === profile.username ||
          (profile.role === "manager" && profile.department === row.department)),
    );

  // ─── Data loading ──────────────────────────────────────────────────────
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

  // ─── Effects ───────────────────────────────────────────────────────────
  useEffect(() => {
    const routeTabs = isCreated ? createdTabs : isCollaborating ? collaboratingTabs : receivedTabs;
    if (dashboardTaskTabRef.current.appliedView === initialView) return;
    const requestedTab = dashboardTaskTabRef.current.tab;
    const firstTab = routeTabs.some((item) => item.key === requestedTab)
      ? requestedTab
      : routeTabs[0].key;
    dashboardTaskTabRef.current.appliedView = initialView;
    dashboardTaskTabRef.current.tab = "";
    sessionStorage.removeItem("sunhold:dashboard-task-tab");
    setStatusTab(firstTab);
    setSelectedKeys([]);
    queryForm.resetFields();
    setQuery({});
    setTaskSort(null);
    void load({}, firstTab, 1, 15, null);
  }, [initialView]);

  useEffect(() => {
    let active = true;
    void api.get<{ items?: PeopleOption[] }>("/people/options")
      .then(({ data }) => {
        if (active) setPeopleOptions(data.items || []);
      })
      .catch(() => {
        if (active) setPeopleOptions([]);
      });
    return () => { active = false; };
  }, []);

  // ─── Derived data ──────────────────────────────────────────────────────
  const scopedTasks = useMemo(() => {
    const names = [profile.username, profile.display_name].filter(Boolean);
    if (!isPersonalView) return tasks;
    if (isCreated) return tasks.filter((row) => names.includes(row.initiator));
    if (isAccepted) return tasks.filter((row) => names.includes(row.owner));
    if (isCollaborating)
      return tasks.filter((row) =>
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
      if (!contains(taskCreationMode(row), query.source)) return false;
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
    () => tasks.filter((row) => selectedKeys.includes(row.id)),
    [tasks, selectedKeys],
  );
  const selected = selectedRows.length === 1 ? selectedRows[0] : null;

  // ─── Task actions ──────────────────────────────────────────────────────
  const createTask = async () => {
    const values = await createForm.validateFields();
    if (!beginTaskAction()) return;
    try {
      const caseNos = taskDataValues(values.case_nos);
      const startAt = values.start_at as Dayjs;
      const endAt = values.end_at as Dayjs;
      const { data: createdTask } = await api.post("/tasks", {
        ...values,
        collaborators: values.collaborators || [],
        case_no: caseNos[0] || "",
        case_nos: caseNos,
        start_at: startAt.format("YYYY-MM-DDTHH:mm:ss"),
        end_at: endAt.format("YYYY-MM-DDTHH:mm:ss"),
        deadline: formatRequiredDate(endAt, "结束时间"),
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
      const { data } = await api.post(`/tasks/${row.id}/${type}`, { comment: labels[type] });
      message.success(labels[type]);
      setSelectedKeys([]);
      if (communication?.id === row.id) {
        setCommunication(data);
        await loadTaskFeedback(data);
      }
      await load();
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

  // ─── Communication / detail ────────────────────────────────────────────
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

  // ─── Case context / navigation ─────────────────────────────────────────
  const resolveLinkedCase = async (row: TaskRow, caseNo = row.case_no) => {
    if (!caseNo) {
      message.warning("当前任务未关联案件");
      return null;
    }
    try {
      const { data } = await api.get("/records", {
        params: { module: "case", keyword: caseNo, page_size: 100 },
      });
      const record = (data.items as CaseRecord[]).find(
        (item) => item.serial_no === caseNo,
      );
      if (!record) message.warning("未找到关联案件或当前账号无权查看");
      return record || null;
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联案件加载失败");
      return null;
    }
  };

  const openCaseDetail = async (row: TaskRow, caseNo = row.case_no) => {
    const record = await resolveLinkedCase(row, caseNo);
    if (!record) return;
    rememberCaseDetailTarget({ id: record.id, serial_no: record.serial_no });
    onNavigate?.("case-company");
  };

  const applyCaseContextTaskPageState = (payload: any, fallbackPage: number, fallbackPageSize: number) => {
    const normalized = normalizeCaseContextTaskPageState(payload, fallbackPage, fallbackPageSize);
    setCaseTasks(normalized.items);
    setCaseTaskContextMeta({
      total: normalized.total,
      page: normalized.page,
      pageSize: normalized.pageSize,
      pages: normalized.pages,
    });
    return normalized;
  };

  const loadCaseContextTasksPage = async (
    record: CaseRecord,
    nextPage = caseTaskContextMeta.page,
    nextPageSize = caseTaskContextMeta.pageSize,
  ) => {
    const { data } = await api.get(`/cases/${record.id}/tasks`, {
      params: { page: nextPage, page_size: nextPageSize },
    });
    return applyCaseContextTaskPageState(data, nextPage, nextPageSize);
  };

  const openCaseContext = async (row: TaskRow, mode: "tasks" | "logs") => {
    setCaseContextLoading(true);
    try {
      const record = await resolveLinkedCase(row);
      if (!record) return;
      if (mode === "tasks") {
        await loadCaseContextTasksPage(record, CASE_CONTEXT_TASK_DEFAULT_PAGE, CASE_CONTEXT_TASK_DEFAULT_PAGE_SIZE);
        setCaseHistory([]);
      } else {
        const { data } = await api.get(`/records/${record.id}/history`);
        setCaseHistory(data.items);
        setCaseTasks([]);
        setCaseTaskContextMeta({
          total: 0,
          page: CASE_CONTEXT_TASK_DEFAULT_PAGE,
          pageSize: CASE_CONTEXT_TASK_DEFAULT_PAGE_SIZE,
          pages: 0,
        });
      }
      setCaseContext({ mode, record });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "关联案件信息加载失败");
    } finally {
      setCaseContextLoading(false);
    }
  };

  // ─── Comments / attachments ────────────────────────────────────────────
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

  // ─── Batch / helper actions ────────────────────────────────────────────
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

  const openTaskHandoff = async (row: TaskRow) => {
    setHandoff(row);
    handoffForm.setFieldsValue({ recipient: "", comment: "" });
    setHandoffDirectoryLoading(true);
    try {
      const { data } = await api.get("/users/directory");
      setHandoffDirectory(
        (data.items || []).filter((item: DirectoryUser) => item.is_active !== false),
      );
    } catch (error: any) {
      setHandoffDirectory([]);
      message.error(error?.response?.data?.detail || "员工目录加载失败，请稍后重试");
    } finally {
      setHandoffDirectoryLoading(false);
    }
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

  // ─── Columns ───────────────────────────────────────────────────────────
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
          title={`(${taskCreationMode(row)})${String(value || "").replace(/^\([^)]*\)/, "")}`}
          onClick={() => openCommunication(row)}
        >
          {`(${taskCreationMode(row)})${String(value || "").replace(/^\([^)]*\)/, "")}`}
        </Button>
      ),
    },
    {
      title: "案号编号",
      dataIndex: "case_no",
      width: 180,
      ellipsis: true,
      render: (_value: string, row: TaskRow) => renderTaskCaseLinks(row),
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
      title: "开始时间",
      key: "started_at",
      width: 142,
      render: (_: unknown, row: TaskRow) => formatTaskScheduleTime(taskStartedAt(row)) || "—",
    },
    {
      title: "结束时间",
      dataIndex: "deadline",
      width: 110,
      sorter: true,
      sortOrder: taskSort?.field === "deadline" ? taskSort.order : null,
      render: (_: string, row: TaskRow) => formatTaskScheduleTime(taskEndedAt(row)) || "—",
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
      render: (_: string, row: TaskRow) => visiblePersonName(row.initiator_display_name),
    },
    {
      title: "负责人",
      dataIndex: "owner",
      width: 95,
      render: (_: string, row: TaskRow) => visiblePersonName(row.owner_display_name),
    },
  ];

  const unreadColumns: any[] = [
    { title: "任务编号", dataIndex: "serial_no", width: 200, ellipsis: true, render: (value: string, row: TaskRow) => { const label = `(${taskCreationMode(row)})${String(value || "").replace(/^\([^)]*\)/, "")}`; return <Button className="task-cell-link task-table-identifier" type="link" title={label} onClick={() => openCommunication(row)}>{label}</Button> } },
    { title: "关联案号", dataIndex: "case_no", width: 180, ellipsis: true, render: (_: string, row: TaskRow) => renderTaskCaseLinks(row) },
    { title: "未读内容", dataIndex: "latest_unread_message", width: 360, ellipsis: true, render: (value: string) => value || "—" },
    { title: "发送人", dataIndex: "latest_unread_sender", width: 140, ellipsis: true, render: (value: string, row: TaskRow) => visibleOptionalPersonName(value, row.latest_unread_sender_display_name) },
    { title: "发送时间", dataIndex: "latest_unread_at", width: 165, sorter: true, sortOrder: taskSort?.field === "updated_at" ? taskSort.order : null, render: (value: string) => value ? formatTaskDateTime(value) : "—" },
    { title: "任务状态", dataIndex: "status", width: 105, ellipsis: true, render: (value: string) => value || "—" },
    { title: "负责人", dataIndex: "owner", width: 120, ellipsis: true, render: (_: string, row: TaskRow) => visiblePersonName(row.owner_display_name) },
  ];

  const columns = isUnread ? unreadColumns : standardColumns;

  const renderTaskCaseLinks = (row: TaskRow, className = "business-relation-link task-table-identifier") => {
    const caseNos = taskCaseNos(row);
    if (!caseNos.length) return "—";
    return (
      <Space size={4} wrap>
        {caseNos.map((caseNo) => (
          <Button key={caseNo} className={className} type="link" title={caseNo} onClick={() => void openCaseDetail(row, caseNo)}>
            {caseNo}
          </Button>
        ))}
      </Space>
    );
  };

  // ─── Create task open / context from sessionStorage ────────────────────
  const openCreateTask = () => {
    const startAt = dayjs().second(0);
    createForm.setFieldsValue({ owner: profile.username || "admin", priority: "普通", source: "人工", collaborators: [], case_nos: [], start_at: startAt, end_at: startAt.add(7, "day") });
    setCreateOpen(true);
  };

  useEffect(() => {
    const raw = window.sessionStorage.getItem("sunhold:task-create-context");
    if (!raw) return;
    try {
      const context = JSON.parse(raw) as { case_no?: string; customer?: string; title?: string };
      if (!context.case_no) return;
      const caseTaskDefaults = getCaseTaskCreateDefaults();
      createForm.setFieldsValue({
        title: context.title || `案件任务—${context.case_no}`,
        owner: profile.username || "admin",
        priority: caseTaskDefaults.priority,
        source: "案件任务",
        collaborators: [],
        case_nos: [context.case_no],
        start_at: dayjs().second(0),
        end_at: dayjs(caseTaskDefaults.deadline).hour(18).minute(0).second(0),
        customer: context.customer || "",
      });
      setCreateOpen(true);
    } catch {
      // A malformed transient workspace context must not prevent task access.
    } finally {
      window.sessionStorage.removeItem("sunhold:task-create-context");
    }
  }, [createForm, initialView, profile.username]);

  // ─── Fee / document / case batch actions ───────────────────────────────
  const feeLabels = { lawFee: "新增律所费用", platformFee: "新增平台费用", internalFee: "新增内部费用" } as const;
  const documentLabels = { authorization: "授权委托书", lawFirmLetter: "律所函", identity: "身份证明", settlement: "结算提成表" } as const;

  const openFee = (key: FeeAction, subtype: FeeSubtype) => requireOne((row) => {
    feeForm.resetFields();
    feeForm.setFieldsValue({ amount: undefined, expense_date: dayjs(), applicant: visiblePersonName(profile.display_name || row.owner_display_name), description: "" });
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

  const selectedCaseNos = Array.from(new Set(selectedRows.flatMap(taskCaseNos)));

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

  // ─── Upload file change handlers ───────────────────────────────────────
  const makeUploadHandlers = (
    setter: React.Dispatch<React.SetStateAction<UploadFile[]>>,
  ) => ({
    beforeUpload: (file: UploadFile) => {
      setter((items) => [...items, file]);
      return false;
    },
    onRemove: (file: UploadFile) => {
      setter((items) => items.filter((item) => item.uid !== file.uid));
    },
  });

  const createMaterialHandlers = makeUploadHandlers(setCreateMaterialFiles);
  const feedbackFileHandlers = makeUploadHandlers(setFeedbackFiles);
  const materialFileHandlers = makeUploadHandlers(setTaskMaterialFiles);

  // ─── Table change handler ──────────────────────────────────────────────
  const handleTableChange = (
    pagination: any,
    _filters: any,
    sorter: any,
    extra: any,
  ) => {
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
  };

  const handleTabChange = (key: string) => {
    setStatusTab(key);
    setSelectedKeys([]);
    void load(query, key, 1, taskMeta.pageSize);
  };

  const handleQuerySubmit = (values: TaskQuery) => {
    setQuery(values);
    setSelectedKeys([]);
    void load(values, statusTab, 1, taskMeta.pageSize);
  };

  const handleQueryReset = () => {
    queryForm.resetFields();
    setQuery({});
    setTaskSort(null);
    setSelectedKeys([]);
    void load({}, statusTab, 1, taskMeta.pageSize, null);
  };

  const handleCaseTaskPageChange = (nextPage: number, nextPageSize: number) => {
    if (caseContext?.record) void loadCaseContextTasksPage(caseContext.record, nextPage, nextPageSize);
  };

  // ─── Render ────────────────────────────────────────────────────────────
  return (
    <>
      <TaskList
        isUnread={isUnread}
        isCreated={isCreated}
        isCollaborating={isCollaborating}
        tabs={tabs}
        statusTab={statusTab}
        counts={counts}
        mobileFiltersOpen={mobileFiltersOpen}
        queryForm={queryForm}
        loading={loading}
        columns={columns}
        filteredTasks={filteredTasks}
        taskSort={taskSort}
        taskMeta={taskMeta}
        selectedKeys={selectedKeys}
        hideTaskFooter={hideTaskFooter}
        actionSubmitting={actionSubmitting}
        profile={profile}
        canManageInitiatedTask={canManageInitiatedTask}
        canManageAcceptedTask={canManageAcceptedTask}
        canManageCompanyCreatedTask={canManageCompanyCreatedTask}
        canWithdrawTask={canWithdrawTask}
        canReviewTaskException={canReviewTaskException}
        selectedRows={selectedRows}
        selected={selected}
        caseBatchLabels={caseBatchLabels}
        onTabChange={handleTabChange}
        onToggleMobileFilters={() => setMobileFiltersOpen((open) => !open)}
        onQuerySubmit={handleQuerySubmit}
        onQueryReset={handleQueryReset}
        onSelectedKeysChange={setSelectedKeys}
        onTableChange={handleTableChange}
        onOpenCommunication={openCommunication}
        onMarkSelectedUnreadRead={markSelectedUnreadTasksRead}
        onConfirmTask={(row) => void simpleAction(row, "confirm")}
        onWithdrawTask={requestTaskWithdrawal}
        onResendTask={(row) => openDialog(row, "resend")}
        onRestartTask={(row) => void simpleAction(row, "restart")}
        onAcceptSelected={acceptSelectedTask}
        onCompleteSelected={() => requireOne((row) => void simpleAction(row, "complete"))}
        onCompleteOne={(row) => void simpleAction(row, "complete")}
        onOpenHandoff={openTaskHandoff}
        onRequestException={requestTaskException}
        onOpenTaskBatchLifecycle={openTaskBatchLifecycle}
        onMoreAction={moreAction}
      />

      <FeeModal
        feeAction={feeAction}
        feeSubtype={feeSubtype}
        feeForm={feeForm}
        selected={selected}
        actionSubmitting={actionSubmitting}
        labels={feeLabels}
        onOk={submitFee}
        onCancel={() => { setFeeAction(null); setFeeSubtype(null); }}
        onOpenCommunication={openCommunication}
        onOpenCaseDetail={openCaseDetail}
      />

      <CaseBatchModal
        caseBatchAction={caseBatchAction}
        batchForm={batchForm}
        selectedCaseNos={selectedCaseNos}
        actionSubmitting={actionSubmitting}
        labels={caseBatchLabels}
        onOk={submitCaseBatch}
        onCancel={() => setCaseBatchAction(null)}
      />

      <DocumentModal
        documentAction={documentAction}
        documentForm={documentForm}
        actionSubmitting={actionSubmitting}
        labels={documentLabels}
        onOk={submitDocument}
        onCancel={() => setDocumentAction(null)}
      />

      <TaskCreateModal
        open={createOpen}
        createForm={createForm}
        peopleOptions={peopleOptions}
        createMaterialFiles={createMaterialFiles}
        actionSubmitting={actionSubmitting}
        onCancel={() => setCreateOpen(false)}
        onOk={createTask}
        onMaterialFilesChange={createMaterialHandlers}
      />

      <HandoffModal
        handoff={handoff}
        handoffForm={handoffForm}
        handoffDirectory={handoffDirectory}
        handoffDirectoryLoading={handoffDirectoryLoading}
        actionSubmitting={actionSubmitting}
        onOk={submitHandoff}
        onCancel={() => setHandoff(null)}
      />

      <DialogModal
        dialog={dialog}
        dialogForm={dialogForm}
        actionSubmitting={actionSubmitting}
        onOk={submitDialog}
        onCancel={() => setDialog(null)}
      />

      <TaskBatchModal
        taskBatchAction={taskBatchAction}
        taskBatchForm={taskBatchForm}
        selectedCount={selectedRows.length}
        actionSubmitting={actionSubmitting}
        labels={taskBatchLabels}
        onOk={() => void submitTaskBatchLifecycle()}
        onCancel={() => setTaskBatchAction(null)}
      />

      <CaseContextModal
        caseContext={caseContext}
        caseTasks={caseTasks}
        caseHistory={caseHistory}
        caseTaskContextMeta={caseTaskContextMeta}
        caseContextLoading={caseContextLoading}
        onCancel={() => setCaseContext(null)}
        onCaseTaskPageChange={handleCaseTaskPageChange}
      />

      <TaskDetail
        communication={communication}
        history={history}
        feedbackAttachments={feedbackAttachments}
        taskMaterialAttachments={taskMaterialAttachments}
        feedbackFiles={feedbackFiles}
        taskMaterialFiles={taskMaterialFiles}
        actionSubmitting={actionSubmitting}
        isInitiatedTaskContext={isInitiatedTaskContext}
        isAcceptedTaskContext={isAcceptedTaskContext}
        profile={profile}
        commentForm={commentForm}
        onClose={closeCommunication}
        onSimpleAction={(row, type) => void simpleAction(row, type)}
        onOpenHandoff={openTaskHandoff}
        onWithdraw={requestTaskWithdrawal}
        onOpenCaseDetail={openCaseDetail}
        onDownloadAttachment={downloadTaskAttachment}
        onDeleteAttachment={deleteTaskAttachment}
        onUploadMaterials={uploadTaskMaterials}
        onMaterialFilesChange={materialFileHandlers}
        onFeedbackFilesChange={feedbackFileHandlers}
        onAddComment={addComment}
        onMarkHistoryUnread={markHistoryUnread}
        isTaskParticipant={isTaskParticipant}
        canWithdrawTask={canWithdrawTask}
      />
    </>
  );
}

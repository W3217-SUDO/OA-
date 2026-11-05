import { useState } from "react";
import dayjs from "dayjs";
import { POPUP_WIDTH } from "../components/common/popupSize";
import { StatusTag } from "../components/common/StatusTag";
import {
  Alert,
  Button,
  Form,
  Input,
  List,
  Modal,
  Space,
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
import type { FormInstance } from "antd";
import type {
  TaskRow,
  HistoryItem,
  TaskFeedbackAttachment,
} from "./types";
import {
  formatTaskDateTime,
  formatTaskScheduleTime,
  taskCaseNos,
  taskEndedAt,
  taskStartedAt,
  visibleCollaboratorNames,
  visiblePersonName,
} from "./constants";

export interface TaskDetailProps {
  communication: TaskRow | null;
  history: HistoryItem[];
  feedbackAttachments: TaskFeedbackAttachment[];
  taskMaterialAttachments: TaskFeedbackAttachment[];
  feedbackFiles: UploadFile[];
  taskMaterialFiles: UploadFile[];
  actionSubmitting: boolean;
  isInitiatedTaskContext: boolean;
  isAcceptedTaskContext: boolean;
  profile: any;
  commentForm: FormInstance;
  onClose: () => void;
  onSimpleAction: (row: TaskRow, type: "accept" | "restart" | "complete" | "confirm") => void;
  onOpenHandoff: (row: TaskRow) => void;
  onWithdraw: (row: TaskRow) => void;
  onOpenCaseDetail: (row: TaskRow, caseNo?: string) => void;
  onDownloadAttachment: (item: TaskFeedbackAttachment) => void;
  onDeleteAttachment: (item: TaskFeedbackAttachment, categoryLabel: "任务反馈附件" | "任务资料附件") => void;
  onUploadMaterials: () => void;
  onMaterialFilesChange: {
    beforeUpload: (file: UploadFile) => boolean;
    onRemove: (file: UploadFile) => void;
  };
  onFeedbackFilesChange: {
    beforeUpload: (file: UploadFile) => boolean;
    onRemove: (file: UploadFile) => void;
  };
  onAddComment: () => void;
  onMarkHistoryUnread: (item: HistoryItem) => void;
  isTaskParticipant: (row: TaskRow) => boolean;
  canWithdrawTask: (row?: TaskRow | null) => boolean;
  canRequestTaskException: (row?: TaskRow | null) => boolean;
  canReviewTaskException: (row?: TaskRow | null) => boolean;
  onRequestException: (row: TaskRow, action: "挂起" | "取消") => void;
  onReviewException: (row: TaskRow, approved: boolean) => void;
  canMaintainTask: (row?: TaskRow | null) => boolean;
  onMaintainTask: (row: TaskRow) => void;
  /** 501635：点附件名打开（不给就下载） */
  onOpenAttachment?: (item: TaskFeedbackAttachment) => void;
  /** 501635：待接收/待处理时在详情里拒绝任务 */
  onRejectTask?: (row: TaskRow) => void;
}

const renderTaskCaseLinks = (
  row: TaskRow,
  onOpenCaseDetail: (row: TaskRow, caseNo?: string) => void,
  className = "business-relation-link task-table-identifier",
) => {
  const caseNos = taskCaseNos(row);
  if (!caseNos.length) return "—";
  return (
    <Space size={4} wrap>
      {caseNos.map((caseNo) => (
        <Button
          key={caseNo}
          className={className}
          type="link"
          title={caseNo}
          onClick={() => onOpenCaseDetail(row, caseNo)}
        >
          {caseNo}
        </Button>
      ))}
    </Space>
  );
};

export default function TaskDetail(props: TaskDetailProps) {
  const { communication, history, feedbackAttachments, taskMaterialAttachments, feedbackFiles, taskMaterialFiles, actionSubmitting, isInitiatedTaskContext, isAcceptedTaskContext, profile, commentForm, onClose, onSimpleAction, onOpenCaseDetail, onDownloadAttachment, onDeleteAttachment, onUploadMaterials, onMaterialFilesChange, onFeedbackFilesChange, onAddComment, onMarkHistoryUnread, isTaskParticipant } = props;

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

  const [historyExpanded, setHistoryExpanded] = useState(false);
  const status = communication?.workflow_status || communication?.status || "";
  const attachments = [
    ...taskMaterialAttachments.map((item) => ({ item, kind: "任务资料附件" as const })),
    ...feedbackAttachments.map((item) => ({ item, kind: "任务反馈附件" as const })),
  ];
  const orderedHistory = [...history].reverse();
  // 记录按时间先后排；收起时只显示最近 3 条
  const shownHistory = historyExpanded ? orderedHistory : orderedHistory.slice(-3);
  const openAttachment = props.onOpenAttachment || onDownloadAttachment;
  const deadlineHint = (() => {
    const end = communication ? taskEndedAt(communication) : "";
    if (!end || ["已完成", "待确认", "已验收", "已拒绝", "已撤回", "已停止", "已取消"].includes(status)) return "";
    const days = dayjs(end).startOf("day").diff(dayjs().startOf("day"), "day");
    if (Number.isNaN(days)) return "";
    return days >= 0 ? `（剩 ${days} 天）` : `（已逾期 ${-days} 天）`;
  })();
  const canReject = Boolean(communication && props.onRejectTask && isAcceptedTaskContext && communication.can_reject && ["待接收", "待处理"].includes(status));

  return (
    <Modal
      width={POPUP_WIDTH.md}
      open={Boolean(communication)}
      title={<Space>任务处理<StatusTag status={communication?.status} /></Space>}
      footer={communication ? (
        <Space wrap>
          {isInitiatedTaskContext && ["已完成", "待确认", "已拒绝"].includes(status) && (
            <>
              {(!communication.auto_completed || communication.phase_completion_required) && (
                <Button loading={actionSubmitting} onClick={() => onSimpleAction(communication, "restart")}>重启任务</Button>
              )}
              <Button loading={actionSubmitting} onClick={() => onSimpleAction(communication, "confirm")}>确认完成</Button>
            </>
          )}
          {isAcceptedTaskContext && ["待接收", "待处理"].includes(status) && (
            <Button loading={actionSubmitting} onClick={() => onSimpleAction(communication, "accept")}>接受任务</Button>
          )}
          {canReject && (
            <Button danger loading={actionSubmitting} onClick={() => props.onRejectTask?.(communication)}>拒绝任务</Button>
          )}
          {isAcceptedTaskContext && ["处理中", "进行中", "已逾期"].includes(status) && !communication.phase_completion_required && (
            <Button type="primary" loading={actionSubmitting} onClick={() => onSimpleAction(communication, "complete")}>完成任务</Button>
          )}
          {/* 501635（tgn 11-06）：转交、申请取消两个按钮并入“维护任务”；负责人在维护里改负责人即转交，想退回就转给发件人 */}
          {props.canMaintainTask(communication) && (
            <Button style={{ minHeight: 44, minWidth: 44 }} loading={actionSubmitting} onClick={() => props.onMaintainTask(communication)}>维护任务</Button>
          )}
          {communication.exception_request?.status === "待审批" && props.canReviewTaskException(communication) && (
            <>
              <Button style={{ minHeight: 44, minWidth: 44 }} loading={actionSubmitting} onClick={() => props.onReviewException(communication, true)}>通过特殊处理</Button>
              <Button danger style={{ minHeight: 44, minWidth: 44 }} loading={actionSubmitting} onClick={() => props.onReviewException(communication, false)}>驳回特殊处理</Button>
            </>
          )}
          <Button onClick={onClose}>关闭</Button>
        </Space>
      ) : (
        <Button onClick={onClose}>关闭</Button>
      )}
      onCancel={onClose}
    >
      <div className="task-detail-flow" aria-label="任务流程">
        {["任务已分派", "任务处理中", "任务完成", "任务已验收"].map((label, index) => (
          <span key={label} className={index <= statusIndex ? "active" : ""}>{label}</span>
        ))}
      </div>
      <div className="task-detail-main">
        <div className="task-detail-title">{communication?.title || "-"}</div>
        <div className="task-detail-content">{communication?.description?.trim() || "（无任务内容）"}</div>
        <div className="task-detail-people">
          <span><b>发件人：</b>{visiblePersonName(communication?.initiator_display_name)}</span>
          <span><b>负责人：</b>{visiblePersonName(communication?.owner_display_name)}</span>
          <span><b>协作人：</b>{communication ? visibleCollaboratorNames(communication) : "-"}</span>
          <span><b>截止日期：</b>{communication ? formatTaskScheduleTime(taskEndedAt(communication)) || "-" : "-"}<em className={deadlineHint.includes("逾期") ? "overdue" : ""}>{deadlineHint}</em></span>
        </div>
        <div className="task-detail-minor">
          <span>任务编号 {communication?.serial_no?.replace(/^\([^)]*\)/, "") || "-"}</span>
          <span>关联案号 {communication ? renderTaskCaseLinks(communication, onOpenCaseDetail, "business-relation-link") : "-"}</span>
          <span>开始 {communication ? formatTaskScheduleTime(taskStartedAt(communication)) || "-" : "-"}</span>
        </div>
      </div>
      {communication && isTaskParticipant(communication) ? (
        <>
          {attachments.length > 0 && (
            <div className="task-detail-attachments">
              <b>附件：</b>
              <ul>
                {attachments.map(({ item, kind }) => (
                  <li key={`${kind}-${item.id}`}>
                    <Button type="link" size="small" className="task-attachment-name" onClick={() => openAttachment(item)}>{item.original_name}</Button>
                    <span className="task-attachment-meta">{kind === "任务资料附件" ? "任务资料" : "反馈"} · {visiblePersonName(item.uploader_display_name)} · {formatTaskDateTime(item.created_at)}</span>
                    <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => onDownloadAttachment(item)}>下载</Button>
                    {(profile.role === "admin" || item.uploader === profile.username) && (
                      <Button danger type="link" size="small" icon={<DeleteOutlined />} onClick={() => onDeleteAttachment(item, kind)}>删除</Button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Form form={commentForm} layout="vertical" className="task-detail-handle">
            <Form.Item label="反馈内容" name="comment" rules={[{ required: true, message: "请输入反馈内容" }]}>
              <Input.TextArea rows={3} placeholder="填写办理情况" />
            </Form.Item>
            <Space wrap align="start">
              <Upload multiple fileList={feedbackFiles} beforeUpload={onFeedbackFilesChange.beforeUpload} onRemove={onFeedbackFilesChange.onRemove}>
                <Button icon={<UploadOutlined />}>添加附件</Button>
              </Upload>
              <Button type="primary" icon={<CommentOutlined />} loading={actionSubmitting} onClick={onAddComment}>提交反馈</Button>
              <Upload multiple fileList={taskMaterialFiles} beforeUpload={onMaterialFilesChange.beforeUpload} onRemove={onMaterialFilesChange.onRemove}>
                <Button type="link">上传任务资料</Button>
              </Upload>
              {taskMaterialFiles.length > 0 && (
                <Button loading={actionSubmitting} onClick={onUploadMaterials}>确认上传 {taskMaterialFiles.length} 个资料</Button>
              )}
            </Space>
          </Form>
          <div className="task-detail-section-title">沟通记录</div>
          <List
            className="task-history"
            dataSource={shownHistory}
            locale={{ emptyText: "暂无沟通或流转记录" }}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button key="mark-unread" type="link" size="small" disabled={actionSubmitting || item.unread} onClick={() => onMarkHistoryUnread(item)}>
                    {item.unread ? "已标记未读" : "标记未读"}
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space wrap>
                      <Tag color={item.action === "任务沟通" ? "blue" : "default"}>{item.action}</Tag>
                      <b>{visiblePersonName(item.operator_display_name)}</b>
                      <span>{new Date(item.created_at).toLocaleString("zh-CN")}</span>
                    </Space>
                  }
                  description={
                    <>
                      {item.from_status && item.to_status && <div>{`${item.from_status} → ${item.to_status}`}</div>}
                      <p>{item.comment || "-"}</p>
                    </>
                  }
                />
              </List.Item>
            )}
          />
          {orderedHistory.length > 3 && (
            <Button type="link" onClick={() => setHistoryExpanded((value) => !value)}>
              {historyExpanded ? "收起" : `展开全部（共 ${orderedHistory.length} 条）`}
            </Button>
          )}
        </>
      ) : (
        <Alert
          type="info"
          showIcon
          message="当前任务仅供查看"
          description="只有发起人、负责人、协作人和管理员可以查看沟通记录、提交反馈或标记未读。"
        />
      )}
    </Modal>
  );
}

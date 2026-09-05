import {
  Alert,
  Button,
  Form,
  Input,
  List,
  Modal,
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
import type { FormInstance } from "antd";
import type {
  TaskRow,
  HistoryItem,
  TaskFeedbackAttachment,
} from "./types";
import {
  formatTaskDate,
  formatTaskDateTime,
  formatTaskScheduleTime,
  statusColors,
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
  const {
    communication,
    history,
    feedbackAttachments,
    taskMaterialAttachments,
    feedbackFiles,
    taskMaterialFiles,
    actionSubmitting,
    isInitiatedTaskContext,
    isAcceptedTaskContext,
    profile,
    commentForm,
    onClose,
    onSimpleAction,
    onOpenHandoff,
    onWithdraw,
    onOpenCaseDetail,
    onDownloadAttachment,
    onDeleteAttachment,
    onUploadMaterials,
    onMaterialFilesChange,
    onFeedbackFilesChange,
    onAddComment,
    onMarkHistoryUnread,
    isTaskParticipant,
    canWithdrawTask,
  } = props;

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
    <Modal
      width={760}
      open={Boolean(communication)}
      title="案件任务"
      footer={communication ? (
        <Space>
          {isInitiatedTaskContext && ["已完成", "待确认", "已拒绝"].includes(communication.workflow_status || communication.status) && (
            <>
              {!communication.auto_completed && (
                <Button
                  loading={actionSubmitting}
                  onClick={() => onSimpleAction(communication, "restart")}
                >
                  重启任务
                </Button>
              )}
              <Button
                loading={actionSubmitting}
                onClick={() => onSimpleAction(communication, "confirm")}
              >
                确认完成
              </Button>
            </>
          )}
          {isAcceptedTaskContext && ["待接收", "待处理"].includes(communication.workflow_status || communication.status) && (
            <Button
              loading={actionSubmitting}
              onClick={() =>
                onSimpleAction(
                  communication,
                  communication.handoff_auto_complete_at ? "restart" : "accept",
                )
              }
            >
              接受任务
            </Button>
          )}
          {isAcceptedTaskContext && ["待接收", "待处理", "处理中", "进行中", "已逾期"].includes(communication.workflow_status || communication.status) && (
            <>
              <Button
                loading={actionSubmitting}
                onClick={() => onSimpleAction(communication, "complete")}
              >
                完成任务
              </Button>
              <Button
                loading={actionSubmitting}
                onClick={() => onOpenHandoff(communication)}
              >
                转交任务
              </Button>
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
          <span key={label} className={index <= statusIndex ? "active" : ""}>
            {label}
          </span>
        ))}
      </div>
      <div className="task-detail-meta">
        <span><b>任务标题：</b>{communication?.title || "-"}</span>
        <span><b>任务编号：</b>{communication?.serial_no?.replace(/^\([^)]*\)/, "") || "-"}</span>
        <span><b>当前负责人：</b>{visiblePersonName(communication?.owner_display_name)}</span>
        <span><b>发布人：</b>{visiblePersonName(communication?.initiator_display_name)}</span>
        <span>
          <b>关联案号：</b>
          {communication
            ? renderTaskCaseLinks(communication, onOpenCaseDetail, "business-relation-link")
            : "-"}
        </span>
        <span>
          <b>开始时间：</b>
          {communication ? formatTaskScheduleTime(taskStartedAt(communication)) || "-" : "-"}
        </span>
        <span>
          <b>结束时间：</b>
          {communication ? formatTaskScheduleTime(taskEndedAt(communication)) || "-" : "-"}
        </span>
        <span>
          <b>状态：</b>
          <Tag color={statusColors[communication?.status || ""] || "blue"}>
            {communication?.status || "-"}
          </Tag>
        </span>
        <span><b>当前协作人：</b>{visibleCollaboratorNames(communication)}</span>
      </div>
      {communication && isTaskParticipant(communication) ? (
        <>
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
                    onClick={() => onMarkHistoryUnread(item)}
                  >
                    {item.unread ? "已标记未读" : "标记未读"}
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color={item.action === "任务沟通" ? "blue" : "default"}>
                        {item.action}
                      </Tag>
                      <b>{visiblePersonName(item.operator_display_name)}</b>
                      <span>{new Date(item.created_at).toLocaleString("zh-CN")}</span>
                    </Space>
                  }
                  description={
                    <>
                      <div>
                        {item.from_status && item.to_status &&
                          `${item.from_status} → ${item.to_status}`}
                      </div>
                      <p>{item.comment || "-"}</p>
                    </>
                  }
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
              {
                title: "上传人",
                dataIndex: "uploader",
                width: 110,
                render: (_: string, item: TaskFeedbackAttachment) =>
                  visiblePersonName(item.uploader_display_name),
              },
              {
                title: "上传时间",
                dataIndex: "created_at",
                width: 168,
                render: (value: string) => formatTaskDateTime(value),
              },
              {
                title: "操作",
                width: 150,
                render: (_: unknown, item: TaskFeedbackAttachment) => (
                  <Space size={0}>
                    <Button
                      type="link"
                      icon={<DownloadOutlined />}
                      onClick={() => onDownloadAttachment(item)}
                    >
                      下载
                    </Button>
                    {(profile.role === "admin" || item.uploader === profile.username) && (
                      <Button
                        danger
                        type="link"
                        icon={<DeleteOutlined />}
                        onClick={() => onDeleteAttachment(item, "任务资料附件")}
                      >
                        删除
                      </Button>
                    )}
                  </Space>
                ),
              },
            ]}
          />
          <Upload
            multiple
            fileList={taskMaterialFiles}
            beforeUpload={onMaterialFilesChange.beforeUpload}
            onRemove={onMaterialFilesChange.onRemove}
            style={{ marginTop: 12 }}
          >
            <Button icon={<UploadOutlined />}>选择任务资料附件</Button>
          </Upload>
          <Button
            type="primary"
            loading={actionSubmitting}
            disabled={!taskMaterialFiles.length}
            onClick={onUploadMaterials}
            style={{ marginLeft: 8 }}
          >
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
              {
                title: "上传人",
                dataIndex: "uploader",
                width: 110,
                render: (_: string, item: TaskFeedbackAttachment) =>
                  visiblePersonName(item.uploader_display_name),
              },
              {
                title: "上传时间",
                dataIndex: "created_at",
                width: 168,
                render: (value: string) => formatTaskDateTime(value),
              },
              {
                title: "操作",
                width: 150,
                render: (_: unknown, item: TaskFeedbackAttachment) => (
                  <Space size={0}>
                    <Button
                      type="link"
                      icon={<DownloadOutlined />}
                      onClick={() => onDownloadAttachment(item)}
                    >
                      下载
                    </Button>
                    {(profile.role === "admin" || item.uploader === profile.username) && (
                      <Button
                        danger
                        type="link"
                        icon={<DeleteOutlined />}
                        onClick={() => onDeleteAttachment(item, "任务反馈附件")}
                      >
                        删除
                      </Button>
                    )}
                  </Space>
                ),
              },
            ]}
          />
          <Form form={commentForm} layout="vertical" style={{ marginTop: 16 }}>
            <Form.Item
              label="反馈内容"
              name="comment"
              rules={[{ required: true, message: "请输入反馈内容" }]}
            >
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item label="反馈附件（可多选，单个不超过 20MB）">
              <Upload
                multiple
                fileList={feedbackFiles}
                beforeUpload={onFeedbackFilesChange.beforeUpload}
                onRemove={onFeedbackFilesChange.onRemove}
              >
                <Button icon={<UploadOutlined />}>选择反馈附件</Button>
              </Upload>
            </Form.Item>
            <Button
              type="primary"
              icon={<CommentOutlined />}
              loading={actionSubmitting}
              onClick={onAddComment}
            >
              提交反馈
            </Button>
          </Form>
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

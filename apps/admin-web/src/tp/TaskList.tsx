import type { Key } from "react";
import {
  Button,
  Card,
  DatePicker,
  Dropdown,
  Form,
  Input,
  Select,
  Space,
  Tag,
} from "antd";
import Table from "../components/ResizableTable";
import type { FitStackGroup } from "../components/ResizableTable";
import type { FormInstance, TablePaginationConfig } from "antd";
import type { SorterResult } from "antd/es/table/interface";
import type {
  TaskRow,
  TaskQuery,
  TaskSort,
  StatusTab,
  CaseBatchAction,
  TaskBatchLifecycleAction,
} from "./types";
import {
  formatTaskDate,
  formatTaskScheduleTime,
  statusColors,
  taskCaseNos,
  taskEndedAt,
  taskStartedAt,
  visiblePersonName,
} from "./constants";
import { useFilterToggle } from "../components/common/MobileFilterToggle";


// 一屏放不下时，原告/被告、发起人/负责人各叠放在一个单元格里（数据不减少）。
const TASK_FIT_STACK: FitStackGroup[] = [
  { title: <span>原告<br />被告</span>, keys: ["plaintiff", "defendant"] },
  { title: <span>发起人<br />负责人</span>, keys: ["initiator", "owner"] },
];
export interface TaskListProps {
  isUnread: boolean;
  isCreated: boolean;
  isCollaborating: boolean;
  tabs: StatusTab[];
  statusTab: string;
  counts: Record<string, number>;
  mobileFiltersOpen: boolean;
  queryForm: FormInstance<TaskQuery>;
  loading: boolean;
  columns: any[];
  filteredTasks: TaskRow[];
  taskSort: TaskSort;
  taskMeta: { total: number; page: number; pageSize: number; statusCounts: Record<string, number> };
  selectedKeys: Key[];
  hideTaskFooter: boolean;
  actionSubmitting: boolean;
  profile: any;
  canManageInitiatedTask: boolean;
  canManageAcceptedTask: boolean;
  canManageCompanyCreatedTask: boolean;
  canWithdrawTask: (row?: TaskRow | null) => boolean;
  canReviewTaskException: (row?: TaskRow | null) => boolean;
  canRequestTaskException: (row?: TaskRow | null) => boolean;
  canMaintainTask: (row?: TaskRow | null) => boolean;
  selectedRows: TaskRow[];
  selected: TaskRow | null;
  caseBatchLabels: Record<CaseBatchAction, string>;
  onTabChange: (key: string) => void;
  onToggleMobileFilters: () => void;
  onQuerySubmit: (values: TaskQuery) => void;
  onQueryReset: () => void;
  /** 任务中心直接新建任务：不关联案件即为事务性任务。 */
  onCreateTask: () => void;
  onSelectedKeysChange: (keys: Key[]) => void;
  onTableChange: (
    pagination: TablePaginationConfig,
    filters: Record<string, (string | number | boolean)[] | null>,
    sorter: SorterResult<TaskRow> | SorterResult<TaskRow>[],
    extra: { action: "paginate" | "sort" | "filter" },
  ) => void;
  onOpenCommunication: (row: TaskRow) => void;
  onMarkSelectedUnreadRead: () => void;
  onConfirmTask: (row: TaskRow) => void;
  onWithdrawTask: (row: TaskRow) => void;
  onResendTask: (row: TaskRow) => void;
  onRestartTask: (row: TaskRow) => void;
  onAcceptSelected: () => void;
  onCompleteSelected: () => void;
  onCompleteOne: (row: TaskRow) => void;
  onOpenHandoff: (row: TaskRow) => void;
  onRequestException: (row: TaskRow, action: "挂起" | "取消") => void;
  onReviewException: (row: TaskRow, approved: boolean) => void;
  onMaintainTask: (row: TaskRow) => void;
  onOpenTaskBatchLifecycle: (action: TaskBatchLifecycleAction) => void;
  onMoreAction: (key: string) => void;
}

export default function TaskList(props: TaskListProps) {
  const { canRequestTaskException, onRequestException, onReviewException } = props;
  const { isUnread, tabs, statusTab, counts, queryForm, loading, columns, filteredTasks, taskMeta, selectedKeys, hideTaskFooter, actionSubmitting, profile, canManageInitiatedTask, canManageAcceptedTask, canManageCompanyCreatedTask, canWithdrawTask, canReviewTaskException, selectedRows, selected, caseBatchLabels, onTabChange, onQuerySubmit, onQueryReset, onCreateTask, onSelectedKeysChange, onTableChange, onOpenCommunication, onMarkSelectedUnreadRead, onConfirmTask, onWithdrawTask, onResendTask, onRestartTask, onAcceptSelected, onCompleteSelected, onCompleteOne, onOpenHandoff, onOpenTaskBatchLifecycle, onMoreAction } = props;
  // 查询区折叠：桌面默认展开、按页面记住；手机默认收起（原来的手机开关由共享开关替代）。
  const filterToggle = useFilterToggle("查询条件");

  return (
    <Card
      className={`task-original-panel task-original-standard${isUnread ? " task-unread-panel" : ""}`}
      title={isUnread ? "未读消息任务列表" : "任务列表"}
    >
      {!isUnread && (
        <div className="task-status-tabs">
          {tabs.map((item) => (
            <button
              key={item.key}
              type="button"
              className={statusTab === item.key ? "active" : ""}
              onClick={() => onTabChange(item.key)}
            >
              {item.label}({counts[item.key] || 0})
            </button>
          ))}
        </div>
      )}

      {filterToggle.toggle}

      <Form<TaskQuery>
        form={queryForm}
        className={`task-query${filterToggle.open ? " mobile-open" : ""} ${filterToggle.fieldsClassName}`}
        colon
        onFinish={onQuerySubmit}
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
        <div className="task-query-submit oa-filter-keep">
          <Button type="primary" htmlType="submit">
            查询
          </Button>
          <Button htmlType="button" onClick={onQueryReset}>
            重置
          </Button>
          <Button htmlType="button" type="primary" className="task-create-button" onClick={onCreateTask}>
            新建任务
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
        fitStack={TASK_FIT_STACK}
        dataSource={filteredTasks}
        tableLayout="fixed"
        scroll={{ x: isUnread ? 1270 : 1900 }}
        rowSelection={{
          selectedRowKeys: selectedKeys,
          onChange: onSelectedKeysChange,
        }}
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
        onChange={onTableChange as any}
      />

      <div className="task-mobile-list" aria-label="移动端任务列表">
        {filteredTasks.length
          ? filteredTasks.map((row) => (
              <article
                key={row.id}
                className={`task-mobile-card${
                  selectedKeys.includes(row.id) ? " selected" : ""
                }`}
              >
                <div className="task-mobile-card-head">
                  <label className="task-mobile-select">
                    <input
                      type="checkbox"
                      aria-label={`选择任务 ${row.title || row.serial_no}`}
                      checked={selectedKeys.includes(row.id)}
                      onChange={(event) => {
                        onSelectedKeysChange(
                          event.target.checked
                            ? Array.from(new Set([...selectedKeys, row.id]))
                            : selectedKeys.filter((key) => key !== row.id),
                        );
                      }}
                    />
                  </label>
                  <Button type="link" onClick={() => onOpenCommunication(row)}>
                    {row.title || row.serial_no}
                  </Button>
                  <Tag color={statusColors[row.status] || "default"}>
                    {row.status || "-"}
                  </Tag>
                </div>
                <button
                  type="button"
                  className="task-mobile-card-body"
                  onClick={() => onOpenCommunication(row)}
                >
                  <span>
                    <b>任务编号</b>
                    {row.serial_no || "-"}
                  </span>
                  <span>
                    <b>案件编号</b>
                    {taskCaseNos(row).join("、") || "-"}
                  </span>
                  <span>
                    <b>负责人</b>
                    {visiblePersonName(row.owner_display_name)}
                  </span>
                  <span>
                    <b>优先级</b>
                    {row.priority || "-"}
                  </span>
                  <span>
                    <b>发起时间</b>
                    {formatTaskDate(row.created_at) || "-"}
                  </span>
                  <span>
                    <b>开始时间</b>
                    {formatTaskScheduleTime(taskStartedAt(row)) || "-"}
                  </span>
                  <span>
                    <b>结束时间</b>
                    {formatTaskScheduleTime(taskEndedAt(row)) || "-"}
                  </span>
                </button>
              </article>
            ))
          : <div className="task-mobile-empty">没有符合条件的任务</div>}
      </div>

      {!hideTaskFooter && (
        <div className="task-bottom-actions">
          <Space size={5} wrap>
            {isUnread && (
              <Button
                loading={actionSubmitting}
                onClick={onMarkSelectedUnreadRead}
              >
                标记已读
              </Button>
            )}
            {canManageInitiatedTask && statusTab === "finished" && (
              <Button onClick={() => selected && onConfirmTask(selected)}>
                验收任务
              </Button>
            )}
            {canManageInitiatedTask && statusTab !== "finished" && (
              <Button
                danger
                disabled={!canWithdrawTask(selected)}
                onClick={() => selected && onWithdrawTask(selected)}
              >
                撤回任务
              </Button>
            )}
            {(canManageInitiatedTask || canManageCompanyCreatedTask) &&
              selected?.status === "已拒绝" && (
                <Button onClick={() => selected && onResendTask(selected)}>
                  重新派发
                </Button>
              )}
            {(canManageInitiatedTask || canManageCompanyCreatedTask) &&
              ["已完成", "待确认"].includes(
                selected?.workflow_status || selected?.status || "",
              ) && (
                <>
                  {(!selected?.auto_completed || selected.phase_completion_required) && (
                    <Button onClick={() => selected && onRestartTask(selected)}>
                      重启任务
                    </Button>
                  )}
                </>
              )}
            {canManageAcceptedTask && statusTab === "pending" && (
              <Button onClick={onAcceptSelected}>接受任务</Button>
            )}
            {canManageAcceptedTask && statusTab === "pending" && (
              <>
                <Button disabled={selectedRows.some(row => row.phase_completion_required)} onClick={onCompleteSelected}>完成任务</Button>
                <Button onClick={() => selected && onOpenHandoff(selected)}>
                  转交任务
                </Button>
              </>
            )}
            {canManageAcceptedTask && statusTab === "processing" && (
              <>
                <Button disabled={selected?.phase_completion_required} onClick={() => selected && onCompleteOne(selected)}>
                  完成任务
                </Button>
                <Button onClick={() => selected && onOpenHandoff(selected)}>
                  转交任务
                </Button>
              </>
            )}
            {selectedRows.length > 1 &&
              (canManageAcceptedTask ||
                canManageInitiatedTask ||
                canManageCompanyCreatedTask) && (
                <Dropdown
                  trigger={["click"]}
                  menu={{
                    items: [
                      ...(canManageAcceptedTask
                        ? [
                            { key: "accept", label: "批量接收任务" },
                            { key: "complete", label: "批量提交完成", disabled: selectedRows.some(row => row.phase_completion_required) },
                            { key: "handoff", label: "批量交接任务" },
                          ]
                        : []),
                      ...(canManageInitiatedTask || canManageCompanyCreatedTask
                        ? [
                            { key: "confirm", label: "批量验收任务" },
                            { key: "withdraw", label: "批量撤回任务", danger: true },
                          ]
                        : []),
                    ],
                    onClick: ({ key }) =>
                      onOpenTaskBatchLifecycle(key as TaskBatchLifecycleAction),
                  }}
                >
                  <Button>批量任务流转</Button>
                </Dropdown>
              )}
            {(canManageAcceptedTask || canManageCompanyCreatedTask) &&
              selected?.workflow_status === "已停止" &&
              selected?.exception_request?.action === "挂起" && (
                <Button onClick={() => selected && onRestartTask(selected)}>
                  恢复挂起任务
                </Button>
              )}
            {selected?.exception_request?.status === "待审批" &&
              canReviewTaskException(selected) && (
                <>
                  <Button style={{ minHeight: 44, minWidth: 44 }} onClick={() => selected && onReviewException(selected, true)}>
                    通过特殊处理
                  </Button>
                  <Button
                    danger
                    style={{ minHeight: 44, minWidth: 44 }}
                    onClick={() => selected && onReviewException(selected, false)}
                  >
                    驳回特殊处理
                  </Button>
                </>
              )}
            {selected && canRequestTaskException(selected) && (
              <Button danger style={{ minHeight: 44, minWidth: 44 }} loading={actionSubmitting} onClick={() => onRequestException(selected, "取消")}>
                申请取消任务
              </Button>
            )}
            {selected && props.canMaintainTask(selected) && (
              <Button style={{ minHeight: 44, minWidth: 44 }} loading={actionSubmitting} onClick={() => props.onMaintainTask(selected)}>维护任务</Button>
            )}
            {selected?.performance_impact?.overdue && (
              <Tag color="red">
                超期 {selected.performance_impact.overdue_days} 天，绩效影响{" "}
                {selected.performance_impact.penalty_points} 分
              </Tag>
            )}
            {canManageCompanyCreatedTask &&
              (selected?.workflow_status || selected?.status) === "处理中" && (
                <>
                  <Button onClick={() => selected && onCompleteOne(selected)}>
                    完成任务
                  </Button>
                  <Button onClick={() => selected && onOpenHandoff(selected)}>
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
                    children: ["官费", "第三方费用", "代理费", "其他费用"].map(
                      (subtype) => ({
                        key: `lawFee:${subtype}`,
                        label: subtype,
                      }),
                    ),
                  },
                  {
                    key: "platformFee",
                    label: "新增平台费用",
                    children: ["官费", "第三方费用", "代理费", "其他费用"].map(
                      (subtype) => ({
                        key: `platformFee:${subtype}`,
                        label: subtype,
                      }),
                    ),
                  },
                  { key: "internalFee", label: "新增内部费用" },
                  ...(["admin", "manager"].includes(profile.role)
                    ? [
                        {
                          key: "batch",
                          label: "批量修改",
                          children: (
                            Object.entries(caseBatchLabels) as [
                              CaseBatchAction,
                              string,
                            ][]
                          ).map(([action, label]) => ({
                            key: `caseBatch:${action}`,
                            label,
                          })),
                        },
                      ]
                    : []),
                  { key: "authorization", label: "生成授权委托书" },
                  { key: "lawFirmLetter", label: "生成律所函" },
                  { key: "identity", label: "生成身份证明" },
                  { key: "settlement", label: "生成结算提成表" },
                  { key: "caseTasks", label: "案件任务" },
                  { key: "logs", label: "案件日志" },
                  { key: "export", label: "导出案件打印表" },
                ],
                onClick: ({ key }) => onMoreAction(key),
              }}
            >
              <Button>更多操作</Button>
            </Dropdown>
          </Space>
        </div>
      )}
    </Card>
  );
}

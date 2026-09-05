import type { TableColumnsType } from "antd";
import {
Button,
Card,
Input,
Select,
Space,
Table,
Tag,
} from "antd";
import { useMemo } from "react";
import { isLegacyIprRecord,statusColor } from "./constants";
import type { IprRecord } from "./types";

interface IprCaseListProps {
  items: IprRecord[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
  loading: boolean;
  keyword: string;
  caseCategoryFilter: "" | "litigation" | "non_litigation";
  annualFeeMonitoringFilter: "" | "true" | "false";
  reminderTypeId: number | null;
  reminderTypeName: string;
  selectedIprCaseIds: number[];
  kind: string;
  reviewView: boolean;
  roleView: { roleView: string; label: string } | undefined;
  warningUnread: number;
  profile: { role?: string; username?: string };
  onKeywordChange: (value: string) => void;
  onSearch: () => void;
  onCaseCategoryChange: (value: "" | "litigation" | "non_litigation") => void;
  onAnnualFeeMonitoringChange: (value: "" | "true" | "false") => void;
  onResetSearch: () => void;
  onReminderTypeClose: () => void;
  onOpenWarning: () => void;
  onOpenReminderTypes: () => void;
  onOpenLegacyHistory: () => void;
  onExportExcel: () => void;
  onOpenBatchCreate: () => void;
  onOpenBatchUpload: () => void;
  onNavigate: (route: string) => void;
  onOpenBatchMaintenance: () => void;
  onSetAnnualFeeMonitoring: (enabled: boolean) => void;
  onOpenCreate: () => void;
  onSelectedIdsChange: (ids: number[]) => void;
  onPageChange: (page: number, pageSize: number) => void;
  onOpenDetail: (record: IprRecord) => void;
  onOpenMainListCustomerCases: (record: IprRecord) => void;
  onEdit: (record: IprRecord) => void;
  onAction: (record: IprRecord, name: "submit" | "close" | "reopen" | "review", approved?: boolean) => void;
  onOpenIprReboot: (record: IprRecord) => void;
  onOpenCpcApplication: (record: IprRecord) => void;
}

export function IprCaseList({
  items,
  total,
  page,
  pageSize,
  pages,
  loading,
  keyword,
  caseCategoryFilter,
  annualFeeMonitoringFilter,
  reminderTypeId,
  reminderTypeName,
  selectedIprCaseIds,
  kind,
  reviewView,
  roleView,
  warningUnread,
  profile,
  onKeywordChange,
  onSearch,
  onCaseCategoryChange,
  onAnnualFeeMonitoringChange,
  onResetSearch,
  onReminderTypeClose,
  onOpenWarning,
  onOpenReminderTypes,
  onOpenLegacyHistory,
  onExportExcel,
  onOpenBatchCreate,
  onOpenBatchUpload,
  onNavigate,
  onOpenBatchMaintenance,
  onSetAnnualFeeMonitoring,
  onOpenCreate,
  onSelectedIdsChange,
  onPageChange,
  onOpenDetail,
  onOpenMainListCustomerCases,
  onEdit,
  onAction,
  onOpenIprReboot,
  onOpenCpcApplication,
}: IprCaseListProps) {
  const columns: TableColumnsType<IprRecord> = useMemo(
    () => [
      {
        title: "案件编号",
        dataIndex: "serial_no",
        width: 195,
        ellipsis: true,
        render: (v: string, row) => (
          <Button type="link" onClick={() => onOpenDetail(row)}>
            {v}
          </Button>
        ),
      },
      {
        title: "类型",
        width: 80,
        render: (_, row) => (
          <Tag color={row.data.case_kind === "专利" ? "blue" : "purple"}>
            {row.data.case_kind}
          </Tag>
        ),
      },
      { title: "案件名称", dataIndex: "title", width: 220, ellipsis: true },
      {
        title: "申请号/注册号",
        width: 160,
        ellipsis: true,
        render: (_, row) => row.data.application_no || "—",
      },
      {
        title: "申请日",
        width: 110,
        render: (_, row) => row.data.application_date || "—",
      },
      {
        title: "客户",
        dataIndex: "customer",
        width: 160,
        ellipsis: true,
        render: (_, row) => (
          <Button
            type="link"
            size="small"
            onClick={() => onOpenMainListCustomerCases(row)}
          >
            {row.customer || "-"}
          </Button>
        ),
      },
      {
        title: "处理人",
        width: 110,
        render: (_, row) => row.data.case_manager || "—",
      },
      {
        title: "期限",
        width: 110,
        render: (_, row) => row.data.deadline || "—",
      },
      {
        title: "年费监控",
        width: 100,
        render: (_, row) =>
          row.data.annual_fee_monitoring ? (
            <Tag color="green">监控中</Tag>
          ) : (
            <Tag>未监控</Tag>
          ),
      },
      {
        title: "状态",
        width: 110,
        render: (_, row) => (
          <Tag color={statusColor[row.status] || "default"}>
            {row.status}
          </Tag>
        ),
      },
      {
        title: "操作",
        fixed: "right",
        width: 250,
        render: (_, row) => (
          <Space size={0}>
            {["草稿", "已驳回"].includes(row.status) && (
              <Button type="link" onClick={() => onEdit(row)}>
                编辑
              </Button>
            )}
            {["草稿", "已驳回"].includes(row.status) && (
              <Button type="link" onClick={() => onAction(row, "submit")}>
                提交审核
              </Button>
            )}
            {row.status === "在办" && (
              <Button
                type="link"
                danger
                onClick={() => onAction(row, "close")}
              >
                结案
              </Button>
            )}
            {row.status === "已结案" &&
              ["admin", "manager"].includes(profile.role || "") && (
                <Button
                  type="link"
                  onClick={() => onAction(row, "reopen")}
                >
                  重新开启
                </Button>
              )}
            {!isLegacyIprRecord(row) && (
              <Button type="link" onClick={() => onOpenIprReboot(row)}>
                案件重提
              </Button>
            )}
            {!isLegacyIprRecord(row) &&
              row.data?.case_kind === "专利" && (
                <Button
                  type="link"
                  onClick={() => onOpenCpcApplication(row)}
                >
                  CPC申报
                </Button>
              )}
            {reviewView &&
              row.status === "待立案审核" &&
              ["admin", "manager"].includes(profile.role || "") && (
                <>
                  <Button
                    type="link"
                    onClick={() => onAction(row, "review", true)}
                  >
                    通过
                  </Button>
                  <Button
                    type="link"
                    danger
                    onClick={() => onAction(row, "review", false)}
                  >
                    驳回
                  </Button>
                </>
              )}
          </Space>
        ),
      },
    ],
    [pageSize, profile.role, reviewView, onOpenDetail, onOpenMainListCustomerCases, onEdit, onAction, onOpenIprReboot, onOpenCpcApplication]
  );

  return (
    <Card
      title={
        reviewView
          ? "知识产权立案审核"
          : `${roleView?.label || kind || "全部"}案件台账`
      }
      extra={
        !reviewView && (
          <Space>
            {roleView ? (
              <Tag color="blue">
                身份筛选：{roleView.label}
              </Tag>
            ) : null}
            <Input
              allowClear
              placeholder="编号、名称、客户、申请号"
              value={keyword}
              onChange={(e) => onKeywordChange(e.target.value)}
              onPressEnter={onSearch}
              style={{ width: 220 }}
            />
            <Button onClick={onSearch}>查询</Button>
            <Select
              value={caseCategoryFilter}
              onChange={onCaseCategoryChange}
              style={{ width: 120 }}
              options={[
                { value: "", label: "全部案件" },
                { value: "litigation", label: "诉讼案件" },
                { value: "non_litigation", label: "非诉案件" },
              ]}
            />
            <Button onClick={onResetSearch}>重置</Button>
            <Button onClick={onOpenWarning}>
              案件预警
              {warningUnread ? (
                <Tag color="red" style={{ marginInlineStart: 6 }}>
                  {warningUnread}
                </Tag>
              ) : null}
            </Button>
            <Button onClick={onOpenReminderTypes}>案件提醒类型</Button>
            <Button onClick={onOpenLegacyHistory}>
              Historical read-only cases
            </Button>
            {reminderTypeId ? (
              <Tag
                closable
                onClose={onReminderTypeClose}
              >
                提醒类型：{reminderTypeName || reminderTypeId}
              </Tag>
            ) : null}
            <Select
              value={annualFeeMonitoringFilter}
              onChange={onAnnualFeeMonitoringChange}
              style={{ width: 112 }}
              options={[
                { value: "", label: "全部年费" },
                { value: "true", label: "监控中" },
                { value: "false", label: "未监控" },
              ]}
            />
            <Button onClick={onExportExcel}>导出Excel</Button>
            <Button onClick={onOpenBatchCreate}>批量新建案件</Button>
            <Button onClick={onOpenBatchUpload}>批量上传文档</Button>
            <Button onClick={() => onNavigate("ipr-custom-file-import")}>
              案件自定义文件导入
            </Button>
            <Button onClick={() => onNavigate("case-files-receipt")}>
              案件票据导入
            </Button>
            <Button onClick={() => onNavigate("case-files-invoice")}>
              案件发票导入
            </Button>
            <Button
              disabled={!selectedIprCaseIds.length}
              onClick={onOpenBatchMaintenance}
            >
              批量维护
            </Button>
            <Button
              disabled={!selectedIprCaseIds.length}
              onClick={() => onSetAnnualFeeMonitoring(true)}
            >
              加入年费监控
            </Button>
            <Button
              disabled={!selectedIprCaseIds.length}
              onClick={() => onSetAnnualFeeMonitoring(false)}
            >
              放弃年费监控
            </Button>
            <Button type="primary" onClick={onOpenCreate}>
              新建{kind || "知识产权"}案件
            </Button>
          </Space>
        )
      }
    >
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={items}
        rowSelection={{
          selectedRowKeys: selectedIprCaseIds,
          onChange: (keys) => onSelectedIdsChange(keys.map(Number)),
        }}
        scroll={{ x: 1250 }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: ["15", "20", "50", "100"],
          showQuickJumper: { goButton: <Button size="small">GO</Button> },
          showTotal: (t) =>
            "共 " + t + " 条" + (pages ? " / " + pages + " 页" : ""),
          onChange: (nextPage, nextPageSize) =>
            onPageChange(nextPage, nextPageSize),
        }}
      />
    </Card>
  );
}

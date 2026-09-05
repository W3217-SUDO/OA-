import {
  Button,
  Card,
  Checkbox,
  Dropdown,
  Input,
  Select,
  Space,
  Table,
} from "antd";
import {
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { customerStatusLabel } from "../customerStatusLabel";
import { displayChinesePersonName, displayChinesePersonNames } from "../contractPeoplePresentation.mjs";
import type { Customer, DirectoryUser, Profile } from "./types";
import type { CustomerListSummary } from "../customerParity.mjs";
import type { Key } from "react";

interface CustomerListProps {
  initialView: string;
  rows: Customer[];
  total: number;
  page: number;
  pageSize: number;
  customerPageCount: number;
  customerPageNumbers: number[];
  jumpPage: string;
  loading: boolean;
  keyword: string;
  customerType: string;
  customerTypeOptions: { value: string; label: string }[];
  managerKeyword: string;
  managerLocked: boolean;
  managerDisplay: string;
  isOriginalCustomerList: boolean;
  isReadOnlyCustomerList: boolean;
  selectedRowKeys: Key[];
  listSummary: CustomerListSummary;
  profile: Profile;
  directory: DirectoryUser[];
  originalActionItems: { key: string; label: string }[];
  onKeywordChange: (value: string) => void;
  onCustomerTypeChange: (value: string) => void;
  onManagerKeywordChange: (value: string) => void;
  onSearch: () => void;
  onReset: () => void;
  onSelectedRowKeysChange: (keys: Key[]) => void;
  onStartCreate: (customerType: string) => void;
  onOpenDetail: (customer: Customer, tab?: string) => void;
  onOpenCustomerCommunication: (customer: Customer) => void;
  onOpenCustomerContracts: (customer: Customer) => void;
  onOpenCustomerCivilCases: (customer: Customer) => void;
  onOpenCustomerIprCases: (customer: Customer) => void;
  onRunOriginalAction: (key: string) => void;
  onGoToPage: (page: number) => void;
  onJumpPageChange: (value: string) => void;
  onPageSizeChange: (value: number) => void;
}

export function CustomerList({
  initialView,
  rows,
  total,
  page,
  pageSize,
  customerPageCount,
  customerPageNumbers,
  jumpPage,
  loading,
  keyword,
  customerType,
  customerTypeOptions,
  managerKeyword,
  managerLocked,
  managerDisplay,
  isOriginalCustomerList,
  isReadOnlyCustomerList,
  selectedRowKeys,
  listSummary,
  profile,
  directory,
  originalActionItems,
  onKeywordChange,
  onCustomerTypeChange,
  onManagerKeywordChange,
  onSearch,
  onReset,
  onSelectedRowKeysChange,
  onStartCreate,
  onOpenDetail,
  onOpenCustomerCommunication,
  onOpenCustomerContracts,
  onOpenCustomerCivilCases,
  onOpenCustomerIprCases,
  onRunOriginalAction,
  onGoToPage,
  onJumpPageChange,
  onPageSizeChange,
}: CustomerListProps) {
  const amount = (value?: number) => Number(value || 0).toFixed(2);
  const displayDate = (value?: string) => {
    const parsed = dayjs(value);
    return value && parsed.isValid() ? parsed.format("YYYY-M-D") : "—";
  };
  const userLabel = (value: string) => displayChinesePersonName(value, directory);
  const userLabels = (values: unknown) => displayChinesePersonNames(values, directory);
  const canOpenCustomerCommunication = [
    "customer-mine",
    "customer-dept",
    "customer-company",
    "customer-shared",
    "customer-recent-contact",
    "customer-recent-update",
  ].includes(initialView);

  const columns = [
    {
      title: "客户编号",
      dataIndex: "serial_no",
      width: 235,
      align: "center" as const,
      ellipsis: true,
      render: (v: string, r: Customer) => (
        <button
          type="button"
          className="customer-cell-link"
          title={v}
          onClick={() => onOpenDetail(r)}
        >
          <span>{v}</span>
        </button>
      ),
    },
    {
      title: "客户名称",
      dataIndex: "title",
      width: 294,
      align: "center" as const,
      ellipsis: true,
      render: (value: string, r: Customer) => (
        <button type="button" className="customer-cell-link" title={value} onClick={() => onOpenDetail(r)}>
          <span>{value}</span>
        </button>
      ),
    },
    {
      title: "案源人",
      key: "source",
      width: 120,
      align: "center" as const,
      ellipsis: true,
      render: (_: unknown, r: Customer) => userLabel(
        r.data.customer_source_display_name || r.data.customer_source || r.data.source_person || r.owner,
      ),
    },
    {
      title: "客户管理人",
      key: "managers",
      width: 220,
      align: "center" as const,
      ellipsis: true,
      render: (_: unknown, r: Customer) => {
        const managers = userLabels((r.data as any).customer_manager_display_names || r.data.customer_managers || [r.owner]);
        return <span title={managers}>{managers}</span>;
      },
    },
    ...(initialView === "customer-shared" ? [{
      title: "共享接收人",
      key: "sharedRecipients",
      width: 180,
      align: "center" as const,
      ellipsis: true,
      render: (_: unknown, r: Customer) => {
        const recipients = (r.data.shared_with || []).map(userLabel).join("、") || "—";
        return <span title={recipients}>{recipients}</span>;
      },
    }] : []),
    {
      title: "建档日期",
      key: "fileDate",
      width: 115,
      align: "center" as const,
      render: (_: unknown, r: Customer) =>
        displayDate(r.data.file_date || r.created_at),
    },
    {
      title: "最后联系日期",
      key: "lastContact",
      width: 120,
      align: "center" as const,
      render: (_: unknown, r: Customer) => displayDate(r.data.last_contact_at),
    },
    {
      title: "最后修改日期",
      key: "lastModified",
      width: 120,
      align: "center" as const,
      render: (_: unknown, r: Customer) =>
        displayDate(initialView === "customer-recent-update" ? r.updated_at : r.data.last_modified_date || r.updated_at),
    },
    {
      title: "沟通记录",
      key: "communication",
      width: 126,
      align: "center" as const,
      render: (_: unknown, r: Customer) =>
        canOpenCustomerCommunication ? (
          <Button type="link" className="customer-cell-link" onClick={() => onOpenCustomerCommunication(r)}>
            新增沟通记录
          </Button>
        ) : "—",
    },
    {
      title: "联系次数",
      key: "contactCount",
      width: 118,
      align: "center" as const,
      render: (_: unknown, r: Customer) => (
        <Button type="link" className="customer-cell-link" onClick={() => onOpenDetail(r, "contacts")}>
          {r.data.contact_count ?? r.data.notes?.length ?? 0}
        </Button>
      ),
    },
    {
      title: "合同数量",
      key: "contractCount",
      width: 118,
      align: "center" as const,
      render: (_: unknown, r: Customer) => (
        <Button
          type="link"
          className="customer-cell-link"
          onClick={() => onOpenCustomerContracts(r)}
        >
          {r.data.contract_count ?? 0}
        </Button>
      ),
    },
    {
      title: "民事案件数量",
      key: "caseCount",
      width: 120,
      align: "center" as const,
      render: (_: unknown, r: Customer) => (
        <Button
          type="link"
          className="customer-cell-link"
          onClick={() => onOpenCustomerCivilCases(r)}
        >
          {r.data.civil_case_count ?? 0}
        </Button>
      ),
    },
    {
      title: "知识产权案件数量",
      key: "iprCaseCount",
      width: 140,
      align: "center" as const,
      render: (_: unknown, r: Customer) => (
        <Button
          type="link"
          className="customer-cell-link"
          onClick={() => onOpenCustomerIprCases(r)}
        >
          {r.data.ipr_case_count ?? 0}
        </Button>
      ),
    },
    {
      title: (
        <span>
          代理费
          <br />
          待收金额
        </span>
      ),
      key: "agencyFee",
      width: 117,
      align: "center" as const,
      render: (_: unknown, r: Customer) => amount(r.data.agency_fee_due),
    },
    {
      title: (
        <span>
          官费
          <br />
          未到金额
        </span>
      ),
      key: "officialFee",
      width: 118,
      align: "center" as const,
      render: (_: unknown, r: Customer) =>
        amount(r.data.official_fee_unreceived),
    },
    {
      title: "客户状态",
      dataIndex: "status",
      width: 118,
      align: "center" as const,
      render: (v: string) => {
        const status = customerStatusLabel(v);
        const label = ["customer-recycle", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-recent-update"].includes(initialView) && status === "已回收" ? "已删除" : status;
        return <span className={`customer-status customer-status-${v}`}>{label}</span>;
      },
    },
  ];

  const showFooter = !["customer-recycle", "customer-dept", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-public", "customer-shared", "customer-recent-contact", "customer-recent-update"].includes(initialView) || rows.length > 0;

  return (
    <Card
      className="panel customer-list-panel"
      title="客户列表"
      extra={(
        <Dropdown
          trigger={["click"]}
          menu={{
            items: [
              { key: "客户", label: "新建非诉客户" },
              { key: "当事人", label: "新建诉讼客户" },
            ],
            onClick: ({ key }) => onStartCreate(key),
          }}
        >
          <Button type="primary" icon={<PlusOutlined />}>新建客户</Button>
        </Dropdown>
      )}
    >
      <div className="customer-query">
        <label>客户名称</label>
        <Input
          value={keyword}
          onChange={(e) => onKeywordChange(e.target.value)}
          onPressEnter={onSearch}
          allowClear
        />
        <label>客户/当事人</label>
        <Select
          value={customerType}
          onChange={onCustomerTypeChange}
          options={customerTypeOptions}
        />
        <label>客户管理人</label>
        <Input
          disabled={managerLocked}
          value={managerDisplay}
          onChange={(event) => onManagerKeywordChange(event.target.value)}
        />
        <Button type="primary" icon={<SearchOutlined />} onClick={onSearch}>
          查询
        </Button>
        {!isOriginalCustomerList && <Button icon={<ReloadOutlined />} onClick={onReset}>
          重置
        </Button>}
      </div>
      <Table
        className="customer-original-table"
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={rows}
        tableLayout="fixed"
        rowSelection={{
          columnWidth: 44,
          selectedRowKeys,
          onChange: onSelectedRowKeysChange,
        }}
        scroll={{ x: 2100, y: "calc(100dvh - 305px)" }}
        pagination={isOriginalCustomerList ? false : {
          pageSize: 15,
          showSizeChanger: true,
          pageSizeOptions: [15, 30, 50],
          showTotal: (count) => `共 ${count} 条`,
        }}
        locale={{ emptyText: "没有查询到符合条件的记录 。" }}
        rowClassName={(record) => selectedRowKeys.includes(record.id) ? "customer-original-selected" : ""}
        components={isOriginalCustomerList && rows.length > 0 ? {
          body: {
            wrapper: (props: any) => {
              const { children, ...rest } = props;
              return <tbody {...rest}>
                <tr className="customer-total-row customer-total-row-top">
                  <td colSpan={11} />
                  <td className="ant-table-cell customer-amount-cell">{amount(listSummary.agency_fee_due)}</td>
                  <td className="ant-table-cell customer-amount-cell">{amount(listSummary.official_fee_unreceived)}</td>
                  <td />
                </tr>
                {children}
              </tbody>;
            },
          },
        } : undefined}
        summary={["customer-recycle", "customer-dept", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-public", "customer-shared", "customer-recent-contact", "customer-recent-update"].includes(initialView) && rows.length === 0 ? undefined : (data) => (
          <Table.Summary>
            <Table.Summary.Row className="customer-total-row">
              <Table.Summary.Cell index={0} colSpan={11} />
              <Table.Summary.Cell index={11} align="center">
                {amount(isOriginalCustomerList ? listSummary.agency_fee_due : data.reduce((sum, row) => sum + (row.data.agency_fee_due || 0), 0))}
              </Table.Summary.Cell>
              <Table.Summary.Cell index={12} align="center">
                {amount(isOriginalCustomerList ? listSummary.official_fee_unreceived : data.reduce((sum, row) => sum + (row.data.official_fee_unreceived || 0), 0))}
              </Table.Summary.Cell>
              <Table.Summary.Cell index={13} />
            </Table.Summary.Row>
          </Table.Summary>
        )}
      />
      {showFooter && <div className="customer-grid-footer">
        <div className="customer-footer-actions">
          <Checkbox
            checked={rows.length > 0 && selectedRowKeys.length === rows.length}
            indeterminate={selectedRowKeys.length > 0 && selectedRowKeys.length < rows.length}
            onChange={(event) => onSelectedRowKeysChange(event.target.checked ? rows.map((row) => row.id) : [])}
          />
          {isReadOnlyCustomerList && (
            <Button onClick={() => {
              const selected = rows.find((row) => selectedRowKeys.includes(row.id));
              if (selected) void onOpenDetail(selected);
            }}>客户查看</Button>
          )}
          {originalActionItems.length > 0 && (
            <Dropdown
              trigger={["click"]}
              menu={{
                items: originalActionItems,
                onClick: ({ key }) => onRunOriginalAction(key),
              }}
            >
              <Button>更多操作</Button>
            </Dropdown>
          )}
        </div>
        {isOriginalCustomerList && <div className="customer-original-pagination">
          <span>共有{total}条，每页显示：</span>
          <Select
            value={pageSize}
            options={[10, 15, 20, 50, 100, 200].map((value) => ({ value, label: String(value) }))}
            onChange={onPageSizeChange}
          />
          <span>条</span>
          <Button disabled={page === 1} onClick={() => onGoToPage(1)}>«</Button>
          <Button disabled={page === 1} onClick={() => onGoToPage(page - 1)}>‹</Button>
          {customerPageNumbers.map((number) => <Button key={number} type={number === page ? "primary" : "default"} onClick={() => onGoToPage(number)}>{number}</Button>)}
          <Button disabled={page === customerPageCount} onClick={() => onGoToPage(page + 1)}>›</Button>
          {["customer-recycle", "customer-dept", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-recent-update"].includes(initialView) && (
            <Button disabled={page === customerPageCount} onClick={() => onGoToPage(customerPageCount)}>»</Button>
          )}
          <Input value={jumpPage} onChange={(event) => onJumpPageChange(event.target.value.replace(/\D/g, ""))} onPressEnter={() => onGoToPage(Number(jumpPage || page))} />
          <Button onClick={() => onGoToPage(Number(jumpPage || page))}>GO</Button>
        </div>}
      </div>}
    </Card>
  );
}

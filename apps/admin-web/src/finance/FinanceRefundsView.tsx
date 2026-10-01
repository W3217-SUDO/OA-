import { Button, Select, message } from "antd";
import type { TableColumnsType } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import Table from "../components/ResizableTable";
import { refundPageSizeOptions, refundStatusOptions } from "../financeRefundHelpers.mjs";
import type { FinanceFlow } from "./types";

export interface FinanceRefundsViewProps {
  initialView: string;
  isNotRequiredRoute: boolean;
  activeStatus: string;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  groupFilter: string;
  onGroupFilterChange: (group: string) => void;
  selectedRows: number[];
  onSelectedRowsChange: (rows: number[]) => void;
  meta: { page: number; pageSize: number; total: number };
  rows: FinanceFlow[];
  columns: TableColumnsType<FinanceFlow>;
  loading: boolean;
  load: (page: number, pageSize: number, status: string, reset?: boolean, group?: string) => Promise<unknown>;
  exportRows: (selectedOnly: boolean) => Promise<void>;
  onBatchStatusChange: (status: string) => void;
  onOpenBatchStatus: () => void;
  onOpenCreation: () => void;
  statusForRoute: (view: string, fallback: string) => string;
}

export function FinanceRefundsActions(props: FinanceRefundsViewProps) {
  const {
    initialView, isNotRequiredRoute, activeStatus, groupFilter, selectedRows, meta,
    onStatusFilterChange, onGroupFilterChange, onSelectedRowsChange, load, exportRows,
    onBatchStatusChange, onOpenBatchStatus, onOpenCreation, statusForRoute,
  } = props;
  return (
    <>
      <Select
        aria-label="退款业务组筛选"
        value={groupFilter || undefined}
        placeholder="全部业务组"
        allowClear
        options={[
          { label: "律所", value: "lawfirm" },
          { label: "商标", value: "trad" },
        ]}
        onChange={(value) => {
          const nextGroup = value || "";
          onGroupFilterChange(nextGroup);
          void load(1, meta.pageSize, activeStatus, true, nextGroup);
        }}
        style={{ minWidth: 130 }}
      />
      <Select
        aria-label="退款状态筛选"
        value={activeStatus}
        disabled={isNotRequiredRoute}
        options={refundStatusOptions.map((value) => ({ label: value, value }))}
        onChange={(value) => {
          if (isNotRequiredRoute) return;
          onStatusFilterChange(value);
          void load(1, meta.pageSize, value, true, groupFilter);
        }}
        style={{ minWidth: 130 }}
      />
      <Button onClick={() => {
        onStatusFilterChange(isNotRequiredRoute ? "R100" : "全部");
        onGroupFilterChange("");
        onSelectedRowsChange([]);
        void load(1, meta.pageSize, statusForRoute(initialView, ""), true, "");
      }}>
        清空
      </Button>
      <Button onClick={() => void exportRows(false)}>导出全部</Button>
      <Button disabled={!selectedRows.length} onClick={() => void exportRows(true)}>
        导出选中
      </Button>
      <Button onClick={() => {
        if (!selectedRows.length) {
          message.warning("请选择需要修改退费进度的记录");
          return;
        }
        onBatchStatusChange("待审批");
        onOpenBatchStatus();
      }}>
        退费进度修改
      </Button>
      <Button type="primary" icon={<PlusOutlined />} onClick={onOpenCreation}>
        退款申请
      </Button>
    </>
  );
}

export function FinanceRefundsTable(props: FinanceRefundsViewProps) {
  const {
    rows, columns, loading, selectedRows, onSelectedRowsChange, meta, load,
    isNotRequiredRoute, activeStatus, statusFilter, groupFilter,
  } = props;
  const loadPage = (page: number, pageSize: number) => {
    const status = isNotRequiredRoute ? activeStatus : statusFilter;
    void load(page, pageSize, status, true, groupFilter);
  };
  return (
    <Table<FinanceFlow>
      rowKey="id"
      loading={loading}
      size="small"
      columns={columns}
      dataSource={rows}
      rowSelection={{
        selectedRowKeys: selectedRows,
        onChange: (keys) => onSelectedRowsChange(keys as number[]),
      }}
      pagination={{
        current: meta.page,
        pageSize: meta.pageSize,
        total: meta.total,
        showSizeChanger: true,
        pageSizeOptions: refundPageSizeOptions,
        onShowSizeChange: (_current, size) => loadPage(1, size),
        onChange: loadPage,
      }}
      scroll={{ x: 1700 }}
    />
  );
}

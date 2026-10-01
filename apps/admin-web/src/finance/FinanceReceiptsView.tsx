import { Button, message } from "antd";
import type { FormInstance, TableColumnsType } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import Table from "../components/ResizableTable";
import dayjs from "dayjs";
import type { IncomingPaymentFormValues } from "./formTypes";
import type { IncomingPayment } from "./types";

export interface FinanceReceiptsViewProps {
  incoming: IncomingPayment[];
  shownIncoming: IncomingPayment[];
  columns: TableColumnsType<IncomingPayment>;
  selectedRows: number[];
  onSelectedRowsChange: (rows: number[]) => void;
  onOpenAllocation: (payment: IncomingPayment) => void;
  canManage: boolean;
  form: FormInstance<IncomingPaymentFormValues>;
  onOpenRegistration: () => void;
  loading: boolean;
}

export function FinanceReceiptsActions({
  incoming, selectedRows, onOpenAllocation, canManage, form, onOpenRegistration,
}: FinanceReceiptsViewProps) {
  return (
    <>
      <Button
        disabled={selectedRows.length !== 1}
        onClick={() => {
          const selected = incoming.find((row) => row.id === selectedRows[0]);
          if (!selected) {
            message.warning("请选择一笔回款记录");
            return;
          }
          onOpenAllocation(selected);
        }}
      >
        已分配记录
      </Button>
      {canManage && (
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            form.resetFields();
            form.setFieldsValue({ received_date: dayjs() });
            onOpenRegistration();
          }}
        >
          登记银行到账
        </Button>
      )}
    </>
  );
}

export function FinanceReceiptsTable({
  shownIncoming, columns, selectedRows, onSelectedRowsChange, loading,
}: FinanceReceiptsViewProps) {
  return (
    <Table<IncomingPayment>
      rowKey="id"
      loading={loading}
      size="small"
      columns={columns}
      dataSource={shownIncoming}
      scroll={{ x: 1700 }}
      rowSelection={{
        selectedRowKeys: selectedRows,
        onChange: (keys) => onSelectedRowsChange(keys as number[]),
      }}
    />
  );
}

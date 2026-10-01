import { Button } from "antd";
import type { FormInstance, TableColumnsType } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import Table from "../components/ResizableTable";
import type { FinanceFlow } from "./types";

export interface FinanceInvoicesViewProps {
  rows: FinanceFlow[];
  columns: TableColumnsType<FinanceFlow>;
  loading: boolean;
  form: FormInstance;
  loadReference: () => Promise<unknown>;
  onEditTargetChange: (target: FinanceFlow | null) => void;
  onSelectedFeeIdsChange: (ids: number[]) => void;
  onOpen: () => void;
}

export function FinanceInvoicesActions({
  form, loadReference, onEditTargetChange,
  onSelectedFeeIdsChange, onOpen,
}: FinanceInvoicesViewProps) {
  return (
    <Button
      type="primary"
      icon={<PlusOutlined />}
      onClick={() => {
        void (async () => {
          try {
            await loadReference();
          } catch {
            return;
          }
          onEditTargetChange(null);
          onSelectedFeeIdsChange([]);
          form.resetFields();
          form.setFieldsValue({
            invoice_type: "增值税普通发票",
            invoice_content: "法律服务费",
            delivery_method: "电子发票",
          });
          onOpen();
        })();
      }}
    >
      发票申请
    </Button>
  );
}

export function FinanceInvoicesTable({ rows, columns, loading }: Pick<FinanceInvoicesViewProps, "rows" | "columns" | "loading">) {
  return (
    <Table<FinanceFlow>
      rowKey="id"
      loading={loading}
      size="small"
      columns={columns}
      dataSource={rows}
      scroll={{ x: 1650 }}
    />
  );
}

import { Button,Card,Checkbox,Modal,Space,Table,Tag } from "antd";
import type { IprCaseCustomer,IprCaseCustomerCandidate,IprRecord } from "../types";

interface IprCustomersPanelProps {
  detail: IprRecord;
  caseCustomers: IprCaseCustomer[];
  customerOpen: boolean;
  customerCandidates: IprCaseCustomerCandidate[];
  customerSelection: number[];
  primaryCustomerId: number | null;
  onOpenCustomerSelector: () => void;
  onCloseCustomerSelector: () => void;
  onSaveCustomers: () => void;
  onCustomerSelectionChange: (keys: number[]) => void;
  onPrimaryCustomerChange: (id: number) => void;
  onOpenLinkedCustomer: (customer: IprCaseCustomer) => void;
  onOpenLinkedCustomerCases: (customer: IprCaseCustomer) => void;
  onOpenContactSelector: (customer: IprCaseCustomer) => void;
}

export function IprCustomersPanel({
  detail,
  caseCustomers,
  customerOpen,
  customerCandidates,
  customerSelection,
  primaryCustomerId,
  onOpenCustomerSelector,
  onCloseCustomerSelector,
  onSaveCustomers,
  onCustomerSelectionChange,
  onPrimaryCustomerChange,
  onOpenLinkedCustomer,
  onOpenLinkedCustomerCases,
  onOpenContactSelector,
}: IprCustomersPanelProps) {
  return (
    <>
      <Card
        size="small"
        title="案件客户与联系人"
        style={{ marginTop: 16 }}
        extra={
          detail.status === "草稿" ||
          detail.status === "已驳回" ||
          detail.status === "在办" ? (
            <Button size="small" onClick={onOpenCustomerSelector}>
              维护案件客户
            </Button>
          ) : null
        }
      >
        <Table
          rowKey="customer_id"
          size="small"
          pagination={false}
          locale={{ emptyText: "暂未关联案件客户" }}
          dataSource={caseCustomers}
          columns={[
            {
              title: "客户编号",
              dataIndex: "customer_no",
              width: 150,
              render: (value, row) => (
                <Button
                  type="link"
                  size="small"
                  onClick={() => onOpenLinkedCustomer(row)}
                >
                  {value || "—"}
                </Button>
              ),
            },
            {
              title: "客户名称",
              dataIndex: "name",
              render: (value, row) => (
                <Space>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => onOpenLinkedCustomerCases(row)}
                  >
                    {value || "—"}
                  </Button>
                  {row.is_primary ? <Tag color="blue">主客户</Tag> : null}
                </Space>
              ),
            },
            { title: "状态", dataIndex: "status", width: 110 },
            {
              title: "联系人",
              width: 130,
              render: (_, row) => (
                <Button
                  type="link"
                  size="small"
                  onClick={() => onOpenContactSelector(row)}
                >
                  维护联系人
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={customerOpen}
        title="维护案件客户"
        onCancel={onCloseCustomerSelector}
        onOk={onSaveCustomers}
        okText="保存关联"
        width={760}
      >
        <p style={{ color: "#666" }}>
          案件可以关联多个客户；必须在已选客户中指定一个主客户，主客户会同步用于案件概览及后续关联流程。
        </p>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={customerCandidates}
          rowSelection={{
            selectedRowKeys: customerSelection,
            onChange: (keys) => {
              const selected = keys.map(Number);
              onCustomerSelectionChange(selected);
            },
          }}
          columns={[
            { title: "客户编号", dataIndex: "customer_no", width: 150 },
            { title: "客户名称", dataIndex: "name" },
            { title: "状态", dataIndex: "status", width: 110 },
            {
              title: "主客户",
              width: 110,
              render: (_, row) => (
                <Checkbox
                  checked={primaryCustomerId === row.id}
                  disabled={!customerSelection.includes(row.id)}
                  onChange={() => onPrimaryCustomerChange(row.id)}
                >
                  主客户
                </Checkbox>
              ),
            },
          ]}
        />
      </Modal>
    </>
  );
}

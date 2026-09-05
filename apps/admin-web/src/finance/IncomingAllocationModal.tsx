import { Alert,Button,Checkbox,Descriptions,Input,InputNumber,Modal,Select,Table } from "antd";
import { money } from "./constants";
import type { AllocationCandidate } from "./types";

interface IncomingAllocationModalProps {
  open: boolean;
  allocateTarget: any;
  allocationValidationError: string;
  allocationKeyword: string;
  allocationStage: string;
  allocationFeeType: string;
  allocationLoading: boolean;
  allocationCandidates: AllocationCandidate[];
  filteredAllocationCandidates: AllocationCandidate[];
  selectedAllocationKeys: (string | number)[];
  allocationAmounts: Record<string, number>;
  allocationComment: string;
  onOk: () => void;
  onCancel: () => void;
  onKeywordChange: (value: string) => void;
  onStageChange: (value: string) => void;
  onFeeTypeChange: (value: string) => void;
  onClearFilters: () => void;
  onSelectedKeysChange: React.Dispatch<React.SetStateAction<(string | number)[]>>;
  onAmountChange: (key: string, value: number) => void;
  onCommentChange: (value: string) => void;
  onOpenCaseDetail: (caseNo: unknown) => void;
}

export function IncomingAllocationModal({
  open,
  allocateTarget,
  allocationValidationError,
  allocationKeyword,
  allocationStage,
  allocationFeeType,
  allocationLoading,
  allocationCandidates,
  filteredAllocationCandidates,
  selectedAllocationKeys,
  allocationAmounts,
  allocationComment,
  onOk,
  onCancel,
  onKeywordChange,
  onStageChange,
  onFeeTypeChange,
  onClearFilters,
  onSelectedKeysChange,
  onAmountChange,
  onCommentChange,
  onOpenCaseDetail,
}: IncomingAllocationModalProps) {
  const stageOptions = Array.from(
    new Set(allocationCandidates.map((row) => row.case_stage))
  )
    .filter(Boolean)
    .map((value) => ({ value, label: value }));

  const feeTypeOptions = Array.from(
    new Set(allocationCandidates.map((row) => row.fee_type))
  )
    .filter(Boolean)
    .map((value) => ({ value, label: value }));

  const columns = [
    { title: "原告", dataIndex: "plaintiff", width: 170, ellipsis: true },
    { title: "被告", dataIndex: "defendant", width: 210, ellipsis: true },
    {
      title: "案号",
      dataIndex: "case_no",
      width: 135,
      render: (value: unknown) =>
        value ? (
          <Button type="link" onClick={() => onOpenCaseDetail(value)}>
            {String(value)}
          </Button>
        ) : (
          "—"
        ),
    },
    { title: "案件阶段", dataIndex: "case_stage", width: 105 },
    { title: "提交日期", dataIndex: "submission_date", width: 100 },
    { title: "费用类型", dataIndex: "fee_type", width: 125 },
    { title: "总额", dataIndex: "total_amount", width: 90, render: money },
    { title: "已回", dataIndex: "received_amount", width: 90, render: money },
    { title: "待回", dataIndex: "remaining_amount", width: 90, render: money },
    {
      title: "本次回款",
      key: "allocation_amount",
      width: 125,
      render: (_: unknown, row: AllocationCandidate) => (
        <InputNumber
          aria-label={`本次回款-${row.case_no || row.contract_no}-${row.fee_type}`}
          min={0.01}
          max={row.remaining_amount}
          precision={2}
          value={allocationAmounts[row.key]}
          onChange={(value) => {
            onAmountChange(row.key, Number(value || 0));
            if (value && !selectedAllocationKeys.includes(row.key)) {
              onSelectedKeysChange((current) => [...current, row.key]);
            }
          }}
        />
      ),
    },
    {
      title: "全部回款",
      key: "all",
      width: 80,
      align: "center" as const,
      render: (_: unknown, row: AllocationCandidate) => (
        <Checkbox
          checked={
            selectedAllocationKeys.includes(row.key) &&
            Number(allocationAmounts[row.key]) === Number(row.remaining_amount)
          }
          onChange={(event) => {
            onAmountChange(row.key, row.remaining_amount);
            onSelectedKeysChange((current) => event.target.checked
                ? Array.from(new Set([...current, row.key]))
                : current.filter((key) => key !== row.key)
            );
          }}
        />
      ),
    },
  ];

  return (
    <Modal
      width="calc(100vw - 48px)"
      style={{ top: 24 }}
      rootClassName="finance-allocation-modal"
      open={open}
      title={`分配回款：${allocateTarget?.receipt_no || ""}`}
      okText="确认分配"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      {allocationValidationError && (
        <Alert
          type="error"
          showIcon
          message={allocationValidationError}
          style={{ marginBottom: 12 }}
        />
      )}
      <section className="finance-allocation-section">
        <div className="finance-allocation-heading">回款信息</div>
        <Descriptions size="small" column={5} colon={false}>
          <Descriptions.Item label="回款单位">
            {allocateTarget?.payer_name || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="到账日期">
            {allocateTarget?.received_date || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="银行单号">
            {allocateTarget?.bank_reference || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="到账金额">
            {money(Number(allocateTarget?.amount || 0))}
          </Descriptions.Item>
          <Descriptions.Item label="已分配">
            {money(Number(allocateTarget?.allocated_amount || 0))}
          </Descriptions.Item>
          <Descriptions.Item label="客户名称">
            {allocateTarget?.claimed_customer || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="未分配余额">
            {money(Number(allocateTarget?.remaining_amount || 0))}
          </Descriptions.Item>
          <Descriptions.Item label="备注" span={3}>
            {allocateTarget?.remark || "—"}
          </Descriptions.Item>
        </Descriptions>
      </section>
      <section className="finance-allocation-section">
        <div className="finance-allocation-heading">案件费用明细</div>
        <div className="finance-allocation-filters">
          <label>
            客户名称
            <Input value={allocateTarget?.claimed_customer || ""} disabled />
          </label>
          <label>
            关键字
            <Input
              value={allocationKeyword}
              onChange={(event) => onKeywordChange(event.target.value)}
              placeholder="案号、原告、被告、案件名称"
              allowClear
            />
          </label>
          <label>
            案件阶段
            <Select
              allowClear
              value={allocationStage || undefined}
              onChange={(value) => onStageChange(value || "")}
              options={stageOptions}
            />
          </label>
          <label>
            费用类型
            <Select
              allowClear
              value={allocationFeeType || undefined}
              onChange={(value) => onFeeTypeChange(value || "")}
              options={feeTypeOptions}
            />
          </label>
          <Button type="primary" onClick={() => undefined}>
            查询
          </Button>
          <Button onClick={onClearFilters}>清空</Button>
        </div>
        <Table<AllocationCandidate>
          className="finance-allocation-table"
          loading={allocationLoading}
          size="small"
          bordered
          rowKey="key"
          scroll={{ x: 1370, y: 390 }}
          pagination={{
            pageSize: 20,
            showSizeChanger: false,
            showTotal: (total) => `共 ${total} 条`,
          }}
          dataSource={filteredAllocationCandidates}
          locale={{ emptyText: "该客户名下暂无未回款案件费用" }}
          rowSelection={{
            selectedRowKeys: selectedAllocationKeys,
            preserveSelectedRowKeys: true,
            onChange: (keys) => onSelectedKeysChange(keys.map((key) => String(key))),
          }}
          columns={columns}
        />
        <div className="finance-allocation-comment">
          <span>分配说明</span>
          <Input
            value={allocationComment}
            onChange={(event) => onCommentChange(event.target.value)}
            placeholder="可选"
          />
        </div>
      </section>
    </Modal>
  );
}

export default IncomingAllocationModal;

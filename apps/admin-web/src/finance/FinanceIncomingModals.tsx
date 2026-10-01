import { Alert, AutoComplete, DatePicker, Form, Input, InputNumber, Modal, Select } from "antd";
import type { FormInstance } from "antd";
import { money } from "./constants";
import type { IncomingClaimFormValues, IncomingPaymentFormValues } from "./formTypes";
import type { Fee, IncomingPayment } from "./types";

export interface IncomingRegistrationModalProps {
  open: boolean;
  form: FormInstance<IncomingPaymentFormValues>;
  customers: Fee[];
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function IncomingRegistrationModal({
  open: incomingOpen,
  form: incomingForm,
  customers,
  onSubmit: createIncoming,
  onClose,
}: IncomingRegistrationModalProps) {
  return (
      <Modal
        open={incomingOpen}
        title="登记银行到账"
        okText="保存为待认领"
        cancelText="取消"
        onOk={createIncoming}
        onCancel={onClose}
      >
        <Alert
          type="info"
          showIcon
          title="银行到账先登记为待认领，不能直接计入合同或案件。"
          style={{ marginBottom: 16 }}
        />
        <Form form={incomingForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              label="到账日期"
              name="received_date"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="到账金额"
              name="amount"
              rules={[{ required: true }]}
            >
              <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item
            label="付款单位/账户名"
            name="payer_name"
            rules={[{ required: true, min: 2 }]}
          >
            <AutoComplete
              allowClear
              placeholder="输入回款单位，或从系统客户中选择"
              options={customers.map((customer) => ({
                value: customer.title,
                label: customer.serial_no
                  ? `${customer.title}｜${customer.serial_no}`
                  : customer.title,
              }))}
              filterOption={(inputValue, option) =>
                String(option?.label || "")
                  .toLowerCase()
                  .includes(inputValue.trim().toLowerCase())
              }
            />
          </Form.Item>
          <Form.Item
            label="银行流水号"
            name="bank_reference"
            rules={[{ required: true, min: 2 }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="银行摘要/备注" name="remark">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
  );
}

export interface IncomingClaimModalProps {
  target: IncomingPayment | null;
  form: FormInstance<IncomingClaimFormValues>;
  customers: Array<{ id: number; title: string; serial_no: string }>;
  loading: boolean;
  onSearch: (keyword: string) => Promise<void>;
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function IncomingClaimModal({
  target: claimTarget,
  form: claimForm,
  customers: claimCustomers,
  loading: claimCustomersLoading,
  onSearch: searchClaimCustomers,
  onSubmit: claimIncoming,
  onClose,
}: IncomingClaimModalProps) {
  return (
      <Modal
        width={760}
        rootClassName="finance-claim-modal"
        open={Boolean(claimTarget)}
        title="回款领取"
        okText="领取"
        cancelText="取消"
        onOk={claimIncoming}
        onCancel={onClose}
      >
        <div className="finance-claim-tip">
          温馨提示：请根据回款单位匹配系统客户，认领前核对流水号、金额和银行单号。
        </div>
        <Form form={claimForm} layout="horizontal" labelCol={{ span: 5 }} wrapperCol={{ span: 17 }}>
          <Form.Item label="回款流水号">
            <Input value={claimTarget?.receipt_no || ""} readOnly />
          </Form.Item>
          <Form.Item label="回款单位">
            <Input value={claimTarget?.payer_name || ""} readOnly />
          </Form.Item>
          <Form.Item
            label="客户名称"
            name="customer"
            rules={[{ required: true, message: "请选择系统客户" }]}
          >
            <Select
              showSearch
              filterOption={false}
              loading={claimCustomersLoading}
              onSearch={(keyword) => void searchClaimCustomers(keyword)}
              placeholder="请选择客户"
              options={claimCustomers.map((x) => ({
                value: x.title,
                label: x.serial_no ? `${x.title}｜${x.serial_no}` : x.title,
              }))}
              notFoundContent={claimCustomersLoading ? "正在查询系统客户..." : "没有匹配的系统客户"}
            />
          </Form.Item>
          <Form.Item label="回款时间">
            <Input value={claimTarget?.received_date || ""} readOnly />
          </Form.Item>
          <Form.Item label="回款金额">
            <Input value={claimTarget?.amount == null ? "无权限" : money(claimTarget.amount)} readOnly />
          </Form.Item>
          <Form.Item label="回款方式">
            <Input value={claimTarget?.bank_source || "—"} readOnly />
          </Form.Item>
          <Form.Item label="银行单号">
            <Input value={claimTarget?.bank_reference || ""} readOnly />
          </Form.Item>
          <Form.Item label="合同编号">
            <Input value={claimTarget?.contract_no || ""} readOnly />
          </Form.Item>
          <Form.Item label="登记备注">
            <Input.TextArea value={claimTarget?.remark || ""} rows={2} readOnly />
          </Form.Item>
          <Form.Item label="领取备注" name="comment">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
  );
}

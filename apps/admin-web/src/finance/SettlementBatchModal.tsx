import { Alert, Form, Input, InputNumber, Modal, Select } from "antd";
import type { FormInstance } from "antd";
import type { SettlementBatchFormValues } from "./formTypes";
import type { FinancePersonOption } from "./types";

export interface SettlementBatchModalProps {
  open: boolean;
  loading: boolean;
  selectedCaseCount: number;
  form: FormInstance<SettlementBatchFormValues>;
  financePeople: FinancePersonOption[];
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function SettlementBatchModal({
  open: settlementBatchOpen,
  loading: settlementActionLoading,
  selectedCaseCount,
  form: settlementBatchForm,
  financePeople,
  onSubmit: submitSettlementBatch,
  onClose,
}: SettlementBatchModalProps) {
  return (
      <Modal
        width={640}
        open={settlementBatchOpen}
        title="批量修改案件信息"
        okText="保存修改"
        cancelText="取消"
        confirmLoading={settlementActionLoading}
        onOk={submitSettlementBatch}
        onCancel={onClose}
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          title={`将修改已选费用关联的 ${selectedCaseCount} 个案件（仅填写的字段会被修改）`}
          style={{ marginBottom: 16 }}
        />
        <Form form={settlementBatchForm} layout="vertical">
          <div className="form-grid">
            <Form.Item label="开庭律师" name="hearing_lawyer">
              <Select
                showSearch
                optionFilterProp="label"
                allowClear
                placeholder="不修改请留空"
                options={financePeople.map((person) => ({ value: person.username, label: person.label }))}
              />
            </Form.Item>
            <Form.Item label="律师助理" name="assistant">
              <Select
                showSearch
                optionFilterProp="label"
                allowClear
                placeholder="不修改请留空"
                options={financePeople.map((person) => ({ value: person.username, label: person.label }))}
              />
            </Form.Item>
          </div>
          <Form.Item label="经办律师（多人用逗号分隔）" name="handling_lawyers">
            <Input placeholder="不修改请留空，例如：张律师，李律师" />
          </Form.Item>
          <Form.Item label="案源人" name="source_lawyer">
            <Select
              showSearch
              optionFilterProp="label"
              allowClear
              placeholder="不修改请留空"
              options={financePeople.map((person) => ({ value: person.username, label: person.label }))}
            />
          </Form.Item>
          <div className="form-grid">
            <Form.Item label="诉讼标的（元）" name="litigation_amount">
              <InputNumber min={0} precision={2} style={{ width: "100%" }} placeholder="不修改请留空" />
            </Form.Item>
            <Form.Item label="案件阶段" name="case_stage">
              <Input placeholder="不修改请留空" />
            </Form.Item>
          </div>
          <Form.Item label="修改说明" name="comment">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
  );
}

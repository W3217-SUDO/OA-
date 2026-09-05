import { Modal, Steps, Alert, Form, Descriptions, Select, Input, Button } from "antd";
import type { Contract, ResolvedClueContract } from "./types";

interface BatchCaseConversionProps {
  open: boolean;
  selectedClues: number[];
  resolvedClueContracts: ResolvedClueContract[];
  contractOptions: Contract[];
  batchStep: number;
  batchForm: any;
  systemPersonOptions: { value: string; label: string }[];
  onOk: () => void;
  onCancel: () => void;
  onBindContract: () => void;
}

export default function BatchCaseConversion({
  open,
  selectedClues,
  resolvedClueContracts,
  contractOptions,
  batchStep,
  batchForm,
  systemPersonOptions,
  onOk,
  onCancel,
  onBindContract,
}: BatchCaseConversionProps) {
  return (
    <Modal
      open={open}
      title={`已取证线索生成案件（已选 ${selectedClues.length} 条）`}
      okText={batchStep === 0 ? "下一步" : "生成案件"}
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Steps current={batchStep} size="small" items={[{ title: "基本信息" }, { title: "生成结果" }]} style={{ marginBottom: 20 }} />
      <Alert
        type="info"
        showIcon
        title="合同由线索来源调查任务自动绑定；每条已取证线索生成一个新案待分配案件。"
        style={{ marginBottom: 15 }}
      />
      <Form form={batchForm} layout="vertical">
        {batchStep === 0 && <>
          <Descriptions size="small" bordered column={1} items={resolvedClueContracts.map((item) => ({ key: item.clue_id, label: `${item.clue_no || "线索"}｜${item.customer || ""}`, children: item.contract ? `${item.contract.serial_no}｜${item.contract.title}` : item.error || "未解析到合同" }))} />
          {resolvedClueContracts.some((item) => !item.contract) && (
            selectedClues.length === 1 && contractOptions.length > 0 ? (
              <>
                <Form.Item
                  label="补充来源任务合同（可选）"
                  name="source_contract_record_id"
                  style={{ marginTop: 16 }}
                >
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder="仅列出该客户可用合同"
                    options={contractOptions.map((contract) => ({
                      value: contract.id,
                      label: `${contract.serial_no}｜${contract.title}`,
                    }))}
                  />
                </Form.Item>
                <Button onClick={onBindContract}>
                  绑定并自动带入
                </Button>
              </>
            ) : (
              <Alert
                type="info"
                showIcon
                message="来源调查任务未自动关联合同"
                description="本次可继续生成案件；案件将保留客户和线索关联，合同关联可在后续补全。"
                style={{ marginTop: 16 }}
              />
            )
          )}
          <Alert type="info" showIcon title="案件名称默认由客户名称、案由和线索店铺/事项名称组成；调查员默认从线索带入。" style={{ marginTop: 16 }} />
          <Form.Item label="客户诉讼地位" name="client_position" rules={[{ required: true }]} style={{ marginTop: 16 }}>
            <Select options={["原告", "被告", "第三人", "申请人", "被申请人"].map((v) => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item label="案由" name="cause_or_charge" rules={[{ required: true, message: "请填写案由" }]}>
            <Input />
          </Form.Item>
          <Form.Item label="案件阶段" name="case_phase" rules={[{ required: true }]}>
            <Select options={["等待公证书", "新案待分配", "文书准备"].map((v) => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item label="经办律师" name="handling_lawyer" rules={[{ required: true, message: "请选择经办律师" }]}>
            <Select showSearch optionFilterProp="label" options={systemPersonOptions} placeholder="请选择系统人员" />
          </Form.Item>
          <Form.Item label="律师助理" name="assistant" rules={[{ required: true, message: "请选择律师助理" }]}>
            <Select allowClear showSearch optionFilterProp="label" options={systemPersonOptions} placeholder="请选择系统人员" />
          </Form.Item>
          <Form.Item label="案件类型" name="case_type">
            <Select
              options={["民事案件", "刑事案件", "行政案件", "仲裁案件"].map(
                (v) => ({ value: v, label: v }),
              )}
            />
          </Form.Item>
          <Form.Item label="拟管辖法院" name="court">
            <Input />
          </Form.Item>
        </>}
        {batchStep === 1 && <Descriptions size="small" bordered column={1} items={[{ key: "status", label: "生成后案件阶段", children: batchForm.getFieldValue("case_phase") || "等待公证书" }, { key: "result", label: "关联规则", children: "客户、合同、线索及来源任务信息将自动带入案件" }]} />}
      </Form>
    </Modal>
  );
}

import { Modal, Form, Input, Select } from "antd";
import type { ModuleKey, PersonOption } from "./types";
import { moduleMeta } from "./constants";

interface GenericCreateModalProps {
  open: boolean;
  createForm: any;
  systemPersonOptions: PersonOption[];
  tab: ModuleKey;
  onOk: () => void;
  onCancel: () => void;
}

export default function GenericCreateModal({
  open,
  createForm,
  systemPersonOptions,
  tab,
  onOk,
  onCancel,
}: GenericCreateModalProps) {
  const meta = moduleMeta[tab];

  return (
    <Modal
      open={open}
      title={`新增${meta.title}`}
      okText="保存"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={createForm} layout="vertical">
        <div className="form-grid">
          <Form.Item
            label="业务编号"
            name="serial_no"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true }]}>
            <Select
              options={meta.statuses.map((v) => ({ value: v, label: v }))}
            />
          </Form.Item>
          <Form.Item
            className="span-2"
            label="标题/事项"
            name="title"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="客户" name="customer">
            <Input />
          </Form.Item>
          <Form.Item label="负责人" name="owner">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={systemPersonOptions}
            />
          </Form.Item>
          {tab === "clue" && (
            <>
              <Form.Item label="调查平台" name="platform">
                <Input />
              </Form.Item>
              <Form.Item
                label="侵权产品"
                name="product"
                rules={[
                  { required: true, message: "不同产品需分别创建线索" },
                ]}
              >
                <Input />
              </Form.Item>
            </>
          )}
          {tab === "evidence" && (
            <Form.Item label="材料来源" name="source">
              <Input />
            </Form.Item>
          )}
          <Form.Item className="span-2" label="说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
}

import { Modal, Form, Input, Select, DatePicker, Checkbox } from "antd";
import dayjs from "dayjs";
import type { PersonOption } from "./types";

interface InvestigationCreateModalProps {
  open: boolean;
  createForm: any;
  systemPersonOptions: PersonOption[];
  onOk: () => void;
  onCancel: () => void;
}

export default function InvestigationCreateModal({
  open,
  createForm,
  systemPersonOptions,
  onOk,
  onCancel,
}: InvestigationCreateModalProps) {
  return (
    <Modal
      open={open}
      title="新建调查任务"
      okText="保存调查任务"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={createForm} layout="vertical">
        <div className="form-grid">
          <Form.Item
            label="调查编号"
            name="serial_no"
            rules={[{ required: true, message: "请填写调查编号" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="负责人/调查员"
            name="owner"
            rules={[{ required: true, message: "请填写负责人" }]}
          >
            <Select showSearch optionFilterProp="label" options={systemPersonOptions} />
          </Form.Item>
          <Form.Item
            className="span-2"
            label="标题/事项"
            name="title"
            rules={[{ required: true, min: 2, message: "调查事项至少 2 个字符" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="权利人/客户" name="customer">
            <Input />
          </Form.Item>
          <Form.Item label="案源人" name="source_owner">
            <Select allowClear showSearch optionFilterProp="label" options={systemPersonOptions} />
          </Form.Item>
          <Form.Item
            label="调查区域"
            name="region"
            rules={[{ required: true, message: "请填写调查区域" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="权利类型"
            name="right_type"
            rules={[{ required: true, message: "请选择权利类型" }]}
          >
            <Select
              options={["商标", "专利", "著作权", "不正当竞争"].map(
                (value) => ({ value, label: value }),
              )}
            />
          </Form.Item>
          <Form.Item
            label="授权开始日期"
            name="authorized_from"
            rules={[{ required: true, message: "请选择授权开始日期" }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            label="授权结束日期"
            name="authorized_to"
            dependencies={["authorized_from"]}
            rules={[
              { required: true, message: "请选择授权结束日期" },
              {
                validator: (_, value) => {
                  const start = createForm.getFieldValue("authorized_from");
                  return !start ||
                    !value ||
                    !dayjs(value).isBefore(dayjs(start), "day")
                    ? Promise.resolve()
                    : Promise.reject(
                        new Error("授权结束日期不能早于开始日期"),
                      );
                },
              },
            ]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="customer_review" valuePropName="checked">
            <Checkbox>线索需要客户审核</Checkbox>
          </Form.Item>
          <Form.Item className="span-2" label="说明" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
}

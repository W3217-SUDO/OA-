import { Form, Input, Modal, Select } from "antd";
import type { FormInstance } from "antd";
import type { SealAsset } from "./types";
import { sealTypes } from "./constants";

interface SealAssetModalProps {
  open: boolean;
  editAsset: SealAsset | null;
  form: FormInstance;
  submitting: boolean;
  onOk: () => void;
  onCancel: () => void;
}

export function SealAssetModal({
  open,
  editAsset,
  form,
  submitting,
  onOk,
  onCancel,
}: SealAssetModalProps) {
  return (
    <Modal
      open={open}
      title={editAsset ? "维护印章资料" : "新增印章入库"}
      okText="保存"
      cancelText="取消"
      confirmLoading={submitting}
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={form} layout="vertical">
        <Form.Item label="印章编号" name="code" rules={[{ required: true }]}>
          <Input disabled={Boolean(editAsset)} />
        </Form.Item>
        <Form.Item label="印章名称" name="name" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <div className="seal-form-grid">
          <Form.Item
            label="印章类别"
            name="seal_type"
            rules={[{ required: true }]}
          >
            <Select
              options={sealTypes.map((x) => ({ value: x, label: x }))}
            />
          </Form.Item>
          <Form.Item
            label="保管人"
            name="custodian"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="存放位置" name="location">
            <Input />
          </Form.Item>
          {editAsset && (
            <Form.Item label="状态" name="status">
              <Select
                options={["可用", "停用", "维修", "遗失"].map((x) => ({
                  value: x,
                  label: x,
                }))}
              />
            </Form.Item>
          )}
        </div>
        <Form.Item label="备注" name="remark">
          <Input.TextArea rows={2} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

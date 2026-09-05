import { Modal, Form, Input, Select, Radio, DatePicker } from "antd";
import type { Row, PersonOption } from "./types";
import { CLUE_INFRINGEMENT_METHOD_OPTIONS, CLUE_SALES_CHANNEL_OPTIONS } from "./constants";

interface EditRecordModalProps {
  open: boolean;
  editTarget: Row | null;
  editForm: any;
  systemPersonOptions: PersonOption[];
  onOk: () => void;
  onCancel: () => void;
}

export default function EditRecordModal({
  open,
  editTarget,
  editForm,
  systemPersonOptions,
  onOk,
  onCancel,
}: EditRecordModalProps) {
  return (
    <Modal
      open={open}
      title={`修改调查记录：${editTarget?.serial_no || ""}`}
      okText="保存修改"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={editForm} layout="vertical">
        <div className="form-grid">
          <Form.Item
            label="标题/事项"
            name="title"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="权利人/客户" name="customer">
            <Input />
          </Form.Item>
          <Form.Item
            label="负责人/调查员（请通过分配入口变更）"
            name="owner"
            rules={[{ required: true }]}
          >
            <Select disabled options={systemPersonOptions} />
          </Form.Item>
          <Form.Item label="调查区域" name="region">
            <Input />
          </Form.Item>
          <Form.Item label="权利类型" name="right_type">
            <Select
              allowClear
              options={["商标", "专利", "著作权", "不正当竞争"].map(
                (value) => ({ value, label: value }),
              )}
            />
          </Form.Item>
          {editTarget?.module === "clue" && (
            <>
              <Form.Item label="侵权方式" name="infringement_method">
                <Select
                  allowClear
                  options={CLUE_INFRINGEMENT_METHOD_OPTIONS.map(
                    (value) => ({ value, label: value }),
                  )}
                />
              </Form.Item>
              <Form.Item label="销售渠道" name="sales_channel">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  options={CLUE_SALES_CHANNEL_OPTIONS.map((value) => ({
                    value,
                    label: value,
                  }))}
                />
              </Form.Item>
              <Form.Item label="侵权产品" name="product">
                <Input />
              </Form.Item>
              <Form.Item label="店铺链接" name="store_url">
                <Input />
              </Form.Item>
              <Form.Item label="店铺名称" name="shop_name">
                <Input />
              </Form.Item>
              <Form.Item label="店铺Id" name="shop_id">
                <Input />
              </Form.Item>
              <Form.Item label="有无产品" name="has_product">
                <Radio.Group
                  options={[
                    { value: true, label: "有" },
                    { value: false, label: "无" },
                  ]}
                />
              </Form.Item>
              <Form.Item label="来源" name="source">
                <Input />
              </Form.Item>
              <Form.Item label="调查地址" name="address">
                <Input />
              </Form.Item>
              <Form.Item label="调查日期" name="investigated_at">
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item label="生产商" name="producer">
                <Input />
              </Form.Item>
              <Form.Item label="主体信息" name="indictee">
                <Input />
              </Form.Item>
              <Form.Item label="调查辅助" name="investigation_assistant">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  options={systemPersonOptions}
                />
              </Form.Item>
            </>
          )}
          {editTarget?.module === "task" && (
            <>
              <Form.Item label="截止日期" name="deadline">
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item label="优先级" name="priority">
                <Select
                  options={["普通", "紧急", "特急"].map((value) => ({
                    value,
                    label: value,
                  }))}
                />
              </Form.Item>
            </>
          )}
        </div>
        <Form.Item label="说明" name="description">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

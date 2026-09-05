import { Drawer, Form, Alert, Input, Select, Radio, DatePicker, Button, Space, Typography } from "antd";
import { CLUE_INFRINGEMENT_METHOD_OPTIONS, CLUE_SALES_CHANNEL_OPTIONS } from "./constants";
import type { PersonOption } from "./types";

interface ClueCreateDrawerProps {
  open: boolean;
  createForm: any;
  systemPersonOptions: { value: string; label: string }[];
  clueFiles: File[];
  onClueFilesChange: (files: File[]) => void;
  onSave: () => void;
  onSubmit: () => void;
  onClose: () => void;
}

export default function ClueCreateDrawer({
  open,
  createForm,
  systemPersonOptions,
  clueFiles,
  onClueFilesChange,
  onSave,
  onSubmit,
  onClose,
}: ClueCreateDrawerProps) {
  return (
    <Drawer
      open={open}
      title="线索报备"
      placement="right"
      width={620}
      footer={
        <Space>
          <Button onClick={onSave}>暂存线索</Button>
          <Button type="primary" onClick={onSubmit}>
            提交审批
          </Button>
        </Space>
      }
      onClose={onClose}
    >
      <Form form={createForm} layout="vertical">
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="提交审批前请确认主体信息完整"
        />
        <div className="form-grid">
          <Form.Item
            label="线索编号"
            name="serial_no"
          >
            <Input disabled />
          </Form.Item>
          <Form.Item label="调查员" name="owner" rules={[{ required: true }]}>
            <Select
              disabled
              showSearch
              optionFilterProp="label"
              options={systemPersonOptions}
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
            <Input disabled />
          </Form.Item>
          <Form.Item label="侵权方式" name="infringement_method">
            <Select
              allowClear
              options={CLUE_INFRINGEMENT_METHOD_OPTIONS.map((value) => ({
                value,
                label: value,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="销售渠道"
            name="sales_channel"
            rules={[{ required: true, message: "请选择销售渠道" }]}
          >
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
          <Form.Item
            label="侵权产品"
            name="product"
            rules={[{ required: true, message: "不同产品需分别创建线索" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="店铺链接" name="store_url">
            <Input placeholder="请输入店铺链接" />
          </Form.Item>
          <Form.Item label="店铺名称" name="shop_name">
            <Input placeholder="请输入店铺名称" />
          </Form.Item>
          <Form.Item label="店铺Id" name="shop_id">
            <Input placeholder="淘宝店铺Id为掌柜名称，拼多多店铺Id为一串数字" />
          </Form.Item>
          <Form.Item label="有无产品" name="has_product">
            <Radio.Group
              options={[
                { value: true, label: "有" },
                { value: false, label: "无" },
              ]}
            />
          </Form.Item>
          <Form.Item label="产品链接" name="product_url">
            <Input placeholder="请输入产品链接" />
          </Form.Item>
          <Form.Item label="规模" name="sale_num">
            <Input placeholder="请输入规模" />
          </Form.Item>
          <Form.Item label="调查地址" name="address">
            <Input placeholder="请输入调查地址" />
          </Form.Item>
          <Form.Item label="调查日期" name="investigated_at">
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="生产商" name="producer">
            <Input placeholder="生产商" />
          </Form.Item>
          <Form.Item label="主体信息" name="indictee">
            <Input placeholder="主体信息" />
          </Form.Item>
          <Form.Item label="调查辅助员" name="investigation_assistant">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="请选择系统人员"
              options={systemPersonOptions}
            />
          </Form.Item>
          <Form.Item label="权利类型" name="right_type">
            <Select
              options={["商标", "专利", "著作权", "不正当竞争"].map(
                (value) => ({ value, label: value }),
              )}
            />
          </Form.Item>
          <Form.Item label="案源人" name="source_owner">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={systemPersonOptions}
            />
          </Form.Item>
          <Form.Item label="调查区域" name="region">
            <Input />
          </Form.Item>
          <Form.Item label="来源" name="source">
            <Input />
          </Form.Item>
          <Form.Item label="附件">
            <input
              multiple
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.zip,.rar"
              onChange={(event) =>
                onClueFilesChange(Array.from(event.target.files || []))
              }
            />
            <Typography.Text type="secondary">
              {clueFiles.length
                ? `已选择 ${clueFiles.length} 个文件`
                : "可上传调查线索相关材料"}
            </Typography.Text>
          </Form.Item>
          <Form.Item className="span-2" label="备注" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </div>
      </Form>
    </Drawer>
  );
}

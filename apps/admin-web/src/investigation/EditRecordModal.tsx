import { Modal, Form, Input, Select, Radio, DatePicker, Cascader, Space } from "antd";
import type { Row, PersonOption, Contract } from "./types";
import { INVESTIGATION_REGION_GROUPS } from "../investigationRegionOptions.mjs";
import { CLUE_INFRINGEMENT_METHOD_OPTIONS, CLUE_SALES_CHANNEL_OPTIONS } from "./constants";

interface EditRecordModalProps {
  open: boolean;
  editTarget: Row | null;
  editForm: any;
  systemPersonOptions: PersonOption[];
  contracts?: Contract[];
  onOk: () => void;
  onCancel: () => void;
}

export default function EditRecordModal({
  open,
  editTarget,
  editForm,
  systemPersonOptions,
  contracts = [],
  onOk,
  onCancel,
}: EditRecordModalProps) {
  const scope = Form.useWatch("authorization_scope_type", editForm);
  if (editTarget?.module === "investigation") return (
    <Modal open={open} title="基本信息修改" width={660} okText="确定" cancelText="取消" onOk={onOk} onCancel={onCancel}>
      <Form form={editForm} layout="horizontal" labelCol={{ span: 7 }} wrapperCol={{ span: 15 }} style={{ paddingTop: 16 }}>
        <Form.Item name="customer" label="权利人" rules={[{ required: true }]}><Input readOnly /></Form.Item>
        <Form.Item name="contract_id" label="合同" rules={[{ required: true, message: "请选择合同" }]}><Select showSearch optionFilterProp="label" options={contracts.map(c => ({ value: c.id, label: `${c.serial_no}_${c.title}`, disabled: ["不可选", "已删除", "已取消", "已作废"].includes(c.status) }))} /></Form.Item>
        <Form.Item name="right_type" label="权利类型" rules={[{ required: true }]}><Select options={["商标", "专利", "著作权", "不正当竞争"].map(value => ({ value, label: value }))} /></Form.Item>
        <Form.Item name="customer_review" label="线索是否客户审核" rules={[{ required: true }]}><Select options={[{ value: false, label: "否" }, { value: true, label: "是" }]} /></Form.Item>
        <Form.Item label="授权期限" required><Space.Compact style={{ width: "100%" }}>
          <Form.Item name="authorized_from" noStyle rules={[{ required: true, message: "请选择授权开始日期" }]}><DatePicker placeholder="开始日期" style={{ width: "50%" }} /></Form.Item>
          <Form.Item name="authorized_to" noStyle dependencies={["authorized_from"]} rules={[{ required: true, message: "请选择授权结束日期" }, ({ getFieldValue }) => ({ validator(_, value) { return !value || !getFieldValue("authorized_from") || value.isAfter(getFieldValue("authorized_from"), "day") ? Promise.resolve() : Promise.reject(new Error("授权结束日期必须晚于开始日期")); } })]}><DatePicker placeholder="结束日期" style={{ width: "50%" }} /></Form.Item>
        </Space.Compact></Form.Item>
        <Form.Item name="authorization_scope_type" label="授权范围" rules={[{ required: true }]}><Select options={[{ value: "N", label: "全国" }, { value: "R", label: "区域" }]} /></Form.Item>
        {scope === "R" && <Form.Item name="authorization_regions" label="授权区域" rules={[{ required: true, message: "请选择授权区域" }]}><Cascader multiple changeOnSelect showSearch options={INVESTIGATION_REGION_GROUPS.map(({ province, cities }) => ({ value: province, label: province, children: cities.map(city => ({ value: city, label: city })) }))} placeholder="请选择授权省、市（可多选）" /></Form.Item>}
        <Form.Item name="description" label="备注"><Input.TextArea rows={3} /></Form.Item>
      </Form>
    </Modal>
  );
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

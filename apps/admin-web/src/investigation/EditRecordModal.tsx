import { POPUP_WIDTH } from "../components/common/popupSize";
import { KeywordPersonSelect } from "../components/KeywordPersonSelect";
import { useEffect, useState } from "react";
import { Modal, Form, Input, Select, Radio, DatePicker, Cascader, Space, Button, Typography, message } from "antd";
import { api } from "../api";
import type { Row, PersonOption, Contract } from "./types";
import { INVESTIGATION_REGION_GROUPS } from "../investigationRegionOptions.mjs";
import { CLUE_INFRINGEMENT_METHOD_OPTIONS, CLUE_SALES_CHANNEL_OPTIONS } from "./constants";
import InvestigationPartyEditor from "./InvestigationPartyEditor";

interface EditRecordModalProps {
  open: boolean;
  editTarget: Row | null;
  editForm: any;
  systemPersonOptions: PersonOption[];
  contracts?: Contract[];
  onOk: () => void;
  onCancel: () => void;
  // BUG20261030015：我的调查线索-待审批线索修改时可上传附件（不限格式），按钮为暂存线索/提交审批/取消。
  clueDraft?: {
    files: File[];
    onFilesChange: (files: File[]) => void;
    onSaveDraft: () => void;
    onSubmit: () => void;
  };
}

type ClueAttachment = { id: number; original_name: string };

function ClueAttachmentField({ recordId, files, onFilesChange }: { recordId: number; files: File[]; onFilesChange: (files: File[]) => void }) {
  const [items, setItems] = useState<ClueAttachment[]>([]);
  const load = async () => {
    try {
      const { data } = await api.get("/attachments", { params: { record_id: recordId } });
      setItems(Array.isArray(data) ? data : data?.items || []);
    } catch {
      setItems([]);
    }
  };
  useEffect(() => { void load(); }, [recordId]);
  const remove = (item: ClueAttachment) => Modal.confirm({
    title: `删除附件“${item.original_name}”？`,
    okText: "删除",
    cancelText: "取消",
    onOk: async () => {
      try {
        await api.delete(`/attachments/${item.id}`);
        message.success("附件已删除");
        await load();
      } catch (error: any) {
        message.error(error?.response?.data?.detail || "附件删除失败");
      }
    },
  });
  return (
    <Form.Item className="span-2" label="附件">
      <input multiple type="file" onChange={(event) => onFilesChange(Array.from(event.target.files || []))} />
      <Typography.Text type="secondary" style={{ display: "block" }}>
        {files.length ? `已选择 ${files.length} 个文件，保存时上传` : "可上传调查线索相关材料，格式不限"}
      </Typography.Text>
      {items.map((item) => (
        <div key={item.id}>
          {item.original_name}
          <Button type="link" size="small" danger onClick={() => remove(item)}>删除</Button>
        </div>
      ))}
    </Form.Item>
  );
}

export default function EditRecordModal({
  open,
  editTarget,
  editForm,
  systemPersonOptions,
  contracts = [],
  onOk,
  onCancel,
  clueDraft,
}: EditRecordModalProps) {
  const scope = Form.useWatch("authorization_scope_type", editForm);
  if (editTarget?.module === "investigation") return (
    <Modal open={open} title="基本信息修改" width={POPUP_WIDTH.md} okText="确定" cancelText="取消" onOk={onOk} onCancel={onCancel}>
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
      footer={clueDraft ? (
        <Space>
          <Button onClick={clueDraft.onSaveDraft}>暂存线索</Button>
          <Button type="primary" onClick={clueDraft.onSubmit}>提交审批</Button>
          <Button onClick={onCancel}>取消</Button>
        </Space>
      ) : undefined}
    >
      <Form form={editForm} layout="vertical">
        <div className="form-grid">
          {/* BUG20261030008：线索没有标题/事项（和旧系统一致），店铺名称单独一项。 */}
          {editTarget?.module !== "clue" && (
            <Form.Item
              label="标题/事项"
              name="title"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
          )}
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
              {/* Legacy field contract: <Form.List name="indictees">; each item exposes name={[name, "confirmation_method"]} and name={[name, "region"]}. */}
              <Form.Item label="主体信息" name="indictees" style={{ gridColumn: "1 / -1" }}><InvestigationPartyEditor /></Form.Item>
              <Form.Item label="调查辅助" name="investigation_assistant">
                <KeywordPersonSelect
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
        {clueDraft && editTarget && (
          <ClueAttachmentField recordId={editTarget.id} files={clueDraft.files} onFilesChange={clueDraft.onFilesChange} />
        )}
      </Form>
    </Modal>
  );
}

import { useEffect, useState } from "react";
import { Alert, Form, Input, Modal, message } from "antd";
import { api } from "../api";
import { KeywordPersonSelect } from "../components/KeywordPersonSelect";
import type { PersonOption, Row } from "./types";

/** 和旧系统一样：一个或多个人做这条线索的调查辅助员，原调查员不变（BUG20261030017）。 */
export function clueAssistantUsernames(row: Row): string[] {
  return String(row.data?.investigation_assistant || "")
    .split(/[,，;；、|\s]+/)
    .map((value) => value.trim())
    .filter(Boolean);
}

export default function ClueAssistantModal({ rows, systemPersonOptions, onDone, onCancel }: {
  rows: Row[];
  systemPersonOptions: PersonOption[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const current = rows.map((row) => clueAssistantUsernames(row).join(","));
  const same = current.every((value) => value === current[0]);
  useEffect(() => {
    form.setFieldsValue({ assistants: same && rows.length ? clueAssistantUsernames(rows[0]) : [], comment: "" });
  }, [rows, same, form]);
  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post("/investigations/clue-assistants", { clue_ids: rows.map((row) => row.id), assistants: values.assistants || [], comment: values.comment || "" });
      message.success("调查辅助员已保存");
      onDone();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "调查辅助员保存失败");
    } finally {
      setSaving(false);
    }
  };
  return (
    <Modal open={rows.length > 0} title={rows.length === 1 ? `调查辅助员：${rows[0].serial_no}` : `调查辅助员：已选 ${rows.length} 条线索`}
      okText="保存" cancelText="取消" confirmLoading={saving} onOk={() => void save()} onCancel={onCancel}>
      <Alert type="info" showIcon style={{ marginBottom: 12 }}
        title={rows.length > 1 && !same ? "所选线索现有的辅助员不一样；保存后都按这次选的名单设置。" : "保存后以这次选的名单为准，原调查员不变；辅助员可以查看、修改、取证这条线索。"} />
      <Form form={form} layout="vertical">
        <Form.Item label="调查辅助员" name="assistants">
          <KeywordPersonSelect mode="multiple" allowClear options={systemPersonOptions} placeholder="输入姓名或账号，可选多人；清空表示不设辅助员" />
        </Form.Item>
        <Form.Item label="说明" name="comment">
          <Input.TextArea rows={2} maxLength={500} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

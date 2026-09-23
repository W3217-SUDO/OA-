import { useState } from "react";
import { DatePicker, Form, Input, Modal, message } from "antd";
import dayjs from "dayjs";
import { api } from "../api";
import type { CaseRow } from "./types";

interface ReceiptBatchUploadModalProps {
  rows: CaseRow[];
  onCancel: () => void;
  onUploaded: () => Promise<boolean>;
}

export function ReceiptBatchUploadModal({ rows, onCancel, onUploaded }: ReceiptBatchUploadModalProps) {
  const [form] = Form.useForm();
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    const values = await form.validateFields();
    if (!file) {
      message.warning("请选择票据文件");
      return;
    }
    const data = new FormData();
    data.append("fee_ids", rows.map(row => row.id).join(","));
    data.append("bill_no", String(values.bill_no).trim());
    data.append("bill_date", values.bill_date.format("YYYY-MM-DD"));
    data.append("file", file);
    setSubmitting(true);
    let uploaded = 0;
    try {
      const response = await api.post("/finance/receipt-files/batch", data);
      uploaded = Number(response.data.uploaded);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量上传票据失败");
      setSubmitting(false);
      return;
    }
    try {
      const refreshed = await onUploaded();
      if (refreshed) message.success(`已为 ${uploaded} 条费用上传票据`);
      else message.warning(`已为 ${uploaded} 条费用上传票据，但列表刷新失败，请点击重试`);
    } catch {
      onCancel();
      message.warning(`已为 ${uploaded} 条费用上传票据，但列表刷新失败，请点击重试`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="票据批量上传" open onCancel={onCancel} onOk={() => void submit()} confirmLoading={submitting} okText="确认上传">
      <p>已选择 {rows.length} 条费用，客户：{rows[0]?.customer}</p>
      <Form form={form} layout="vertical" initialValues={{ bill_date: dayjs() }}>
        <Form.Item name="bill_no" label="票据编号" rules={[{ required: true, whitespace: true, message: "请输入票据编号" }]}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="bill_date" label="票据日期" rules={[{ required: true, message: "请选择票据日期" }]}>
          <DatePicker />
        </Form.Item>
        <Form.Item label="票据文件" required>
          <input type="file" onChange={event => setFile(event.target.files?.[0] || null)} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

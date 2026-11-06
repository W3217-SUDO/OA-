import { useState } from "react";
import { Alert, Button, Form, message, Modal, Select } from "antd";
import { api } from "../api";
import type { FeedbackReviewConfig } from "./types";

// 问题处理中心的“审核设置”：选审核人和免审账号。权限在后端校验，这里只是入口。
export default function FeedbackReviewSettings() {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<FeedbackReviewConfig | null>(null);
  const [reviewer, setReviewer] = useState("");
  const [exempt, setExempt] = useState<string[]>([]);

  const show = async () => {
    try {
      const { data } = await api.get<FeedbackReviewConfig>("/feedback/review-config");
      setConfig(data);
      setReviewer(data.reviewer);
      setExempt(data.exempt);
      setOpen(true);
    } catch {
      message.error("审核设置读取失败，请稍后重试");
    }
  };

  const save = async () => {
    if (!reviewer) {
      message.warning("必须选择审核人");
      return;
    }
    setSaving(true);
    try {
      await api.put("/feedback/review-config", { reviewer, exempt });
      message.success("审核设置已保存");
      setOpen(false);
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      message.error(typeof detail === "string" ? detail : "审核设置保存失败");
    } finally {
      setSaving(false);
    }
  };

  // 姓名和账号一起显示，避免把名字相近的账号选混；搜索两者都能匹配。
  const options = (config?.users || []).map((user) => ({
    value: user.username, label: `${user.display_name}（${user.username}）`,
  }));

  return <>
    <Button onClick={() => void show()}>审核设置</Button>
    <Modal title="问题处理中心审核设置" open={open} onCancel={() => setOpen(false)} okText="保存" cancelText="取消"
      onOk={() => void save()} confirmLoading={saving} okButtonProps={{ disabled: !config?.can_edit }}>
      {config && !config.reviewer_active && <Alert type="warning" showIcon style={{ marginBottom: 16 }}
        title={`当前审核人 ${config.reviewer_display_name}（${config.reviewer}）已停用，请更换。`} />}
      {config && !config.can_edit && <Alert type="info" showIcon style={{ marginBottom: 16 }} title="只有管理员本人可以修改审核设置。" />}
      <Form layout="vertical">
        <Form.Item label="审核人" required extra="免审账号之外提交的问题，要审核人点“审核通过”后才开始处理，内容会自动发到审核人的钉钉。">
          <Select aria-label="审核人" showSearch optionFilterProp="label" value={reviewer || undefined} options={options}
            disabled={!config?.can_edit} placeholder="选择在职账号" onChange={setReviewer} />
        </Form.Item>
        <Form.Item label="免审账号" extra="这些账号提交的问题不用审核，直接进入待处理。">
          <Select aria-label="免审账号" mode="multiple" optionFilterProp="label" value={exempt} options={options}
            disabled={!config?.can_edit} placeholder="选择在职账号" onChange={setExempt} />
        </Form.Item>
      </Form>
    </Modal>
  </>;
}

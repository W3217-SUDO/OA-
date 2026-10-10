import { useRef, useState } from "react";
import { Button, Empty, Form, Input, Modal, Space, Switch, Tooltip, message } from "antd";
import { DeleteOutlined, EditOutlined, PlusOutlined, UploadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText, type WorkspaceSkill } from "./types";

type Props = { open: boolean; onClose: () => void; skills: WorkspaceSkill[]; refresh: () => Promise<void>; onSelect: (id: string) => void };

export function SkillManager({ open, onClose, skills, refresh, onSelect }: Props) {
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const reset = () => { setEditingId(""); form.resetFields(); };
  const save = async (values: Record<string, string>) => {
    setBusy(true);
    try {
      const payload = { ...values, quick_prompts: (values.quick_prompts || "").split(/\r?\n/).map((value) => value.trim()).filter(Boolean) };
      if (editingId) await api.patch(`/agent/skills/${editingId}`, payload);
      else { const { data } = await api.post("/agent/skills", payload); onSelect(data.id); }
      await refresh(); reset(); message.success("技能已保存");
    } catch (error) { message.error(errorText(error, "技能保存失败")); }
    finally { setBusy(false); }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    try {
      const body = new FormData(); body.append("file", file);
      const { data } = await api.post("/agent/skills/upload", body);
      await refresh(); onSelect(data.id); message.success("技能已上传并选中");
    } catch (error) { message.error(errorText(error, "技能上传失败")); }
    finally { setBusy(false); if (fileRef.current) fileRef.current.value = ""; }
  };
  const toggle = async (skill: WorkspaceSkill, enabled: boolean) => {
    setBusy(true);
    try { await api.patch(`/agent/skills/${skill.id}`, { enabled }); await refresh(); }
    catch (error) { message.error(errorText(error, "技能更新失败")); }
    finally { setBusy(false); }
  };
  const remove = (skill: WorkspaceSkill) => Modal.confirm({ title: `删除“${skill.name}”？`, okText: "删除", cancelText: "取消", okButtonProps: { danger: true }, onOk: async () => {
    try { await api.delete(`/agent/skills/${skill.id}`); await refresh(); if (editingId === skill.id) reset(); }
    catch (error) { message.error(errorText(error, "技能删除失败")); throw error; }
  } });
  return <Modal open={open} title="我的技能" width={760} footer={null} onCancel={() => { onClose(); reset(); }}>
    <div className="workspace-skill-manager">
      <section className="workspace-skill-list">
        <div className="workspace-section-heading"><b>自定义技能</b><Space size={4}>
          <input hidden ref={fileRef} type="file" accept=".json,.md,.markdown,.docx" onChange={(event) => void upload(event.target.files?.[0])} />
          <Tooltip title="上传 Markdown、JSON 或 Word 技能"><Button icon={<UploadOutlined />} disabled={busy} onClick={() => fileRef.current?.click()}>上传</Button></Tooltip>
          <Tooltip title="新增技能"><Button icon={<PlusOutlined />} disabled={busy} onClick={reset} aria-label="新增技能" /></Tooltip>
        </Space></div>
        {skills.filter((skill) => skill.custom).map((skill) => <div className="workspace-skill-row" key={skill.id}>
          <div><b>{skill.name}</b><p>{skill.description}</p></div><Space size={2}>
            <Switch size="small" checked={skill.available} disabled={busy} onChange={(value) => void toggle(skill, value)} aria-label={`启用${skill.name}`} />
            <Tooltip title="编辑技能"><Button type="text" icon={<EditOutlined />} disabled={busy} aria-label="编辑技能" onClick={() => { setEditingId(skill.id); form.setFieldsValue({ ...skill, quick_prompts: skill.quick_prompts.join("\n") }); }} /></Tooltip>
            <Tooltip title="删除技能"><Button type="text" danger icon={<DeleteOutlined />} disabled={busy} aria-label="删除技能" onClick={() => remove(skill)} /></Tooltip>
          </Space>
        </div>)}
        {!skills.some((skill) => skill.custom) && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无自定义技能" />}
      </section>
      <Form layout="vertical" form={form} onFinish={(values) => void save(values)} disabled={busy}>
        <div className="workspace-section-heading"><b>{editingId ? "编辑技能" : "新增技能"}</b></div>
        <div className="workspace-skill-fields">
          <Form.Item name="name" label="名称" rules={[{ required: true, min: 2, max: 64 }]}><Input /></Form.Item>
          <Form.Item name="category" label="分类" initialValue="自定义" rules={[{ required: true, max: 32 }]}><Input /></Form.Item>
        </div>
        <Form.Item name="description" label="说明" rules={[{ required: true, min: 2, max: 500 }]}><Input /></Form.Item>
        <Form.Item name="instruction" label="技能指令" rules={[{ required: true, min: 10, max: 6000 }]}><Input.TextArea autoSize={{ minRows: 5, maxRows: 10 }} /></Form.Item>
        <Form.Item name="quick_prompts" label="快捷指令"><Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} /></Form.Item>
        <Button htmlType="submit" type="primary" loading={busy}>保存技能</Button>
      </Form>
    </div>
  </Modal>;
}

import { useEffect, useState } from "react";
import { Alert, Button, Empty, Modal, Spin, Tag } from "antd";
import { DownloadOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText, type WorkspaceSkill } from "./types";
import { SkillManager } from "./SkillManager";

type Definition = { id: string; name: string; scope: "personal"; filename: string; content: string; definition_sha256: string; import_sha256?: string };

export async function downloadPersonalSkill(id: string) {
  const { data, headers } = await api.get<Blob>(`/agent/skills/${encodeURIComponent(id)}/definition/download`, { responseType: "blob" });
  const disposition = String(headers["content-disposition"] || "");
  const fileName = /filename="([^"/\\]+)"/.exec(disposition)?.[1] || "SKILL.md";
  const url = URL.createObjectURL(data);
  const link = document.createElement("a"); link.href = url; link.download = fileName;
  try { document.body.appendChild(link); link.click(); }
  finally { link.remove(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); }
}

export function PersonalAiSpaceSkills({ active, busy, onSkillsChanged, onSelect }: { active: boolean; busy: boolean; onSkillsChanged?: () => Promise<void>; onSelect?: (id: string) => void }) {
  const [items, setItems] = useState<WorkspaceSkill[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [operation, setOperation] = useState("");
  const [managerOpen, setManagerOpen] = useState(false);
  const [definition, setDefinition] = useState<Definition | null>(null);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController(); setLoading(true); setError("");
    void api.get<{ items: WorkspaceSkill[] }>("/agent/skills/personal", { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setItems(data.items); })
      .catch(failure => { if (!controller.signal.aborted) setError(errorText(failure, "个人技能加载失败")); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [active]);
  const refresh = async () => {
    const { data } = await api.get<{ items: WorkspaceSkill[] }>("/agent/skills/personal"); setItems(data.items); setError("");
    await onSkillsChanged?.();
  };
  const run = async (id: string, operation: () => Promise<void>) => {
    setOperation(id); setError("");
    try { await operation(); } catch (failure) { setError(errorText(failure, "个人技能操作未完成")); }
    finally { setOperation(""); }
  };
  const locked = busy || loading || !!operation;
  return <section className="personal-ai-space-skills" aria-label="个人技能目录">
    <div className="personal-ai-space-toolbar">
      <Button icon={<PlusOutlined />} disabled={locked} onClick={() => setManagerOpen(true)}>导入个人技能</Button>
      <Button icon={<ReloadOutlined />} aria-label="刷新个人技能目录" disabled={locked} onClick={() => void run("refresh", refresh)} />
    </div>
    {error && <Alert type="error" showIcon title="个人技能操作未完成" description={error} action={<Button disabled={locked} onClick={() => void run("refresh", refresh)}>重新加载</Button>} />}
    {loading ? <Spin /> : !error && !items.length ? <Empty description="尚未安装个人技能" /> : <ul className="personal-ai-skill-list">{items.map(item => <li key={item.id}>
      <div className="personal-ai-skill-heading"><strong>{item.name}</strong><Tag color={item.enabled ?? item.available ? "success" : "default"}>{item.enabled ?? item.available ? "已启用" : "已停用"}</Tag></div>
      <p>{item.description}</p>
      <div className="personal-ai-space-file-actions">
        <Button disabled={locked} onClick={() => void run(item.id, async () => { const { data } = await api.get<Definition>(`/agent/skills/${encodeURIComponent(item.id)}/definition`); setDefinition(data); })}>查看完整定义</Button>
        <Button icon={<DownloadOutlined />} disabled={locked} onClick={() => void run(item.id, () => downloadPersonalSkill(item.id))}>下载 MD</Button>
        {onSelect && <Button disabled={locked || !item.available} onClick={() => onSelect(item.id)}>使用</Button>}
      </div>
    </li>)}</ul>}
    <SkillManager open={managerOpen} onClose={() => setManagerOpen(false)} mode="import-only" scope="personal" skills={items} refresh={refresh} onSelect={onSelect} />
    <Modal open={!!definition} onCancel={() => setDefinition(null)} title={definition ? `${definition.name} · 个人技能定义` : "个人技能定义"} width={760} className="personal-ai-skill-definition" footer={<Button onClick={() => setDefinition(null)}>关闭</Button>}>
      {definition && <div className="personal-ai-skill-definition-content"><p>当前保存的 SKILL.md 定义；不是原 GitHub 仓库 ZIP。</p><small>当前定义 SHA256：{definition.definition_sha256}</small>{definition.import_sha256 && <small>导入时原文件 SHA256：{definition.import_sha256}</small>}<pre tabIndex={0}>{definition.content}</pre></div>}
    </Modal>
  </section>;
}

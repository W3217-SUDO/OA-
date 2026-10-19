import { useEffect, useRef, useState } from "react";
import { Alert, Button, Select } from "antd";
import { FileTextOutlined } from "@ant-design/icons";
import { api } from "./api";
import { errorText } from "./personal-agent/types";

export type SystemSkillResource = { path: string; sha256: string; characters: number };
type Page = { skill_id: string; path: string; sha256: string; content: string; offset: number; next_offset: number | null };

export function SystemSkillResources({ skillId, items }: { skillId: string; items: SystemSkillResource[] }) {
  const [path, setPath] = useState<string>();
  const [content, setContent] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  const read = async () => {
    const item = items.find(entry => entry.path === path);
    if (!item) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true); setError(""); setContent("");
    try {
      let offset = 0;
      const parts: string[] = [];
      while (true) {
        const { data } = await api.get<Page>(`/agent/system-skills/${encodeURIComponent(skillId)}/resources`, {
          params: { path: item.path, offset, limit: 16000 }, signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (data.skill_id !== skillId || data.path !== item.path || data.sha256 !== item.sha256
          || data.offset !== offset || typeof data.content !== "string"
          || (data.next_offset !== null && (!Number.isInteger(data.next_offset) || data.next_offset <= offset || data.next_offset >= item.characters))) {
          throw new Error("技能资料响应无效，未展示不完整内容");
        }
        parts.push(data.content);
        if (data.next_offset === null) break;
        offset = data.next_offset;
      }
      setContent(parts.join(""));
    } catch (failure) {
      if (!controller.signal.aborted) setError(errorText(failure, "技能参考资料加载失败"));
    } finally { if (!controller.signal.aborted) setLoading(false); }
  };
  if (!items.length) return null;
  return <section className="system-skill-resources">
    <h3>配套参考资料（{items.length}）</h3>
    <div className="system-skill-resource-controls">
      <Select aria-label="选择技能参考资料" placeholder="选择参考资料" value={path} disabled={loading}
        options={items.map(item => ({ value: item.path, label: item.path }))}
        onChange={value => { setPath(value); setContent(""); setError(""); }} />
      <Button icon={<FileTextOutlined />} disabled={!path} loading={loading} onClick={() => void read()}>读取全文</Button>
    </div>
    {error && <Alert type="error" showIcon title={error} />}
    {content && <pre>{content}</pre>}
  </section>;
}

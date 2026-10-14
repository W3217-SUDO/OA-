import { useRef, useState } from "react";
import { Alert, Button, Modal, message } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { skillBase, skillScopeLabel, type SkillScope } from "./skillScope";
import { errorText, type WorkspaceSkill } from "./types";

type Props = {
  scope: SkillScope;
  busy: boolean;
  onBusy: (value: boolean) => void;
  refresh: () => Promise<void>;
  onSelect?: (id: string) => void;
};

export function SkillFileImport({ scope, busy, onBusy, refresh, onSelect }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const operationLock = useRef(false);
  const [error, setError] = useState("");
  const [refreshPending, setRefreshPending] = useState<WorkspaceSkill | null>(null);
  const scopeLabel = skillScopeLabel(scope);
  const selected = (skill: WorkspaceSkill) => {
    if (skill.available) {
      onSelect?.(skill.id);
      message.success(onSelect ? "技能已导入并选中" : `${scopeLabel}已导入`);
    } else message.info("技能已导入但已停用，当前选择保持不变；请在智能体中心启用后使用");
  };
  const upload = async (file: File) => {
    let saved: WorkspaceSkill | null = null;
    try {
      const body = new FormData(); body.append("file", file);
      const { data } = await api.post<WorkspaceSkill>(`${skillBase(scope)}/upload`, body);
      saved = data;
      await refresh(); selected(data); setRefreshPending(null);
    } catch (failure) {
      setRefreshPending(saved);
      setError(saved ? `技能已导入，但列表刷新失败：${errorText(failure, "请刷新技能列表")}` : errorText(failure, "技能导入失败"));
    } finally { operationLock.current = false; onBusy(false); }
  };
  const confirm = (file?: File) => {
    if (!file || busy || operationLock.current || refreshPending) return;
    setError("");
    if (!/\.(json|md|markdown|docx)$/i.test(file.name) || !file.size || file.size > 2 * 1024 * 1024) {
      setError("请选择 2MB 以内的 Markdown、JSON 或 Word（.docx）技能文件"); return;
    }
    operationLock.current = true; onBusy(true);
    Modal.confirm({
      title: `确认导入到${scopeLabel}？`,
      className: "workspace-skill-import-modal",
      content: <div className="workspace-skill-import-confirmation"><b>{file.name}</b><p>{scope === "global" ? "导入后启用的技能可供全所账号选用。" : "导入后仅本人可选用，不会共享给其他账号。"}技能指令会参与 AI 回答，请确认文件内容可信。</p></div>,
      okText: "确认导入", cancelText: "取消", maskClosable: false, closable: false,
      onOk: () => upload(file),
      onCancel: () => { operationLock.current = false; onBusy(false); },
    });
  };
  const retryRefresh = async () => {
    if (!refreshPending || busy || operationLock.current) return;
    operationLock.current = true; onBusy(true);
    try { await refresh(); selected(refreshPending); setRefreshPending(null); setError(""); }
    catch (failure) { setError(`技能已导入，但列表刷新失败：${errorText(failure, "请刷新技能列表")}`); }
    finally { operationLock.current = false; onBusy(false); }
  };
  return <div className="workspace-skill-file-import">
    <input hidden ref={fileRef} type="file" accept=".json,.md,.markdown,.docx" onChange={event => { const file = event.target.files?.[0]; event.target.value = ""; confirm(file); }} />
    <Button icon={<UploadOutlined />} disabled={busy || !!refreshPending} onClick={() => fileRef.current?.click()}>导入技能文件</Button>
    {error && <Alert type={refreshPending ? "warning" : "error"} showIcon title={refreshPending ? "技能已导入，待刷新" : "技能导入未完成"} description={error} action={refreshPending ? <Button disabled={busy} onClick={() => void retryRefresh()}>刷新{scopeLabel}</Button> : undefined} />}
  </div>;
}

import { useEffect, useState } from "react";
import { Alert, Button, Card, Checkbox, Empty, Space, message } from "antd";
import { api } from "../api";

// 501580（陶国南 11-05）：系统中心“自动任务”“逾期扣款”。列出全部部门和角色，默认都勾选；
// 取消勾选的部门或角色的人不再收到自动任务 / 任务超期不再记超期绩效。只存取消勾选的，新加的部门、角色默认勾选。
type Scope = { excluded_departments: string[]; excluded_roles: string[] };
type Settings = { value: Scope; departments: { name: string }[]; roles: { code: string; name: string }[] };
export type TaskScopeKind = "automatic-task" | "overdue-penalty";

const TEXT: Record<TaskScopeKind, { title: string; note: string; saved: string }> = {
  "automatic-task": {
    title: "自动任务",
    note: "勾选的部门和角色照常收到系统自动任务。取消勾选后，这个部门或角色的人不再收到系统自动任务（全部 15 类都不发，改为手动）；一个人的部门或任一角色被取消勾选就不发。已发出的任务不受影响。",
    saved: "自动任务设置已保存，之后生成的自动任务按新设置发",
  },
  "overdue-penalty": {
    title: "逾期扣款",
    note: "勾选的部门和角色任务超期照常记超期绩效。取消勾选后，这个部门或角色的人任务超期不再记超期绩效；一个人的部门或任一角色被取消勾选就不记。已记的绩效和老系统迁来的扣款不追溯、不删除。",
    saved: "逾期扣款设置已保存，之后按新设置记超期绩效",
  },
};

const sameScope = (a: Scope, b: Scope) =>
  JSON.stringify([[...a.excluded_departments].sort(), [...a.excluded_roles].sort()]) ===
  JSON.stringify([[...b.excluded_departments].sort(), [...b.excluded_roles].sort()]);

function ScopeGroup({ title, names, excluded, onChange }: { title: string; names: string[]; excluded: string[]; onChange: (excluded: string[]) => void }) {
  const checked = names.filter((name) => !excluded.includes(name));
  // 已停用或已删除的部门/角色若曾被取消勾选，保留在排除名单里，不在这里显示。
  const hiddenExcluded = excluded.filter((name) => !names.includes(name));
  return (
    <Card size="small" type="inner" style={{ marginBottom: 16 }} title={`${title}（已勾选 ${checked.length} / ${names.length}）`} extra={
      <Space>
        <Button size="small" onClick={() => onChange(hiddenExcluded)}>全选</Button>
        <Button size="small" onClick={() => onChange([...hiddenExcluded, ...names])}>全不选</Button>
      </Space>
    }>
      {names.length ? (
        <Checkbox.Group
          style={{ display: "flex", flexWrap: "wrap", gap: "8px 16px" }}
          options={names.map((name) => ({ label: name, value: name }))}
          value={checked}
          onChange={(values) => onChange([...hiddenExcluded, ...names.filter((name) => !values.includes(name))])}
        />
      ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`没有${title}`} />}
    </Card>
  );
}

export function SystemTaskScopes({ kind }: { kind: TaskScopeKind }) {
  const text = TEXT[kind];
  const [settings, setSettings] = useState<Settings>();
  const [draft, setDraft] = useState<Scope>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string>();

  const load = async () => {
    setLoading(true);
    setLoadError(undefined);
    try {
      const { data } = await api.get<Settings>(`/system/task-scopes/${kind}`);
      setSettings(data);
      setDraft(data.value);
    } catch (error: any) {
      setLoadError(error?.response?.data?.detail || `${text.title}设置加载失败`);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void load(); }, [kind]);

  if (loading) return <Card loading title={text.title} />;
  if (loadError || !settings || !draft) {
    return <Card title={text.title}><Alert type="error" showIcon title={loadError || `${text.title}设置加载失败`} action={<Button size="small" onClick={() => void load()}>重试</Button>} /></Card>;
  }
  const changed = !sameScope(draft, settings.value);
  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put<{ value: Scope }>(`/system/task-scopes/${kind}`, { value: draft });
      setSettings({ ...settings, value: data.value });
      setDraft(data.value);
      message.success(text.saved);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title={text.title} extra={
      <Space>
        <Button disabled={!changed} onClick={() => setDraft(settings.value)}>撤销修改</Button>
        <Button type="primary" loading={saving} disabled={!changed} onClick={() => void save()}>保存</Button>
      </Space>
    }>
      <Alert type="info" showIcon style={{ marginBottom: 16 }} title={text.note} />
      <ScopeGroup title="部门" names={settings.departments.map((item) => item.name)} excluded={draft.excluded_departments}
        onChange={(excluded) => setDraft({ ...draft, excluded_departments: excluded })} />
      <ScopeGroup title="角色" names={settings.roles.map((item) => item.name)} excluded={draft.excluded_roles}
        onChange={(excluded) => setDraft({ ...draft, excluded_roles: excluded })} />
    </Card>
  );
}

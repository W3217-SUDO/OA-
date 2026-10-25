import { useEffect, useState } from "react";
import { Alert, Button, Card, Checkbox, Empty, Input, Popconfirm, Select, Space, Tag, Tooltip, message } from "antd";
import { ArrowDownOutlined, ArrowUpOutlined, DeleteOutlined } from "@ant-design/icons";
import { api } from "../api";
import Table from "../components/ResizableTable";

// 系统参数“首页分端待办”：三个端各放哪些待办（顺序即首页顺序），各角色默认看哪个端；管理端看全部。
type PortalItem = { key: string; label: string; route: string; source: string; description: string };
type Portal = { key: string; name: string; items: string[] };
type PortalConfig = { portals: Portal[]; role_portals: Record<string, string[]> };
type Settings = { value: PortalConfig; defaults: PortalConfig; items: PortalItem[]; roles: { code: string; name: string }[] };

const MANAGE_PORTAL = "manage";
const MAX_PORTAL_ITEMS = 12;

export function SystemDashboardPortals() {
  const [settings, setSettings] = useState<Settings>();
  const [draft, setDraft] = useState<PortalConfig>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string>();

  const load = async () => {
    setLoading(true);
    setLoadError(undefined);
    try {
      const { data } = await api.get<Settings>("/system/dashboard-portals");
      setSettings(data);
      setDraft(data.value);
    } catch (error: any) {
      setLoadError(error?.response?.data?.detail || "首页分端配置加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void load(); }, []);

  if (loading) return <Card loading title="首页分端待办" />;
  if (loadError || !settings || !draft) {
    return <Card title="首页分端待办"><Alert type="error" showIcon title={loadError || "首页分端配置加载失败"} action={<Button size="small" onClick={() => void load()}>重试</Button>} /></Card>;
  }

  const itemByKey = new Map(settings.items.map((item) => [item.key, item]));
  const updatePortal = (key: string, change: (portal: Portal) => Portal) =>
    setDraft({ ...draft, portals: draft.portals.map((portal) => (portal.key === key ? change(portal) : portal)) });
  const moveItem = (portal: Portal, index: number, offset: number) => {
    const items = [...portal.items];
    const [moved] = items.splice(index, 1);
    items.splice(index + offset, 0, moved);
    return { ...portal, items };
  };
  const portalOptions = [...draft.portals.map((portal) => ({ label: portal.name, value: portal.key })), { label: "管理端（全部）", value: MANAGE_PORTAL }];
  const roleNames = Array.from(new Set([...settings.roles.map((role) => role.name), ...Object.keys(draft.role_portals)]));
  const changed = JSON.stringify(draft) !== JSON.stringify(settings.value);

  const save = async () => {
    const empty = draft.portals.find((portal) => !portal.name.trim());
    if (empty) {
      message.error("端口名称不能为空");
      return;
    }
    setSaving(true);
    try {
      const { data } = await api.put<{ value: PortalConfig }>("/system/dashboard-portals", { value: draft });
      setSettings({ ...settings, value: data.value });
      setDraft(data.value);
      message.success("首页分端待办已保存，用户刷新首页后生效");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card
      title="首页分端待办"
      extra={<Space>
        <Popconfirm title="恢复成默认分端？" description="恢复后还需要点“保存”才会生效。" okText="恢复" cancelText="取消" onConfirm={() => setDraft(settings.defaults)}>
          <Button>恢复默认</Button>
        </Popconfirm>
        <Button disabled={!changed} onClick={() => setDraft(settings.value)}>撤销修改</Button>
        <Button type="primary" loading={saving} disabled={!changed} onClick={() => void save()}>保存</Button>
      </Space>}
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        title="首页“我的待办”按端分页签显示。每个端最多 12 项，排在前面的显示在前面；管理端固定显示全部待办，不用配置。一个角色可以勾选多个端，首页就会出现多个页签。"
      />
      <div className="system-portal-grid">
        {draft.portals.map((portal) => {
          const unused = settings.items.filter((item) => !portal.items.includes(item.key));
          return (
            <Card key={portal.key} size="small" type="inner" title={
              <Input value={portal.name} maxLength={20} aria-label="端口名称" style={{ maxWidth: 200 }}
                onChange={(event) => updatePortal(portal.key, (current) => ({ ...current, name: event.target.value }))} />
            } extra={<span className={portal.items.length > 8 ? "system-portal-count is-over" : "system-portal-count"}>{portal.items.length} 项</span>}>
              {!portal.items.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有待办项" />}
              <ol className="system-portal-items">
                {portal.items.map((key, index) => {
                  const item = itemByKey.get(key);
                  return (
                    <li key={key}>
                      <Tooltip title={item?.description}><span className="system-portal-item-name">{item?.label || key}</span></Tooltip>
                      <Space size={2}>
                        <Button type="text" size="small" icon={<ArrowUpOutlined />} aria-label={`上移${item?.label}`} disabled={index === 0}
                          onClick={() => updatePortal(portal.key, (current) => moveItem(current, index, -1))} />
                        <Button type="text" size="small" icon={<ArrowDownOutlined />} aria-label={`下移${item?.label}`} disabled={index === portal.items.length - 1}
                          onClick={() => updatePortal(portal.key, (current) => moveItem(current, index, 1))} />
                        <Button type="text" size="small" danger icon={<DeleteOutlined />} aria-label={`移除${item?.label}`}
                          onClick={() => updatePortal(portal.key, (current) => ({ ...current, items: current.items.filter((itemKey) => itemKey !== key) }))} />
                      </Space>
                    </li>
                  );
                })}
              </ol>
              <Select
                style={{ width: "100%" }}
                placeholder={portal.items.length >= MAX_PORTAL_ITEMS ? `最多 ${MAX_PORTAL_ITEMS} 项` : "添加待办项"}
                disabled={portal.items.length >= MAX_PORTAL_ITEMS}
                value={null}
                showSearch
                optionFilterProp="label"
                options={unused.map((item) => ({ value: item.key, label: item.label, title: item.description }))}
                onChange={(key: string) => updatePortal(portal.key, (current) => ({ ...current, items: [...current.items, key] }))}
              />
            </Card>
          );
        })}
      </div>
      <h3 className="system-portal-subtitle">角色归属</h3>
      <Table
        size="small"
        rowKey="name"
        pagination={false}
        dataSource={roleNames.map((name) => ({ name }))}
        columns={[
          { title: "角色", dataIndex: "name", width: 180, render: (name: string) => settings.roles.some((role) => role.name === name) ? name : <Space>{name}<Tag>已停用</Tag></Space> },
          {
            title: "首页显示的端",
            render: (_: unknown, row: { name: string }) => (
              <Checkbox.Group
                options={portalOptions}
                value={draft.role_portals[row.name] || []}
                onChange={(values) => {
                  const next = { ...draft.role_portals };
                  if (values.length) next[row.name] = values as string[];
                  else delete next[row.name];
                  setDraft({ ...draft, role_portals: next });
                }}
              />
            ),
          },
        ]}
      />
      <p className="system-portal-note">没有归属任何端的角色，首页继续显示原来的“我的待办”；系统管理员账号始终看管理端。</p>
    </Card>
  );
}

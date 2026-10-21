import { useState } from "react";
import { Alert, Button, Drawer, Empty, Input, Space, Tabs, Tag } from "antd";
import { ApiOutlined, CheckOutlined, DownloadOutlined, SearchOutlined } from "@ant-design/icons";
import "./capability-market.css";

export type DshCatalogItem = {
  id: string; name: string; title: string; category: string; description: string;
  requirements: string; version: string; author: string; source: string;
  unavailable_reason: string; experimental: boolean;
};

export function DshPluginCatalog({ items, installedNames, busy, ready, onInstall }: {
  items: DshCatalogItem[]; installedNames: string[]; busy: string; ready: boolean;
  onInstall: (item: DshCatalogItem) => void;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("全部");
  const [selected, setSelected] = useState<DshCatalogItem | null>(null);
  const matching = items.filter(item => (category === "全部" || item.category === category)
    && `${item.title} ${item.name} ${item.description}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  const installButton = (item: DshCatalogItem) => {
    const installed = installedNames.includes(item.name);
    return <Button type="primary" icon={installed ? <CheckOutlined /> : <DownloadOutlined />}
      disabled={installed || !!item.unavailable_reason || !ready || (!!busy && busy !== item.name)}
      loading={busy === item.name} onClick={() => onInstall(item)}>{installed ? "已安装" : busy === item.name ? "正在安装" : "安装到系统"}</Button>;
  };
  return <div className="dsh-plugin-market">
    <div className="dsh-plugin-market-toolbar"><h3>插件市场 <span>{items.length}</span></h3>
      <Input prefix={<SearchOutlined />} aria-label="搜索 DSH 插件" placeholder="搜索插件名称或功能" allowClear
        value={query} onChange={event => setQuery(event.target.value)} /></div>
    <Tabs className="capability-market-categories" activeKey={category} onChange={setCategory}
      items={["全部", ...new Set(items.map(item => item.category))].map(value => ({ key: value, label: value }))} />
    {!matching.length && <Empty description="没有匹配的插件" />}
    <div className="capability-market-grid">{matching.map(item => <article className="capability-market-card" key={item.id}>
      <div className="capability-market-card-heading"><span className="capability-market-icon"><ApiOutlined /></span>
        <div><h3>{item.title}</h3><small>{item.author} · {item.version}</small></div></div>
      <p>{item.description}</p>
      <div className="capability-market-tags"><Tag>{item.category}</Tag><Tag color={item.experimental ? "gold" : "green"}>{item.experimental ? "实验性" : "官方插件"}</Tag></div>
      {item.unavailable_reason && <p className="dsh-plugin-failure">{item.unavailable_reason}</p>}
      <footer><Button onClick={() => setSelected(item)}>查看详情</Button>{installButton(item)}</footer>
    </article>)}</div>
    <Drawer open={!!selected} title={selected?.title} onClose={() => setSelected(null)} width={680}
      rootClassName="capability-market-detail dsh-plugin-detail" zIndex={1500}
      footer={selected && <Space wrap><Button onClick={() => setSelected(null)}>关闭</Button>{installButton(selected)}</Space>}>
      {selected && <><p>{selected.description}</p><Space wrap><Tag>{selected.category}</Tag><Tag>{selected.version}</Tag></Space>
        <h3>使用要求</h3><p>{selected.requirements}</p>
        <h3>安装范围</h3><p>安装到系统，后续个人空间和案件空间消息可加载此插件；各工作区的文件、会话和记忆保持隔离。安装与运行失败会显示实际错误。</p>
        <h3>插件来源</h3><p className="dsh-plugin-package-name">{selected.name}</p>
        <a href={selected.source} target="_blank" rel="noopener noreferrer">查看官方发布包</a>
        {selected.experimental && <Alert type="warning" showIcon title="此插件由 DSH 官方作为实验性能力发布。" />}
        {selected.unavailable_reason && <Alert type="error" showIcon title={selected.unavailable_reason} />}
      </>}
    </Drawer>
  </div>;
}

import { useState } from "react";
import { Drawer, Empty, Input, List, message, Space, Tag } from "antd";
import { FileOutlined, SearchOutlined } from "@ant-design/icons";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { rememberTaskDetailTarget } from "./taskDetailNavigation";
import { rememberInvestigationDetailTarget } from "./investigationDetailNavigation";

type Result = {
  type: string;
  id: number;
  module: string;
  route: string;
  serial_no: string;
  title: string;
  subtitle: string;
  status: string;
  updated_at: string;
};

const moduleNames: Record<string, string> = {
  customer: "客户",
  contract: "合同",
  case: "案件",
  task: "任务",
  clue: "线索",
  notary: "公证",
  evidence: "证据",
  seal: "用印",
  finance: "财务",
  document: "收发文",
  hr: "人事",
  warehouse: "仓库",
  report: "报表",
  attachment: "附件",
  template: "模板",
};

export default function GlobalSearch({ onNavigate }: { onNavigate: (route: string) => void }) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Result[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const search = async (value = query) => {
    const q = value.trim();
    if (q.length < 2) {
      message.warning("至少输入 2 个字符");
      return;
    }
    setLoading(true);
    setOpen(true);
    try {
      const { data } = await api.get("/search", { params: { q } });
      setItems(data.items);
    } catch {
      message.error("全局检索失败");
    } finally {
      setLoading(false);
    }
  };

  const openResult = (item: Result) => {
    if (item.module === "case") rememberCaseDetailTarget({ id: item.id, serial_no: item.serial_no });
    if (item.module === "contract") rememberContractDetailTarget({ id: item.id, serial_no: item.serial_no });
    if (item.module === "customer") rememberCustomerDetailTarget({ id: item.id, serial_no: item.serial_no, title: item.title });
    if (item.module === "task") rememberTaskDetailTarget({ id: item.id, serial_no: item.serial_no });
    if (["clue", "notary", "evidence"].includes(item.module)) rememberInvestigationDetailTarget({ id: item.id, serial_no: item.serial_no, module: item.module });
    onNavigate(item.route);
    setOpen(false);
  };

  return (
    <>
      <Input.Search
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onSearch={search}
        enterButton={<SearchOutlined />}
        placeholder="案号、法院号、案件名、客户名、任务内容"
      />
      <Drawer size={600} open={open} title={`全局检索：${query}`} onClose={() => setOpen(false)}>
        <List
          loading={loading}
          dataSource={items}
          locale={{ emptyText: <Empty description="未找到匹配的业务、附件或模板" /> }}
          renderItem={(item) => (
            <List.Item style={{ cursor: "pointer" }} onClick={() => openResult(item)}>
              <List.Item.Meta
                avatar={<FileOutlined style={{ fontSize: 22, color: "#00a65a" }} />}
                title={<Space><Tag>{moduleNames[item.module] || item.module}</Tag><b>{item.serial_no}</b>{item.title}{item.status && <Tag color="green">{item.status}</Tag>}</Space>}
                description={<><div>{item.subtitle || "—"}</div><small>更新：{item.updated_at ? new Date(item.updated_at).toLocaleString("zh-CN") : "—"}</small></>}
              />
            </List.Item>
          )}
        />
      </Drawer>
    </>
  );
}

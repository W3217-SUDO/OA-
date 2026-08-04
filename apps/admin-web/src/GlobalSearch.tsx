import { useMemo, useState } from "react";
import { Drawer, Empty, Input, List, message, Space, Tag } from "antd";
import { FileOutlined, SearchOutlined } from "@ant-design/icons";
import { api } from "./api";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberContractDetailTarget } from "./contractDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { rememberTaskDetailTarget } from "./taskDetailNavigation";
import { rememberInvestigationDetailTarget } from "./investigationDetailNavigation";
import { rememberBusinessRecordDetailTarget } from "./businessRecordDetailNavigation";
import { rememberDocumentSearchDetailTarget } from "./documentSearchDetailNavigation";

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
  related_id?: number | null;
  related_serial_no?: string;
};
export type AuthorizedMenuItem = {
  key: string;
  label: string;
  disabled?: boolean;
  link_url?: string;
  menu_type_id?: number;
  open_target?: string;
  children?: AuthorizedMenuItem[];
};
type MenuSearchResult = {
  item: AuthorizedMenuItem;
  path: string;
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
  invoice: "开票",
  refund: "退费",
  sms: "开庭短信",
  document: "收发文",
  hr: "人事",
  warehouse: "仓库",
  report: "报表",
  attachment: "附件",
  template: "模板",
};

export function searchAuthorizedMenuItems(
  items: AuthorizedMenuItem[],
  query: string,
): MenuSearchResult[] {
  const keyword = query.trim().toLocaleLowerCase();
  if (!keyword) return [];
  const visit = (nodes: AuthorizedMenuItem[], ancestors: string[]): MenuSearchResult[] =>
    nodes.flatMap((item) => {
      const path = [...ancestors, item.label];
      const children = visit(item.children || [], path);
      const isClickableLeaf = !item.children?.length && !item.disabled;
      const matches = `${path.join(" ")} ${item.key}`.toLocaleLowerCase().includes(keyword);
      return [
        ...(isClickableLeaf && matches ? [{ item, path: path.join(" / ") }] : []),
        ...children,
      ];
    });
  return visit(items, []);
}

export default function GlobalSearch({
  onNavigate,
  menuItems = [],
  onOpenMenu,
}: {
  onNavigate: (route: string) => void;
  menuItems?: AuthorizedMenuItem[];
  onOpenMenu?: (item: AuthorizedMenuItem) => void;
}) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Result[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const menuMatches = useMemo(
    () => searchAuthorizedMenuItems(menuItems, query),
    [menuItems, query],
  );

  const handleQueryChange = (value: string) => {
    setQuery(value);
    setItems([]);
    setOpen(Boolean(value.trim()));
  };

  const search = async (value = query) => {
    const q = value.trim();
    if (!q) {
      setItems([]);
      setOpen(false);
      return;
    }
    setOpen(true);
    if (q.length < 2) {
      setItems([]);
      return;
    }
    setLoading(true);
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
    if (["finance", "invoice", "refund", "finance_package", "finance_settlement", "finance_archive_settlement", "seal", "document", "warehouse", "hr"].includes(item.module)) rememberBusinessRecordDetailTarget({ id: item.id, module: item.module as "finance" | "invoice" | "refund" | "finance_package" | "finance_settlement" | "finance_archive_settlement" | "seal" | "document" | "warehouse" | "hr" });
    if (["attachment", "template"].includes(item.module)) rememberDocumentSearchDetailTarget({ id: item.id, kind: item.module as "attachment" | "template" });
    if (item.module === "sms" && item.related_id) rememberCaseDetailTarget({ id: item.related_id, serial_no: item.related_serial_no });
    onNavigate(item.route);
    setOpen(false);
  };
  const openMenuResult = (item: MenuSearchResult) => {
    if (onOpenMenu) onOpenMenu(item.item);
    else onNavigate(item.item.key);
    setOpen(false);
  };

  return (
    <>
      <Input.Search
        value={query}
        onChange={(event) => handleQueryChange(event.target.value)}
        onSearch={search}
        enterButton={<SearchOutlined />}
        placeholder="搜索菜单、案号、法院号、案件名、客户名"
      />
      <Drawer size={600} open={open} title={`全局检索：${query}`} onClose={() => setOpen(false)}>
        {menuMatches.length > 0 && (
          <List
            header="菜单"
            dataSource={menuMatches}
            renderItem={(item) => (
              <List.Item style={{ cursor: "pointer" }} onClick={() => openMenuResult(item)}>
                <List.Item.Meta
                  avatar={<SearchOutlined style={{ fontSize: 18, color: "#1677ff" }} />}
                  title={<Space><Tag color="blue">菜单</Tag><b>{item.item.label}</b></Space>}
                  description={item.path}
                />
              </List.Item>
            )}
          />
        )}
        {query.trim().length >= 2 ? (
          <List
            header={menuMatches.length ? "业务、附件或模板" : undefined}
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
        ) : !menuMatches.length ? (
          <Empty description="未找到匹配菜单；输入至少 2 个字符可检索业务数据" />
        ) : null}
      </Drawer>
    </>
  );
}

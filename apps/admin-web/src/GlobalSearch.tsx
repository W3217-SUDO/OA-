import { useState } from "react";
import { Input } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import {
  GLOBAL_CASE_SEARCH_CONTEXT_KEY,
  buildGlobalCaseSearchContext,
} from "./globalCaseSearchParity.mjs";

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

  const handleQueryChange = (value: string) => {
    setQuery(value);
  };

  const search = async (value = query) => {
    const q = value.trim();
    if (!q) return;
    const exactMenuMatches = searchAuthorizedMenuItems(menuItems, q).filter(({ item }) =>
      [item.label, item.key].some((candidate) => candidate.trim().toLocaleLowerCase() === q.toLocaleLowerCase()),
    );
    if (exactMenuMatches.length === 1) {
      openMenuResult(exactMenuMatches[0]);
      return;
    }
    const context = buildGlobalCaseSearchContext(q);
    if (!context) return;
    sessionStorage.setItem(GLOBAL_CASE_SEARCH_CONTEXT_KEY, JSON.stringify(context));
    onNavigate(context.route);
  };
  const openMenuResult = (item: MenuSearchResult) => {
    if (onOpenMenu) onOpenMenu(item.item);
    else onNavigate(item.item.key);
  };

  return (
    <Input.Search
      value={query}
      onChange={(event) => handleQueryChange(event.target.value)}
      onSearch={search}
      enterButton={<SearchOutlined />}
      placeholder="搜索菜单、案号、法院号、案件名、客户名"
    />
  );
}

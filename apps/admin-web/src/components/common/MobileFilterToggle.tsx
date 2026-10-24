import { DownOutlined, FilterOutlined } from "@ant-design/icons";
import { useState } from "react";

const PHONE_QUERY = "(max-width: 720px)";
const STORAGE_PREFIX = "sunhold:filter-open:";

function isPhone() {
  try { return window.matchMedia(PHONE_QUERY).matches; } catch { return false; }
}

// 桌面上的展开/收起按页面记住（同一页面多个筛选区再按 label 区分）；手机每次进入都先收起。
function storageKey(label: string) {
  const page = new URLSearchParams(window.location.search).get("page") || "home";
  return `${STORAGE_PREFIX}${page}:${label}`;
}

function initialOpen(label: string) {
  if (isPhone()) return false;
  try { return localStorage.getItem(storageKey(label)) !== "0"; } catch { return true; }
}

/**
 * 筛选区（页面上方的查询卡片）可折叠：桌面默认展开、开关是筛选区上方的一行小字，手机默认收起、开关是整行按钮。
 * 用法：把 toggle 放在筛选表单前面，className 加到筛选表单上（整块收起）；
 * 表单里还有新增、导出等按钮时改用 fieldsClassName，只收起字段，带 oa-filter-keep 的子元素保留。
 */
export function useMobileFilterToggle(label = "筛选条件") {
  const [open, setOpen] = useState(() => initialOpen(label));
  const change = () => setOpen((value) => {
    const next = !value;
    if (!isPhone()) {
      try { localStorage.setItem(storageKey(label), next ? "1" : "0"); } catch { /* 存储不可用时只是不记住 */ }
    }
    return next;
  });
  const toggle = (
    <button type="button" className="oa-filter-toggle" aria-expanded={open} onClick={change}>
      <FilterOutlined />
      <span>{label}</span>
      <span className="oa-filter-toggle-state">
        {open ? "收起" : "展开"}
        <DownOutlined />
      </span>
    </button>
  );
  const state = open ? " is-open" : "";
  return { open, toggle, className: `oa-filter-collapsible${state}`, fieldsClassName: `oa-filter-fields${state}` };
}

export const useFilterToggle = useMobileFilterToggle;

import { DownOutlined, FilterOutlined } from "@ant-design/icons";
import { useState } from "react";

/**
 * 手机上筛选区默认收起，点“筛选条件”再展开；桌面不显示开关，筛选区照常展开。
 * 用法：把 toggle 放在筛选表单前面，className 加到筛选表单上（整块收起）；
 * 表单里还有新增、导出等按钮时改用 fieldsClassName，只收起字段，带 oa-filter-keep 的子元素保留。
 */
export function useMobileFilterToggle(label = "筛选条件") {
  const [open, setOpen] = useState(false);
  const toggle = (
    <button type="button" className="oa-filter-toggle" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
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

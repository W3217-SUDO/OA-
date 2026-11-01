import { useState, type MouseEvent, type ReactNode } from "react";
import { Dropdown } from "antd";

export type IprRowMenuItem = { key: string; label: string; disabled?: boolean; onClick: () => void };

/** 案件页下方各页签的右键菜单（BUG20261028020，按原系统各页签的菜单项）。
 * 在某一行上点右键，菜单针对这一行；在空白处点右键，只能用不针对某一行的项（如上传、新增、刷新）。
 * 没有权限或当前状态不允许的项置灰。 */
export function IprRowContextMenu<T>({ rows, rowKey, items, children }: {
  rows: T[];
  rowKey: (row: T) => string | number;
  items: (row: T | null) => IprRowMenuItem[];
  children: ReactNode;
}) {
  const [current, setCurrent] = useState<T | null>(null);
  const pick = (event: MouseEvent<HTMLDivElement>) => {
    const key = (event.target as HTMLElement).closest("tr[data-row-key]")?.getAttribute("data-row-key");
    setCurrent(key == null ? null : rows.find((row) => String(rowKey(row)) === key) ?? null);
  };
  const menuItems = items(current);
  return (
    <Dropdown
      trigger={["contextMenu"]}
      menu={{
        items: menuItems.map(({ key, label, disabled }) => ({ key, label, disabled })),
        onClick: ({ key }) => menuItems.find((item) => item.key === key)?.onClick(),
      }}
    >
      <div className="ipr-row-context-menu" onContextMenuCapture={pick}>{children}</div>
    </Dropdown>
  );
}

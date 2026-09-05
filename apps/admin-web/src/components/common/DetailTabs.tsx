import { Tabs,type TabsProps } from "antd";
import type { ReactNode } from "react";

/** Detail sections keep their original keys, mounting behavior and controlled selection. */
export function DetailTabs({ sections, toolbar, ...props }: Omit<TabsProps, "items"> & { sections: TabsProps["items"]; toolbar?: ReactNode }) {
  return <>{toolbar}<Tabs {...props} items={sections} /></>;
}

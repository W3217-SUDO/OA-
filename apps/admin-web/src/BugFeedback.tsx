import type { ReactNode } from "react";
import { Button } from "antd";
import { AuditOutlined, QuestionCircleOutlined } from "@ant-design/icons";
import { FEEDBACK_CENTER_ROUTE, FEEDBACK_ROUTE } from "./feedback/navigation";

// 问题反馈入口放在哪（501295，陶国南 11-03）：系统试运行期间天天要用——
// "tab"：顶部栏“工作台”页签右边固定一个“问题反馈”页签（21:34 改成这样），管理员的“问题处理中心”在左侧菜单“工作台”下面；
// "top"：左侧菜单“工作台”下面紧挨着；"bottom"：侧栏左下角（系统稳定后改回这个）。
// 只是显示位置，菜单权限和角色权限树不受影响。
export const FEEDBACK_MENU_PLACEMENT: "tab" | "top" | "bottom" = "tab";

type FeedbackMenuItem = { key: string; label: string; icon?: ReactNode };

// 放在“工作台”后面的菜单项；管理员在下面多一个“问题处理中心”。
export function withFeedbackMenu<T extends FeedbackMenuItem>(items: T[], administrator: boolean): T[] {
  if (FEEDBACK_MENU_PLACEMENT === "bottom") return items;
  const entries = [
    ...(FEEDBACK_MENU_PLACEMENT === "top" ? [{ key: FEEDBACK_ROUTE, label: "问题反馈", icon: <QuestionCircleOutlined /> }] : []),
    ...(administrator ? [{ key: FEEDBACK_CENTER_ROUTE, label: "问题处理中心", icon: <AuditOutlined /> }] : []),
  ] as T[];
  const rest = items.filter((item) => item.key !== FEEDBACK_ROUTE && item.key !== FEEDBACK_CENTER_ROUTE);
  const at = rest.findIndex((item) => item.key === "dashboard");
  return at < 0 ? [...entries, ...rest] : [...rest.slice(0, at + 1), ...entries, ...rest.slice(at + 1)];
}

// 顶部页签：“问题反馈”固定在“工作台”右边，不能关；原来在别处打开的同一页签挪到这里，不会出现两个。
export function withFeedbackTab<T extends { key: string; label: string }>(pages: T[]): T[] {
  if (FEEDBACK_MENU_PLACEMENT !== "tab") return pages;
  const rest = pages.filter((page) => page.key !== FEEDBACK_ROUTE);
  const at = rest.findIndex((page) => page.key === "dashboard");
  const entry = { key: FEEDBACK_ROUTE, label: "问题反馈" } as T;
  return at < 0 ? [entry, ...rest] : [...rest.slice(0, at + 1), entry, ...rest.slice(at + 1)];
}

export const isPinnedFeedbackTab = (key: string) => FEEDBACK_MENU_PLACEMENT === "tab" && key === FEEDBACK_ROUTE;

// 问题反馈入口固定在侧栏左下角，不压在内容区数据上；管理员在下面多一个“问题处理中心”。
export default function BugFeedback({ onOpen, onOpenCenter }: { onOpen: () => void; onOpenCenter?: () => void }) {
  if (FEEDBACK_MENU_PLACEMENT !== "bottom") return null;
  return (
    <>
      <Button className="bug-feedback-trigger" aria-label="问题反馈" title="问题反馈" icon={<QuestionCircleOutlined />} onClick={onOpen}>
        <span className="bug-feedback-label">问题反馈</span>
      </Button>
      {onOpenCenter && (
        <Button className="bug-feedback-trigger bug-feedback-center" aria-label="问题处理中心" title="问题处理中心" icon={<AuditOutlined />} onClick={onOpenCenter}>
          <span className="bug-feedback-label">问题处理中心</span>
        </Button>
      )}
    </>
  );
}

import type { ReactNode } from "react";
import { Button } from "antd";
import { AuditOutlined, QuestionCircleOutlined } from "@ant-design/icons";
import { FEEDBACK_CENTER_ROUTE, FEEDBACK_ROUTE } from "./feedback/navigation";

// 问题反馈入口放在哪（501295，陶国南 11-03），只是显示位置，菜单权限和角色权限树不受影响：
// 顶部栏“工作台”页签右边固定一个“问题反馈”页签（陶国南 21:34 要的，系统稳定后改成 false 去掉）；
export const FEEDBACK_TOP_TAB = true;
// 左侧的“问题反馈”（管理员另有“问题处理中心”）：陶国南 21:41 “左侧的先保留”；
// "bottom"：侧栏最下面（陶威 11-03 要求挪回 1.2.245 之前的位置），手机端侧栏底部按钮不显示，就放在菜单末尾；
// "dashboard"：菜单里“工作台”下面紧挨着。
export const FEEDBACK_SIDEBAR_POSITION: "bottom" | "dashboard" = "bottom";

type FeedbackMenuItem = { key: string; label: string; icon?: ReactNode };

// 左侧菜单里的问题反馈项；电脑端放在最下面时用侧栏底部按钮（BugFeedback），菜单里不再放。
export function withFeedbackMenu<T extends FeedbackMenuItem>(items: T[], administrator: boolean, narrow = false): T[] {
  if (FEEDBACK_SIDEBAR_POSITION === "bottom" && !narrow) return items;
  const entries = [
    { key: FEEDBACK_ROUTE, label: "问题反馈", icon: <QuestionCircleOutlined /> },
    ...(administrator ? [{ key: FEEDBACK_CENTER_ROUTE, label: "问题处理中心", icon: <AuditOutlined /> }] : []),
  ] as T[];
  const rest = items.filter((item) => item.key !== FEEDBACK_ROUTE && item.key !== FEEDBACK_CENTER_ROUTE);
  if (FEEDBACK_SIDEBAR_POSITION === "bottom") return [...rest, ...entries];
  const at = rest.findIndex((item) => item.key === "dashboard");
  return at < 0 ? [...entries, ...rest] : [...rest.slice(0, at + 1), ...entries, ...rest.slice(at + 1)];
}

// 顶部页签：“问题反馈”固定在“工作台”右边，不能关；原来在别处打开的同一页签挪到这里，不会出现两个。
export function withFeedbackTab<T extends { key: string; label: string }>(pages: T[]): T[] {
  if (!FEEDBACK_TOP_TAB) return pages;
  const rest = pages.filter((page) => page.key !== FEEDBACK_ROUTE);
  const at = rest.findIndex((page) => page.key === "dashboard");
  const entry = { key: FEEDBACK_ROUTE, label: "问题反馈" } as T;
  return at < 0 ? [entry, ...rest] : [...rest.slice(0, at + 1), entry, ...rest.slice(at + 1)];
}

export const isPinnedFeedbackTab = (key: string) => FEEDBACK_TOP_TAB && key === FEEDBACK_ROUTE;

// 问题反馈入口固定在侧栏左下角，不压在内容区数据上；管理员在下面多一个“问题处理中心”。
export default function BugFeedback({ onOpen, onOpenCenter }: { onOpen: () => void; onOpenCenter?: () => void }) {
  if (FEEDBACK_SIDEBAR_POSITION !== "bottom") return null;
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

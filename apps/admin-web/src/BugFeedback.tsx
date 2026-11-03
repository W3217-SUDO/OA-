import type { ReactNode } from "react";
import { Button } from "antd";
import { AuditOutlined, QuestionCircleOutlined } from "@ant-design/icons";
import { FEEDBACK_CENTER_ROUTE, FEEDBACK_ROUTE } from "./feedback/navigation";

// 问题反馈入口放在哪（501295，陶国南 11-03）：系统试运行期间天天要用，放到左侧菜单“工作台”下面紧挨着；
// 以后系统稳定了改回 "bottom"，就回到侧栏左下角。只是显示位置，菜单权限和角色权限树不受影响。
export const FEEDBACK_MENU_PLACEMENT: "top" | "bottom" = "top";

type FeedbackMenuItem = { key: string; label: string; icon?: ReactNode };

// 放在“工作台”后面的菜单项；管理员在下面多一个“问题处理中心”。
export function withFeedbackMenu<T extends FeedbackMenuItem>(items: T[], administrator: boolean): T[] {
  if (FEEDBACK_MENU_PLACEMENT !== "top") return items;
  const entries = [
    { key: FEEDBACK_ROUTE, label: "问题反馈", icon: <QuestionCircleOutlined /> },
    ...(administrator ? [{ key: FEEDBACK_CENTER_ROUTE, label: "问题处理中心", icon: <AuditOutlined /> }] : []),
  ] as T[];
  const rest = items.filter((item) => item.key !== FEEDBACK_ROUTE && item.key !== FEEDBACK_CENTER_ROUTE);
  const at = rest.findIndex((item) => item.key === "dashboard");
  return at < 0 ? [...entries, ...rest] : [...rest.slice(0, at + 1), ...entries, ...rest.slice(at + 1)];
}

// 问题反馈入口固定在侧栏左下角，不压在内容区数据上；管理员在下面多一个“问题处理中心”。
export default function BugFeedback({ onOpen, onOpenCenter }: { onOpen: () => void; onOpenCenter?: () => void }) {
  if (FEEDBACK_MENU_PLACEMENT === "top") return null;
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

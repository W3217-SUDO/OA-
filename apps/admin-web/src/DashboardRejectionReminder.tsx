import type { ReactNode } from "react";
import { Empty } from "antd";
import AgentAvatar from "./personal-agent/AgentAvatar";
import type { DashboardRejection } from "./dashboardData";
import { rejectionPrompt } from "./dashboardPrompts";

type Props = {
  items: DashboardRejection[];
  total: number;
  loading: boolean;
  status: ReactNode;
  onOpen: (item: DashboardRejection) => void;
  onAsk: (prompt: string) => void;
};

// 右侧栏：当前账号提交后被驳回的单据，可以直接查看或交给智能体处理。
export default function DashboardRejectionReminder({ items, total, loading, status, onOpen, onAsk }: Props) {
  return (
    <aside className="wb-rail" aria-label="审批驳回提醒">
      <header className="wb-section-head">
        <h3>审批驳回提醒</h3>
        {total > 0 && <span className="wb-count is-alert" title={`共 ${total} 条被驳回`}>{total}</span>}
      </header>
      {status}
      {!loading && !items.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无被驳回的审批" />}
      <ul className="wb-rejection-list">
        {items.map((item) => (
          <li className="wb-rejection" key={`${item.type}-${item.id}`}>
            <div className="wb-rejection-top">
              <span className="wb-rejection-type">{item.type}</span>
              <b title={item.serial_no}>{item.serial_no}</b>
            </div>
            <button type="button" className="wb-rejection-title" title={item.title} onClick={() => onOpen(item)}>{item.title}</button>
            <p className="wb-rejection-reason" title={item.reason}>{item.reason || "未填写驳回原因"}</p>
            <div className="wb-rejection-foot">
              <span className="wb-rejection-by">
                {item.rejected_by && <span>{item.rejected_by} 驳回</span>}
                <time>{item.rejected_at}</time>
              </span>
              <button type="button" className="wb-ask" onClick={() => onAsk(rejectionPrompt(item))}>
                <AgentAvatar size={15} />交给智能体
              </button>
            </div>
          </li>
        ))}
      </ul>
      {total > items.length && <p className="wb-rail-more">仅显示最新 {items.length} 条，其余请进入对应列表查看</p>}
    </aside>
  );
}

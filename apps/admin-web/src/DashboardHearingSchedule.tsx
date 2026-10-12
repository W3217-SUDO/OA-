import { useMemo, type ReactNode } from "react";
import { Button, Empty } from "antd";
import { RightOutlined } from "@ant-design/icons";
import AgentAvatar from "./personal-agent/AgentAvatar";
import dayjs from "dayjs";
import DashboardPersonCell from "./DashboardPersonCell";
import { hearingPrompt } from "./dashboardPrompts";

type Hearing = Record<string, string>;

type Props = {
  hearings: Hearing[];
  loading: boolean;
  status: ReactNode;
  canOpenSchedule: boolean;
  canOpenCase: boolean;
  canOpenCustomer: boolean;
  onOpenSchedule: () => void;
  onOpenCase: (caseNo: string) => void;
  onOpenCustomer: (customer: string) => void;
  onAsk: (prompt: string) => void;
};

function dayHint(date: string) {
  const distance = dayjs(date).startOf("day").diff(dayjs().startOf("day"), "day");
  if (distance === 0) return "今天";
  if (distance === 1) return "明天";
  return "";
}

// 开庭排期按日期排成日程表：左侧是日期，右侧是当天的每一场开庭。
export default function DashboardHearingSchedule({ hearings, loading, status, canOpenSchedule, canOpenCase, canOpenCustomer, onOpenSchedule, onOpenCase, onOpenCustomer, onAsk }: Props) {
  const days = useMemo(() => {
    const byDate = new Map<string, Hearing[]>();
    hearings.forEach((item) => byDate.set(item.date, [...(byDate.get(item.date) || []), item]));
    return Array.from(byDate, ([date, items]) => ({ date, weekday: items[0].weekday.replace("星期", "周"), items }));
  }, [hearings]);
  return (
    <section className="wb-docket" aria-label="开庭排期">
      <header className="wb-section-head">
        <h3>
          {/* 无权查看排期时标题保持纯文本，避免出现点了没反应的入口。 */}
          {canOpenSchedule
            ? <Button type="link" className="wb-title-link" onClick={onOpenSchedule}>开庭排期<RightOutlined /></Button>
            : <span className="wb-title-link">开庭排期</span>}
        </h3>
        {hearings.length > 0 && <span className="wb-count" title={`近期共 ${hearings.length} 场开庭`}>{hearings.length}</span>}
      </header>
      {status}
      <div className="wb-docket-body">
        {!loading && !days.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="近期没有开庭安排" />}
        {days.map((day) => (
          <div className="wb-day" key={day.date}>
            <div className="wb-day-date">
              <span>{dayjs(day.date).format("M月")}</span>
              <strong>{dayjs(day.date).format("D")}</strong>
              <span>{day.weekday}</span>
              {dayHint(day.date) && <em className={dayHint(day.date) === "今天" ? "is-today" : ""}>{dayHint(day.date)}</em>}
            </div>
            <ul className="wb-day-list">
              {day.items.map((item) => (
                <li className="wb-hearing" key={`${item.case_no}-${item.time}`}>
                  <div className="wb-hearing-main">
                    <span className="wb-hearing-time">{item.time}</span>
                    <div className="wb-hearing-body">
                      <b title={item.court}>{item.court || "法院待定"}</b>
                      <span className="wb-hearing-case">
                        {/* 关联案号与客户只在当前账号确实能进入详情时才是链接。 */}
                        {canOpenCase
                          ? <Button type="link" size="small" onClick={() => onOpenCase(item.case_no)}>{item.case_no}</Button>
                          : <span>{item.case_no}</span>}
                        {item.client && (canOpenCustomer
                          ? <Button type="link" size="small" onClick={() => onOpenCustomer(item.client)}>{item.client}</Button>
                          : <span>{item.client}</span>)}
                      </span>
                      <span className="wb-hearing-people">
                        <span><label>开庭</label><DashboardPersonCell value={item.lawyer} /></span>
                        <span><label>经办</label><DashboardPersonCell value={item.agent} /></span>
                        <span><label>助理</label><DashboardPersonCell value={item.assistant} /></span>
                      </span>
                    </div>
                  </div>
                  <button type="button" className="wb-ask" onClick={() => onAsk(hearingPrompt(item))}>
                    <AgentAvatar size={15} />交给智能体
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

import { useCallback, useMemo, useState, type ReactNode } from "react";
import { Button, Empty } from "antd";
import { api } from "./api";
import { RightOutlined } from "@ant-design/icons";
import AgentAvatar from "./personal-agent/AgentAvatar";
import dayjs from "dayjs";
import { hearingPrompt } from "./dashboardPrompts";
import { usePeopleNames } from "./personNames";

type Hearing = Record<string, string>;

type Props = {
  hearings: Hearing[];
  hearingsTotal?: number;
  loading: boolean;
  status: ReactNode;
  canOpenSchedule: boolean;
  canOpenCase: boolean;
  canOpenCustomer: boolean;
  onOpenSchedule: () => void;
  onOpenCase: (caseNo: string) => void;
  onOpenCustomer: (customer: string) => void;
  onOpenHearingAgent: (caseNo: string) => void;
  onAsk: (prompt: string) => void;
};

function dayHint(date: string) {
  const distance = dayjs(date).startOf("day").diff(dayjs().startOf("day"), "day");
  if (distance === 0) return "今天";
  if (distance === 1) return "明天";
  return "";
}

type Scope = "personal" | "company";
const PAGE_SIZE = 13;

// 开庭排期按日期排成日程表：左侧是日期，右侧是当天的每一场开庭。
// 分“个人 / 全所”两个页签（陶国南 11-01 定）：默认看本人相关的开庭，所有人都能切到全所；全所数据多，按页加载。
export default function DashboardHearingSchedule({ hearings, hearingsTotal, loading, status, canOpenSchedule, canOpenCase, canOpenCustomer, onOpenSchedule, onOpenCase, onOpenCustomer, onOpenHearingAgent, onAsk }: Props) {
  const showPeople = usePeopleNames();
  const [scope, setScope] = useState<Scope>("personal");
  const [company, setCompany] = useState<{ rows: Hearing[]; total: number; page: number; loading: boolean; error: string }>(
    { rows: [], total: 0, page: 0, loading: false, error: "" });
  const loadCompany = useCallback(async (page: number) => {
    setCompany((current) => ({ ...current, loading: true, error: "" }));
    try {
      const { data } = await api.get("/dashboard/hearings", { params: { scope: "company", page, page_size: PAGE_SIZE } });
      setCompany((current) => ({
        rows: page === 1 ? data.items || [] : [...current.rows, ...(data.items || [])],
        total: data.total || 0, page, loading: false, error: "",
      }));
    } catch (error: any) {
      setCompany((current) => ({ ...current, loading: false, error: error?.response?.data?.detail || "全所开庭排期加载失败" }));
    }
  }, []);
  const switchScope = (next: Scope) => {
    setScope(next);
    if (next === "company") void loadCompany(1);
  };
  const shown = scope === "company" ? company.rows : hearings;
  const total = scope === "company" ? company.total : (hearingsTotal ?? hearings.length);
  const busy = scope === "company" ? company.loading && !company.rows.length : loading;
  const days = useMemo(() => {
    const byDate = new Map<string, Hearing[]>();
    shown.forEach((item) => byDate.set(item.date, [...(byDate.get(item.date) || []), item]));
    return Array.from(byDate, ([date, items]) => ({ date, weekday: items[0].weekday.replace("星期", "周"), items }));
  }, [shown]);
  return (
    <section className="wb-docket" aria-label="开庭排期">
      <header className="wb-section-head">
        <h3>
          {/* 无权查看排期时标题保持纯文本，避免出现点了没反应的入口。 */}
          {canOpenSchedule
            ? <Button type="link" className="wb-title-link" onClick={onOpenSchedule}>开庭排期<RightOutlined /></Button>
            : <span className="wb-title-link">开庭排期</span>}
        </h3>
        <span className="wb-docket-tools">
          <span className="wb-docket-scope" role="tablist" aria-label="开庭范围">
            {([["personal", "个人"], ["company", "全所"]] as const).map(([value, label]) => (
              <Button key={value} size="small" role="tab" aria-selected={scope === value}
                type={scope === value ? "primary" : "default"} onClick={() => scope !== value && switchScope(value)}>
                {label}
              </Button>
            ))}
          </span>
          {total > 0 && <span className="wb-count" title={`近期共 ${total} 场开庭`}>{total}</span>}
        </span>
      </header>
      {scope === "personal" ? status : company.error ? <div className="dashboard-section-status" role="alert">{company.error}</div> : null}
      <div className="wb-docket-body">
        {!busy && !days.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="近期没有开庭安排" />}
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
                  {/* 第一行：时间、法院（完整显示）和“交给智能体”；下面整行宽度给案件信息，开庭/经办/助理排在一行。 */}
                  <div className="wb-hearing-top">
                    <span className="wb-hearing-time">{item.time}</span>
                    <b className="wb-hearing-court">{item.court || "法院待定"}</b>
                    <button type="button" className="wb-ask" title="交给智能体" aria-label="交给智能体" onClick={() => canOpenCase ? onOpenHearingAgent(item.case_no) : onAsk(hearingPrompt(item))}>
                      <AgentAvatar size={15} />智能体
                    </button>
                  </div>
                  <div className="wb-hearing-detail">
                    <span className="wb-hearing-case">
                      {/* 关联案号与客户只在当前账号确实能进入详情时才是链接。 */}
                      {canOpenCase
                        ? <Button type="link" size="small" onClick={() => onOpenCase(item.case_no)}>{item.case_no}</Button>
                        : <span>{item.case_no}</span>}
                      {item.client && (canOpenCustomer
                        ? <Button type="link" size="small" onClick={() => onOpenCustomer(item.client)}>{item.client}</Button>
                        : <span>{item.client}</span>)}
                    </span>
                    {(item.hearing_type || item.courtroom || item.stage) && (
                      <span className="wb-hearing-meta">
                        {item.hearing_type && <span className="wb-hearing-type">{item.hearing_type}</span>}
                        {item.courtroom && <span>{item.courtroom}</span>}
                        {item.stage && <span><label>阶段</label>{item.stage}</span>}
                      </span>
                    )}
                    {item.opponent && <span className="wb-hearing-opponent"><label>对方</label>{item.opponent}</span>}
                    <span className="wb-hearing-people">
                      <span><label>开庭</label>{showPeople(item.lawyer)}</span>
                      <span><label>经办</label>{showPeople(item.agent)}</span>
                      <span><label>助理</label>{showPeople(item.assistant)}</span>
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {scope === "company" && company.rows.length < company.total && (
          <div className="wb-docket-more">
            <Button size="small" loading={company.loading} onClick={() => void loadCompany(company.page + 1)}>
              加载更多（已显示 {company.rows.length} / {company.total}）
            </Button>
          </div>
        )}
      </div>
    </section>
  );
}

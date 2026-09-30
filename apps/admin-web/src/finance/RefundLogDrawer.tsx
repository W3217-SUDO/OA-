import { Alert, Button, Drawer, Empty, Spin } from "antd";
import dayjs from "dayjs";
import { useEffect, useLayoutEffect, useMemo, useState } from "react";
import { api } from "../api";
import "./refund-log-drawer.css";

type RefundLog = {
  id: number | string;
  content: string;
  operator: string;
  operator_display_name?: string;
  created_at: string | null;
  source: string;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; items: RefundLog[] };

type Props = {
  feeId: number;
  onClose: () => void;
  personDisplayName: (identity: unknown, displayName?: unknown) => string;
};

export function RefundLogDrawer({ feeId, onClose, personDisplayName }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [headerBottom, setHeaderBottom] = useState<number>();

  useLayoutEffect(() => {
    const topbar = document.querySelector(".topbar");
    if (!topbar) return;
    const updateTop = () => setHeaderBottom(topbar.getBoundingClientRect().bottom);
    updateTop();
    const observer = new ResizeObserver(updateTop);
    observer.observe(topbar);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    api.get<{ items: RefundLog[] }>("/finance/case-fees/refunds/logs", {
      params: { fee_id: feeId },
      signal: controller.signal,
    }).then(({ data }) => {
      if (!controller.signal.aborted) setState({ status: "loaded", items: data.items });
    }).catch((error: any) => {
      if (controller.signal.aborted) return;
      const detail = error?.response?.data?.detail;
      setState({ status: "error", message: typeof detail === "string" ? detail : "退费日志加载失败，请重试" });
    });
    return () => controller.abort();
  }, [feeId, attempt]);

  const groups = useMemo(() => {
    if (state.status !== "loaded") return [];
    const entries = state.items.map((item) => {
      const date = dayjs(item.created_at);
      return { item, date, timestamp: date.isValid() ? date.valueOf() : -Infinity };
    }).sort((left, right) => right.timestamp - left.timestamp);
    const months = new Map<string, typeof entries>();
    for (const entry of entries) {
      const month = entry.date.isValid() ? entry.date.format("YYYY-MM") : "日期未记录";
      const entriesInMonth = months.get(month);
      if (entriesInMonth) entriesInMonth.push(entry);
      else months.set(month, [entry]);
    }
    return [...months].map(([month, entriesInMonth]) => ({ month, entries: entriesInMonth }));
  }, [state]);

  return (
    <Drawer
      open
      title="查看日志"
      placement="right"
      width="min(600px, 100vw)"
      mask={false}
      closable={{ placement: "end" }}
      rootClassName="refund-log-drawer"
      rootStyle={{ top: headerBottom }}
      onClose={onClose}
      footer={<Button onClick={onClose}>关闭</Button>}
    >
      {state.status === "loading" && (
        <div className="refund-log-state" role="status"><Spin />正在加载日志</div>
      )}
      {state.status === "error" && (
        <Alert
          type="error"
          showIcon
          message={state.message}
          action={<Button onClick={() => setAttempt((value) => value + 1)}>重试</Button>}
        />
      )}
      {state.status === "loaded" && (groups.length === 0 ? (
        <Empty description="暂无日志" />
      ) : (
        <div className="refund-log-timeline">
          {groups.map(({ month, entries }) => (
            <section className="refund-log-month" key={month} aria-label={month}>
              <h3>{month}</h3>
              {entries.map(({ item, date }) => (
                <article className="refund-log-entry" key={`${item.source}:${item.id}`}>
                  <div className="refund-log-date">
                    {date.isValid() ? <time dateTime={item.created_at!}>{date.format("YYYY-MM-DD")}</time> : "日期未记录"}
                  </div>
                  <p className="refund-log-content">
                    <span className="refund-log-operator">{personDisplayName(item.operator, item.operator_display_name)}：</span>{item.content}
                  </p>
                </article>
              ))}
            </section>
          ))}
        </div>
      ))}
    </Drawer>
  );
}

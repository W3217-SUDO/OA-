import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Card, Segmented } from "antd";
import { api } from "../api";
import FeedbackManager, { FEEDBACK_GROUP_STATUSES, type FeedbackView } from "./FeedbackManager";
import { FEEDBACK_SOURCE_ROUTE_KEY, feedbackPageLabel, readFeedbackPageControls, scrollFeedbackToTop, type FeedbackPageOption } from "./navigation";
import { hasFeedbackDraft } from "./draft";
import type { FeedbackStatusCounts } from "./types";
import "./feedback.css";

type Props = {
  onNavigate: (route: string) => void;
  openPages: FeedbackPageOption[];
  menuPages: FeedbackPageOption[];
  resolvePageLabel: (route: string) => string;
};

export default function FeedbackPage({ onNavigate, openPages, menuPages, resolvePageLabel }: Props) {
  const [sourceRoute] = useState(() => sessionStorage.getItem(FEEDBACK_SOURCE_ROUTE_KEY) || "");
  const [pageControls] = useState(readFeedbackPageControls);
  // 从某个页面点“问题反馈”进来先填写；直接打开（如从通知、页签）先看处理中的（tgn 11-01，BUG20261101005）。
  // 有没提交的草稿时，切到别的页签再回来也先回到填写页，已填内容原样保留（高勤兰 11-02，BUG20261102002）。
  const [view, setView] = useState<FeedbackView>(sourceRoute || hasFeedbackDraft() ? "create" : "open");
  const [navKey, setNavKey] = useState(0);
  const [counts, setCounts] = useState<Record<string, number> | null>(null);
  const [countKey, setCountKey] = useState(0);
  const headRef = useRef<HTMLDivElement>(null);
  // 点页签（包括再点当前页签）回到对应列表，并把页面滚回顶部，不用再往上拖（tgn 11-05，BUG20261105023）。
  const switchView = (value: FeedbackView) => {
    setView(value);
    setNavKey((key) => key + 1);
    scrollFeedbackToTop(headRef.current);
  };
  const returnToSource = () => onNavigate(sourceRoute || "dashboard");
  // 来源页可能是详情等非菜单页面，补进快捷选项并带上可读名称。
  const pages = useMemo(() => {
    const merged = sourceRoute && !openPages.some((page) => page.key === sourceRoute)
      ? [{ key: sourceRoute, label: resolvePageLabel(sourceRoute) }, ...openPages] : openPages;
    return merged.map((page) => ({ ...page, label: feedbackPageLabel(page.key, page.label) }));
  }, [sourceRoute, openPages, resolvePageLabel]);

  // 详情按钮行吸在页头下面：页头高度随宽度变化（手机上页签换行），量出来交给样式（ResizeObserver，Chrome 100 支持）。
  useEffect(() => {
    const head = headRef.current?.closest<HTMLElement>(".ant-card-head");
    const card = head?.parentElement;
    if (!head || !card || typeof ResizeObserver === "undefined") return;
    const update = () => card.style.setProperty("--feedback-head-h", `${head.offsetHeight}px`);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(head);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    void api.get<FeedbackStatusCounts>("/feedback/status-counts", { params: { mine: true } })
      .then(({ data }) => { if (!cancelled) setCounts(data.counts); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [countKey]);

  const groupCount = (group: "open" | "closed") => counts
    ? ` ${FEEDBACK_GROUP_STATUSES[group].reduce((sum, value) => sum + (counts[value] ?? 0), 0)}` : "";

  return <Card className="panel feedback-page-card" title={<div className="feedback-page-head" ref={headRef}
      onClickCapture={(event) => {
        const item = (event.target as HTMLElement).closest(".ant-segmented-item-selected");
        if (item && headRef.current?.contains(item)) switchView(view);
      }}>
      <span>我的反馈</span>
      <Segmented value={view} aria-label="切换提交反馈、处理中和已解决"
        options={[{ value: "create", label: "提交反馈" }, { value: "open", label: `处理中${groupCount("open")}` },
          { value: "closed", label: `已解决${groupCount("closed")}` }]}
        onChange={(value) => switchView(value as FeedbackView)} />
    </div>}
    extra={<Button onClick={returnToSource}>{sourceRoute ? "返回原页面" : "返回工作台"}</Button>}>
    <FeedbackManager sourceRoute={sourceRoute} pageControls={pageControls} openPages={pages} menuPages={menuPages}
      onNavigate={onNavigate} view={view} onViewChange={setView} navKey={navKey}
      onChanged={() => setCountKey((key) => key + 1)} />
  </Card>;
}

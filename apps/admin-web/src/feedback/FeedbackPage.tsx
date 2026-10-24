import { useEffect, useMemo, useState } from "react";
import { Button, Card, Segmented } from "antd";
import { api } from "../api";
import FeedbackManager from "./FeedbackManager";
import { FEEDBACK_SOURCE_ROUTE_KEY, feedbackPageLabel, readFeedbackPageControls, type FeedbackPageOption } from "./navigation";
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
  // 从某个页面点“问题反馈”进来先填写；直接打开（如从通知、页签）先看我的反馈。
  const [view, setView] = useState<"create" | "mine">(sourceRoute ? "create" : "mine");
  const [navKey, setNavKey] = useState(0);
  const [mineCount, setMineCount] = useState<number | null>(null);
  const [countKey, setCountKey] = useState(0);
  const returnToSource = () => onNavigate(sourceRoute || "dashboard");
  // 来源页可能是详情等非菜单页面，补进快捷选项并带上可读名称。
  const pages = useMemo(() => {
    const merged = sourceRoute && !openPages.some((page) => page.key === sourceRoute)
      ? [{ key: sourceRoute, label: resolvePageLabel(sourceRoute) }, ...openPages] : openPages;
    return merged.map((page) => ({ ...page, label: feedbackPageLabel(page.key, page.label) }));
  }, [sourceRoute, openPages, resolvePageLabel]);

  useEffect(() => {
    let cancelled = false;
    void api.get<FeedbackStatusCounts>("/feedback/status-counts", { params: { mine: true } })
      .then(({ data }) => { if (!cancelled) setMineCount(data.total); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [countKey]);

  return <Card className="panel feedback-page-card" title={<div className="feedback-page-head">
      <span>问题反馈</span>
      <Segmented value={view} aria-label="切换提交反馈和我的反馈"
        options={[{ value: "create", label: "提交反馈" }, { value: "mine", label: `我的反馈${mineCount ? ` ${mineCount}` : ""}` }]}
        onChange={(value) => { setView(value as "create" | "mine"); setNavKey((key) => key + 1); }} />
    </div>}
    extra={<Button onClick={returnToSource}>{sourceRoute ? "返回原页面" : "返回工作台"}</Button>}>
    <FeedbackManager sourceRoute={sourceRoute} pageControls={pageControls} openPages={pages} menuPages={menuPages}
      onNavigate={onNavigate} view={view} onViewChange={setView} navKey={navKey}
      onChanged={() => setCountKey((key) => key + 1)} />
  </Card>;
}

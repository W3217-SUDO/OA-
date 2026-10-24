import { useMemo, useState } from "react";
import { Button, Card } from "antd";
import FeedbackManager from "./FeedbackManager";
import { FEEDBACK_SOURCE_ROUTE_KEY, feedbackPageLabel, readFeedbackPageControls, type FeedbackPageOption } from "./navigation";

type Props = {
  onNavigate: (route: string) => void;
  openPages: FeedbackPageOption[];
  menuPages: FeedbackPageOption[];
  resolvePageLabel: (route: string) => string;
};

export default function FeedbackPage({ onNavigate, openPages, menuPages, resolvePageLabel }: Props) {
  const [sourceRoute] = useState(() => sessionStorage.getItem(FEEDBACK_SOURCE_ROUTE_KEY) || "");
  const [pageControls] = useState(readFeedbackPageControls);
  const returnToSource = () => onNavigate(sourceRoute || "dashboard");
  // 来源页可能是详情等非菜单页面，补进快捷选项并带上可读名称。
  const pages = useMemo(() => {
    const merged = sourceRoute && !openPages.some((page) => page.key === sourceRoute)
      ? [{ key: sourceRoute, label: resolvePageLabel(sourceRoute) }, ...openPages] : openPages;
    return merged.map((page) => ({ ...page, label: feedbackPageLabel(page.key, page.label) }));
  }, [sourceRoute, openPages, resolvePageLabel]);

  return <Card className="panel" title="问题反馈"
    extra={<Button onClick={returnToSource}>{sourceRoute ? "返回原页面" : "返回工作台"}</Button>}>
    <FeedbackManager sourceRoute={sourceRoute} pageControls={pageControls} openPages={pages} menuPages={menuPages} onNavigate={onNavigate} />
  </Card>;
}

import { useState } from "react";
import { Button, Card } from "antd";
import FeedbackManager from "./FeedbackManager";
import { FEEDBACK_SOURCE_PAGE_KEY, FEEDBACK_SOURCE_ROUTE_KEY } from "./navigation";

type Props = { onNavigate: (route: string) => void };

export default function FeedbackPage({ onNavigate }: Props) {
  const [sourcePage] = useState(() => sessionStorage.getItem(FEEDBACK_SOURCE_PAGE_KEY) || "");
  const [sourceRoute] = useState(() => sessionStorage.getItem(FEEDBACK_SOURCE_ROUTE_KEY));
  const returnToSource = () => onNavigate(sourceRoute || "dashboard");

  return <Card className="panel" title="问题反馈"
    extra={<Button onClick={returnToSource}>{sourceRoute ? "返回原页面" : "返回控制台"}</Button>}>
    <FeedbackManager sourcePage={sourcePage} />
  </Card>;
}

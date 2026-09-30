import { useState } from "react";
import { Button, Card } from "antd";
import FeedbackForm from "./FeedbackForm";
import FeedbackManager from "./FeedbackManager";
import { FEEDBACK_SOURCE_PAGE_KEY, FEEDBACK_SOURCE_ROUTE_KEY } from "./navigation";

type Props = { isAdmin: boolean; onNavigate: (route: string) => void };

export default function FeedbackPage({ isAdmin, onNavigate }: Props) {
  const [sourcePage] = useState(() => sessionStorage.getItem(FEEDBACK_SOURCE_PAGE_KEY) || "");
  const [sourceRoute] = useState(() => sessionStorage.getItem(FEEDBACK_SOURCE_ROUTE_KEY));
  const returnToSource = () => onNavigate(sourceRoute || "dashboard");

  return <Card className="panel" title="问题反馈"
    extra={<Button onClick={returnToSource}>{sourceRoute ? "返回原页面" : "返回控制台"}</Button>}>
    {isAdmin
      ? <FeedbackManager sourcePage={sourcePage} />
      : <FeedbackForm sourcePage={sourcePage} onCancel={returnToSource} />}
  </Card>;
}

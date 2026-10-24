import { Card } from "antd";
import FeedbackManager from "./FeedbackManager";

type Props = { onNavigate: (route: string) => void };

// 问题处理中心：管理员在这里看全部用户的反馈，指派处理人、回复和改状态（详情里的操作沿用反馈详情）。
export default function FeedbackCenterPage({ onNavigate }: Props) {
  return <Card className="panel" title="问题处理中心">
    <FeedbackManager center sourceRoute="" pageControls={{}} openPages={[]} menuPages={[]} onNavigate={onNavigate} />
  </Card>;
}

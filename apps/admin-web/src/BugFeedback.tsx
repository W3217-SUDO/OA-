import { Button } from "antd";
import { QuestionCircleOutlined } from "@ant-design/icons";

// 问题反馈入口固定在侧栏左下角，不压在内容区数据上。
export default function BugFeedback({ onOpen }: { onOpen: () => void }) {
  return (
    <Button className="bug-feedback-trigger" aria-label="问题反馈" title="问题反馈" icon={<QuestionCircleOutlined />} onClick={onOpen}>
      <span className="bug-feedback-label">问题反馈</span>
    </Button>
  );
}

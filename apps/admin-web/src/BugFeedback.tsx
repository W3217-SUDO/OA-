import { Button } from "antd";

export default function BugFeedback({ onOpen }: { onOpen: () => void }) {
  return <Button className="bug-feedback-trigger" aria-label="问题反馈" title="问题反馈" onClick={onOpen}>问题反馈</Button>;
}

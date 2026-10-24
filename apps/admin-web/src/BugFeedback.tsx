import { Button } from "antd";
import { AuditOutlined, QuestionCircleOutlined } from "@ant-design/icons";

// 问题反馈入口固定在侧栏左下角，不压在内容区数据上；管理员在下面多一个“问题处理中心”。
export default function BugFeedback({ onOpen, onOpenCenter }: { onOpen: () => void; onOpenCenter?: () => void }) {
  return (
    <>
      <Button className="bug-feedback-trigger" aria-label="问题反馈" title="问题反馈" icon={<QuestionCircleOutlined />} onClick={onOpen}>
        <span className="bug-feedback-label">问题反馈</span>
      </Button>
      {onOpenCenter && (
        <Button className="bug-feedback-trigger bug-feedback-center" aria-label="问题处理中心" title="问题处理中心" icon={<AuditOutlined />} onClick={onOpenCenter}>
          <span className="bug-feedback-label">问题处理中心</span>
        </Button>
      )}
    </>
  );
}

type Props = {
  size?: number;
  className?: string;
};

// 智能体头像：统一用新的全身形象（v6，陶威 11-03 认可）里的头部，左栏、对话、工作台、案件智能体等所有地方一致。
// 透明背景 webp（128px，约 6KB），钉钉 Chrome 100 内核支持；不参与无障碍朗读。
export const AGENT_HEAD_SRC = "/assets/agent/agent-head.webp";

export default function AgentAvatar({ size = 32, className }: Props) {
  return (
    <img className={`agent-avatar${className ? ` ${className}` : ""}`} src={AGENT_HEAD_SRC} width={size} height={size} alt="" aria-hidden="true" draggable={false} />
  );
}

// 放在按钮、菜单、标题里代替图标：带 anticon 类，间距和原来的图标一样。
export function AgentIcon({ size = 16 }: { size?: number }) {
  return <span role="img" aria-hidden="true" className="anticon agent-icon"><AgentAvatar size={size} /></span>;
}

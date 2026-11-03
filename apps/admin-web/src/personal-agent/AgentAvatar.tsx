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

// 彩色头像当图标用（如案件智能体右侧收起按钮）：带 anticon 类，原来图标上的眨眼、点头动画照样生效。
export function AgentHeadIcon({ size = 16 }: { size?: number }) {
  return <span role="img" aria-hidden="true" className="anticon agent-icon"><AgentAvatar size={size} /></span>;
}

// 线条图标版（陶威 11-03）：同一个小机器人的轮廓（圆角方头、两侧耳朵、天线小球、眼睛和笑脸），
// 颜色跟随所在位置的文字色（currentColor），放在深色/浅色导航栏、按钮、标题里都和其他图标一致。不写 size 时随字号（1em）。
export function AgentIcon({ size }: { size?: number }) {
  const dimension = size ?? "1em";
  return (
    <span role="img" aria-hidden="true" className="anticon agent-line-icon">
      <svg width={dimension} height={dimension} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" focusable="false">
        <path d="M12 7V4.6" />
        <circle cx="12" cy="3.2" r="1.5" fill="currentColor" stroke="none" />
        <rect x="4.6" y="7" width="14.8" height="13" rx="5" />
        <rect x="1.9" y="11" width="2.7" height="5.2" rx="1.35" fill="currentColor" stroke="none" />
        <rect x="19.4" y="11" width="2.7" height="5.2" rx="1.35" fill="currentColor" stroke="none" />
        <circle cx="9.4" cy="12.8" r="1.35" fill="currentColor" stroke="none" />
        <circle cx="14.6" cy="12.8" r="1.35" fill="currentColor" stroke="none" />
        <path d="M10 16.1q2 1.5 4 0" />
      </svg>
    </span>
  );
}

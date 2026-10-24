type Props = {
  size?: number;
  className?: string;
};

// 形象的主体颜色取当前主题色（theme.css 里的 --oa-agent-* 变量），切换主题时头像跟着变；天线小球和腮红保持原色。
// 不在内联样式里写 color-mix：钉钉手机内核不认识，会整块变黑；旧内核上这些变量由主题模块按当前主题色算好写入。
const BODY = { fill: "var(--oa-agent-body)" };
const DARK = { fill: "var(--oa-agent-dark)" };
const DARK_STROKE = { stroke: "var(--oa-agent-dark)" };
const FACE = { fill: "var(--oa-agent-face)" };
const INK = { fill: "var(--oa-agent-ink)" };
const INK_STROKE = { stroke: "var(--oa-agent-ink)" };

// 工作台智能体的卡通形象：圆脑袋、大眼睛、腮红和小天线。纯色填充，同一页面里多次出现也不会互相影响，且不参与无障碍朗读。
export default function AgentAvatar({ size = 32, className }: Props) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 48 48" role="presentation" aria-hidden="true" focusable="false">
      <path d="M24 10V6" style={DARK_STROKE} strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="24" cy="4.6" r="3" fill="#ffc53d" style={DARK_STROKE} strokeWidth="1.4" />
      <rect x="1.5" y="20" width="6.5" height="13" rx="3.25" style={DARK} />
      <rect x="40" y="20" width="6.5" height="13" rx="3.25" style={DARK} />
      <rect x="7" y="9" width="34" height="33" rx="14" style={BODY} />
      <rect x="11.5" y="14.5" width="25" height="21" rx="10.5" style={FACE} />
      <ellipse cx="19" cy="24" rx="2.7" ry="3.3" style={INK} />
      <ellipse cx="29" cy="24" rx="2.7" ry="3.3" style={INK} />
      <circle cx="20" cy="22.8" r="1" fill="#ffffff" />
      <circle cx="30" cy="22.8" r="1" fill="#ffffff" />
      <path d="M21.2 29.6q2.8 2.6 5.6 0" style={INK_STROKE} strokeWidth="1.7" strokeLinecap="round" fill="none" />
      <ellipse cx="14.8" cy="29" rx="2.3" ry="1.5" fill="#ff9db0" opacity=".85" />
      <ellipse cx="33.2" cy="29" rx="2.3" ry="1.5" fill="#ff9db0" opacity=".85" />
    </svg>
  );
}

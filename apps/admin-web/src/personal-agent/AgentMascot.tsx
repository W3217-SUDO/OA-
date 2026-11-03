import type { CSSProperties } from "react";

// 智能体全身形象（陶威 11-03 认可的 v6，Asset Generator 出图）：首页欢迎用招手，思考中用悬浮，空状态用抱平板，完成提示用点赞。
// 32px 小头像、左栏和对话头像仍用 AgentAvatar / ai-assistant-logo.png，不用这里。
export type AgentMascotPose = "wave" | "float" | "tablet" | "thumbsup";

// 各姿势图片的宽高比（图片 320px 高，按 2 倍显示尺寸压成 webp，每张约 15KB）。
const RATIO: Record<AgentMascotPose, number> = { wave: 223 / 320, float: 232 / 320, tablet: 236 / 320, thumbsup: 228 / 320 };

// 招手图上两只眼睛的位置（占图片宽高的百分比），眨眼时在这里盖一层和脸同色的眼皮。
const WAVE_EYES = [
  { left: 32, top: 30, width: 13.4, height: 11.6 },
  { left: 56, top: 32.8, width: 13.8, height: 11.2 },
];

export default function AgentMascot({ pose, height, blink = false, bob = false, className }: {
  pose: AgentMascotPose;
  height: number;
  blink?: boolean;
  bob?: boolean;
  className?: string;
}) {
  const width = Math.round(height * RATIO[pose]);
  return (
    <span className={`agent-mascot${bob ? " is-bob" : ""}${className ? ` ${className}` : ""}`} style={{ width, height }} aria-hidden="true">
      <img src={`/assets/agent/agent-${pose}.webp`} alt="" width={width} height={height} draggable={false} />
      {blink && pose === "wave" && WAVE_EYES.map((eye, index) => (
        <i key={index} className="agent-mascot-lid" style={{ left: `${eye.left}%`, top: `${eye.top}%`, width: `${eye.width}%`, height: `${eye.height}%` } as CSSProperties} />
      ))}
    </span>
  );
}

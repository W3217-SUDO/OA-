import type { ReactNode } from "react";
import AgentAvatar from "./personal-agent/AgentAvatar";

// 工作台顶部的问候语：头像、称呼和今天的开庭与驳回概况，占用原页面标题的位置。
export default function DashboardGreeting({ greeting, name, briefing }: { greeting: string; name?: string; briefing: ReactNode }) {
  return (
    <header className="wb-greeting">
      <div className="wb-greeting-mark"><AgentAvatar size={32} /></div>
      <div className="wb-greeting-text">
        <h2>{greeting}{name ? `，${name}` : ""}</h2>
        <p>{briefing}</p>
      </div>
    </header>
  );
}

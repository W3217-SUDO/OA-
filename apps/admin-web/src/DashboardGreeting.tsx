import type { ReactNode } from "react";
import AgentAvatar from "./personal-agent/AgentAvatar";

// 工作概况头部的问候语，只随概况视图显示，不占用助手对话或全局标题。
export default function DashboardGreeting({ greeting, name, briefing }: { greeting: string; name?: string; briefing: ReactNode }) {
  return (
    <div className="wb-greeting">
      <div className="wb-greeting-mark"><AgentAvatar size={32} /></div>
      <div className="wb-greeting-text">
        <h2>{greeting}{name ? `，${name}` : ""}</h2>
        <p>{briefing}</p>
      </div>
    </div>
  );
}

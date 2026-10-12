import type { CaseLitigantAgent } from "./types";

export const normalizeCaseLitigantAgents = (value: unknown): CaseLitigantAgent[] => {
  const serialized = Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value.join(",")
    : typeof value === "string" ? value : "";
  // 历史导入曾按逗号拆分代理人 JSON，先重组并解码，再读取姓名及身份。
  const agents: unknown = /^\s*\[\s*(?:\{|"|\])/.test(serialized) ? JSON.parse(serialized) : value;
  return Array.isArray(agents)
    ? agents.map((item) => {
      if (typeof item === "string") return { name: item, law_firm: "", position: "", phone: "", authority: "" };
      const agent = item && typeof item === "object" ? item as Record<string, unknown> : {};
      return {
        name: String(agent.name ?? agent.Name ?? "").trim(),
        law_firm: String(agent.law_firm || "").trim(),
        position: String(agent.position ?? agent.Position ?? "").trim(),
        phone: String(agent.phone || "").trim(),
        authority: String(agent.authority ?? agent.AgentAuthCode ?? "").trim(),
      };
    }).filter((agent) => agent.name)
    : [];
};

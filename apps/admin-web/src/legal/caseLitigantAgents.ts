import type { CaseLitigantAgent } from "./types";

export class CaseLitigantAgentDataError extends Error {
  readonly cause: SyntaxError;

  constructor(cause: SyntaxError) {
    super("代理人历史数据格式错误，请核对原始记录");
    this.name = "CaseLitigantAgentDataError";
    this.cause = cause;
  }
}

export const normalizeCaseLitigantAgents = (value: unknown): CaseLitigantAgent[] => {
  const serialized = Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value.join(",")
    : typeof value === "string" ? value : "";
  // 历史导入曾按逗号拆分代理人 JSON，先重组并解码，再读取姓名及身份。
  let agents: unknown = value;
  if (/^\s*\[\s*(?:\{|"|\])/.test(serialized)) {
    try {
      agents = JSON.parse(serialized);
    } catch (error) {
      if (error instanceof SyntaxError) throw new CaseLitigantAgentDataError(error);
      throw error;
    }
  }
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

export const normalizeCaseLitigantAgentFields = (data: Record<string, unknown>) => ({
  plaintiff_agents: normalizeCaseLitigantAgents(data.plaintiff_agents),
  defendant_agents: normalizeCaseLitigantAgents(data.defendant_agents),
  third_party_agents: normalizeCaseLitigantAgents(data.third_party_agents),
});

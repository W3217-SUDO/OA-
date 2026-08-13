export type AgentSkill = {
  id: string;
  name: string;
  category: string;
  description: string;
  source: string;
  available: boolean;
  unavailable_reason: string;
  quick_prompts: string[];
};

export const DEFAULT_AGENT_SKILL = "general-office";

export function encodeAgentSkillMessage(skillId: string, message: string) {
  const normalized = String(skillId || DEFAULT_AGENT_SKILL).trim();
  return `[[skill:${normalized}]]\n${message.trim()}`;
}

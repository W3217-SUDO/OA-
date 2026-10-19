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
export const NO_AGENT_SKILL_OPTION = { value: "", label: "不使用附加技能" };

export function availableAgentSkillId(skillId: string, skills: { id: string; available: boolean }[]) {
  return skills.some(item => item.id === skillId && item.available) ? skillId : "";
}

export function encodeAgentSkillMessage(skillId: string, message: string) {
  const normalized = skillId.trim();
  return normalized ? `[[skill:${normalized}]]\n${message.trim()}` : message.trim();
}

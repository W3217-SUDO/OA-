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
// 收文助手：专用对话固定使用法院收文技能，用户只需粘贴送达短信或链接。
export const COURT_INTAKE_SKILL = "court-doc-intake";
export const NO_AGENT_SKILL_OPTION = { value: "", label: "不使用附加技能" };

// 智能体中心的固定任务入口（501141）：点开新建一条对话，带好技能和开场提示。
export type AgentTaskEntry = { key: string; label: string; hint: string; skillId: string; prompt: string; greeting: string };
export const AGENT_TASK_ENTRIES: AgentTaskEntry[] = [
  { key: "tasks", label: "任务处理", hint: "查我的任务，完成、转交、延期", skillId: "my-tasks", prompt: "我有哪些任务",
    greeting: "我会按已逾期、今天到期、本周到期汇总你负责的任务，再按你的答复完成、转交或延期；每一步操作前都会先请你确认。" },
  { key: "intake", label: "收文处理", hint: "粘贴法院短信，自动收文入库", skillId: COURT_INTAKE_SKILL, prompt: "",
    greeting: "把法院送达短信或链接粘贴到下面，我会自动下载文书、匹配案件、收文入库并回填法院案号和开庭；缴费通知会先问你再提交缴纳。" },
  { key: "customer", label: "客户与合同", hint: "新建客户、合同、案件、费用，申请开票", skillId: "customer-contract-case", prompt: "",
    greeting: "告诉我客户名称和要办的事，或者发来合同扫描件。我会按顺序办理新建客户、新建合同并提交审批、立案、新建案件费用、申请开票，每一步都先请你确认。" },
];
export const taskEntryForSkill = (skillId: string) => AGENT_TASK_ENTRIES.find((item) => item.skillId === skillId);

export function availableAgentSkillId(skillId: string, skills: { id: string; available: boolean }[]) {
  return skills.some(item => item.id === skillId && item.available) ? skillId : "";
}

export function encodeAgentSkillMessage(skillId: string, message: string) {
  const normalized = skillId.trim();
  return normalized ? `[[skill:${normalized}]]\n${message.trim()}` : message.trim();
}

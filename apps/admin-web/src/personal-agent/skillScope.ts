import type { WorkspaceSkill } from "./types";

export type SkillScope = "personal" | "global";
export const skillBase = (scope: SkillScope) => scope === "global" ? "/agent/global-skills" : "/agent/skills";
export const skillScopeLabel = (scope: SkillScope) => scope === "global" ? "全局技能" : "个人技能";
export const managedSkills = (items: WorkspaceSkill[], scope: SkillScope) => items.filter(item => item.custom && (item.scope === scope || (scope === "personal" && !item.scope)));
export const skillChoiceLabel = (item: WorkspaceSkill) => item.scope === "global" ? `${item.name} · 全局` : item.custom ? `${item.name} · 个人` : item.name;

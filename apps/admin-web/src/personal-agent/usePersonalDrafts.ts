import { useRef, useState, type SetStateAction } from "react";
import { DEFAULT_AGENT_SKILL } from "../agentSkillRouting";
import type { DecisionFailure, Material, ResponseMode, WorkspaceCase, WorkspaceSkill } from "./types";

type Draft = { input: string; skillId: string; responseMode: ResponseMode; materials: Material[]; caseMaterials: Material[]; selectedCase: WorkspaceCase | null; savedDocuments: Record<number, string>; decisionResult?: unknown; decisionFailures: Record<string, DecisionFailure> };
export const EMPTY_PERSONAL_DRAFT: Draft = { input: "", skillId: DEFAULT_AGENT_SKILL, responseMode: "fast", materials: [], caseMaterials: [], selectedCase: null, savedDocuments: {}, decisionFailures: {} };

export function usePersonalDrafts() {
  const [items, setItems] = useState<Record<string, Draft>>({});
  const ref = useRef<Record<string, Draft>>({});
  const replace = (next: Record<string, Draft>) => { ref.current = next; setItems(next); };
  const update = <K extends keyof Draft>(target: string, key: K, value: SetStateAction<Draft[K]>) => {
    const previous = ref.current[target] || EMPTY_PERSONAL_DRAFT;
    const next = typeof value === "function" ? (value as (old: Draft[K]) => Draft[K])(previous[key]) : value;
    replace({ ...ref.current, [target]: { ...previous, [key]: next } });
  };
  const move = (source: string, target: string) => {
    const next = { ...ref.current, [target]: ref.current[source] || EMPTY_PERSONAL_DRAFT };
    delete next[source]; replace(next);
  };
  const remove = (target: string) => { const next = { ...ref.current }; delete next[target]; replace(next); };
  const chooseMaterials = (target: string, selectedCase: WorkspaceCase, caseMaterials: Material[]) => {
    replace({ ...ref.current, [target]: { ...(ref.current[target] || EMPTY_PERSONAL_DRAFT), selectedCase, caseMaterials } });
  };
  const refreshSkills = (skills: WorkspaceSkill[]) => replace(Object.fromEntries(Object.entries(ref.current).map(([key, value]) => [key, { ...value, skillId: skills.some((item) => item.id === value.skillId && item.available) ? value.skillId : DEFAULT_AGENT_SKILL }])));
  return { items, ref, update, move, remove, chooseMaterials, refreshSkills };
}

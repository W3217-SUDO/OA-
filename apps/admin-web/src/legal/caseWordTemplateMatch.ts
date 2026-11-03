export type WordTemplateSlot = { index: number | null; kind: "underline" | "placeholder"; sample: string; note: string; source: "case" | "manual"; key: string };
export type WordTemplate = { id: string; name: string; builtin: boolean; is_active: boolean; fields: string[]; options: Record<string, string[]>; slots?: WordTemplateSlot[] };

/** 从一句话里找出要生成的模板，例如“生成撤诉申请书”“帮我出一份撤诉申请书”；不是生成文书的话交给智能体正常回答。 */
export function matchWordTemplate(text: string, templates: WordTemplate[]): WordTemplate | null {
  const content = text.trim();
  if (!/(生成|起草|出一份|做一份|写一份)/.test(content) || content.length > 40) return null;
  return [...templates].sort((a, b) => b.name.length - a.name.length).find(item => item.is_active && content.includes(item.name)) || null;
}

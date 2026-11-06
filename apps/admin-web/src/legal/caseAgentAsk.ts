// 501634（tgn 11-06 15:31 确认）：智能体拿不准时不再用一段文字反问，在回复最后一行写
// 【追问】{"questions":[{"question":"…","options":["…","…"]}]}，界面把它变成输入框上方的选项问题条。
export const ASK_MARKER = "【追问】";
export const MAX_QUESTIONS = 4;
export const MAX_OPTIONS = 4;

export type AgentQuestion = { question: string; options: string[] };

const clean = (value: unknown) => String(value ?? "").trim();

/** 拆出回复正文和追问；格式不对时当作普通文字，不出问题条。 */
export function parseAgentAsk(content: string): { text: string; questions: AgentQuestion[] } {
  const source = content || "";
  const index = source.lastIndexOf(ASK_MARKER);
  if (index < 0) return { text: source, questions: [] };
  const raw = source.slice(index + ASK_MARKER.length).trim();
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start < 0 || end <= start) return { text: source, questions: [] };
  try {
    const parsed = JSON.parse(raw.slice(start, end + 1));
    const list: unknown[] = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.questions) ? parsed.questions : [];
    const questions = list
      .map((item: any) => ({
        question: clean(item?.question),
        options: Array.from(new Set<string>((Array.isArray(item?.options) ? item.options : []).map(clean).filter(Boolean)))
          .filter((option) => !/^其他/.test(option)).slice(0, MAX_OPTIONS),
      }))
      .filter((item) => item.question)
      .slice(0, MAX_QUESTIONS);
    if (!questions.length) return { text: source, questions: [] };
    return { text: source.slice(0, index).trimEnd(), questions };
  } catch {
    return { text: source, questions: [] };
  }
}

/** 全部答完后一起发回智能体的那条消息。 */
export function formatAgentAnswers(questions: AgentQuestion[], answers: string[]): string {
  if (questions.length === 1) return `${questions[0].question}\n${answers[0] || ""}`;
  return questions.map((item, index) => `${index + 1}. ${item.question}\n${answers[index] || ""}`).join("\n");
}

// 501298（陶国南 11-04 07:31）：确认执行或驳回后，待确认卡片自动收起，对话里只留一行结果；失败的仍留在卡片里并写明原因。
export type DecidedLine = { text: string; tone: "done" | "rejected" | "restored" };

/** 已经处理完的操作返回一行结果；还没处理、正在执行或失败的返回 null（留在卡片里）。 */
export function actionResultLine(status: string, summary: string): DecidedLine | null {
  const text = summary || "智能体操作";
  if (status === "succeeded") return { text: `已执行：${text}`, tone: "done" };
  if (status === "approved") return { text: `已执行：${text}`, tone: "done" };
  if (status === "rejected") return { text: `已驳回：${text}`, tone: "rejected" };
  if (status === "restored") return { text: `已恢复：${text}`, tone: "restored" };
  return null;
}

/** 把结果行按处理时间插进对话；没有时间的消息（刚发出的）排在最后。 */
export function mergeByTime<M, A>(messages: M[], actions: A[], messageTime: (item: M) => string | undefined, actionTime: (item: A) => string | undefined) {
  const at = (value?: string) => { const time = value ? Date.parse(value) : NaN; return Number.isNaN(time) ? Number.POSITIVE_INFINITY : time; };
  const rows: ({ kind: "message"; item: M; index: number } | { kind: "action"; item: A })[] = messages.map((item, index) => ({ kind: "message" as const, item, index }));
  for (const action of [...actions].sort((left, right) => at(actionTime(left)) - at(actionTime(right)))) {
    const time = at(actionTime(action));
    const position = rows.findIndex((row) => row.kind === "message" && at(messageTime(row.item)) > time);
    rows.splice(position < 0 ? rows.length : position, 0, { kind: "action", item: action });
  }
  return rows;
}

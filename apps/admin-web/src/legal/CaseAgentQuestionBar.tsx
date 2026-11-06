import { useEffect, useState } from "react";
import { Button, Input, Tooltip } from "antd";
import { ArrowRightOutlined, CloseOutlined, EditOutlined, LeftOutlined, RightOutlined } from "@ant-design/icons";
import type { AgentQuestion } from "./caseAgentAsk";

// 501634（tgn 11-06 15:31 确认）：输入框上方的问题条，参照 tgn 截图：一题一页（1/4），编号选项点一下就选，
// 最后一行“其他补充…”可自己打字（回车或右箭头提交）。多题全部答完再一起交给 onSubmit。
// 写入确认也用它（选项为批准/驳回）。关掉只是稍后处理，不算回答。样式不用 :has、dvh、color-mix、@container（钉钉 Chrome 100）。
export function CaseAgentQuestionBar({ questions, disabled, busy, onSubmit, onClose, testId = "case-agent-question-bar", note }: {
  questions: AgentQuestion[];
  disabled?: boolean;
  busy?: boolean;
  onSubmit: (answers: string[], typed: boolean[]) => void;
  onClose: () => void;
  testId?: string;
  note?: string;
}) {
  const [page, setPage] = useState(0);
  const [answers, setAnswers] = useState<string[]>([]);
  const [typed, setTyped] = useState<boolean[]>([]);
  const [draft, setDraft] = useState("");
  const key = questions.map((item) => item.question + item.options.join("|")).join("||");
  useEffect(() => { setPage(0); setAnswers([]); setTyped([]); setDraft(""); }, [key]);
  if (!questions.length) return null;
  const current = questions[Math.min(page, questions.length - 1)];
  const answer = (value: string, isTyped: boolean) => {
    const text = value.trim();
    if (!text || disabled || busy) return;
    const nextAnswers = [...answers]; nextAnswers[page] = text;
    const nextTyped = [...typed]; nextTyped[page] = isTyped;
    setAnswers(nextAnswers); setTyped(nextTyped); setDraft("");
    const missing = questions.findIndex((_, index) => !nextAnswers[index]);
    if (missing < 0) onSubmit(nextAnswers, nextTyped);
    else setPage(missing > page ? missing : Math.min(page + 1, questions.length - 1));
  };
  return <div className="case-agent-question-bar" role="dialog" aria-label={current.question} data-testid={testId}>
    <div className="case-agent-question-head">
      <strong className="case-agent-question-title">{current.question}</strong>
      <span className="case-agent-question-tools">
        {questions.length > 1 && <>
          <Button type="text" size="small" icon={<LeftOutlined />} aria-label="上一题" disabled={page === 0} onClick={() => setPage(page - 1)} />
          <span className="case-agent-question-pager">{page + 1}/{questions.length}</span>
          <Button type="text" size="small" icon={<RightOutlined />} aria-label="下一题" disabled={page >= questions.length - 1} onClick={() => setPage(page + 1)} />
        </>}
        <Tooltip title="稍后再答（不算回答）"><Button type="text" size="small" icon={<CloseOutlined />} aria-label="关闭问题条" onClick={onClose} /></Tooltip>
      </span>
    </div>
    {note ? <div className="case-agent-question-note">{note}</div> : null}
    <div className="case-agent-question-options" role="listbox" aria-label="选项">
      {current.options.map((option, index) => {
        const chosen = answers[page] === option && !typed[page];
        return <button key={option} type="button" role="option" aria-selected={chosen} disabled={disabled || busy}
          className={chosen ? "case-agent-question-option is-chosen" : "case-agent-question-option"} onClick={() => answer(option, false)}>
          <span className="case-agent-question-index">{index + 1}</span>
          <span className="case-agent-question-text">{option}</span>
          <ArrowRightOutlined className="case-agent-question-go" />
        </button>;
      })}
      <div className="case-agent-question-other">
        <span className="case-agent-question-index"><EditOutlined /></span>
        <Input variant="borderless" value={draft} disabled={disabled || busy} placeholder="其他补充…" aria-label="其他补充"
          onChange={(event) => setDraft(event.target.value)} onPressEnter={() => answer(draft, true)} />
        {draft.trim() ? <Button type="text" size="small" icon={<ArrowRightOutlined />} aria-label="提交补充" onClick={() => answer(draft, true)} /> : null}
      </div>
    </div>
  </div>;
}

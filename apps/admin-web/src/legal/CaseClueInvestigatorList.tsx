import type { CaseClueInvestigator } from "../caseSecondBatchParity";

/** 修改案件基本信息：调查员按关联线索逐条显示（501293，只读）。 */
export function CaseClueInvestigatorList({ value = [] }: { value?: CaseClueInvestigator[] }) {
  if (!value.length) return <span style={{ color: "#999" }}>未关联调查线索</span>;
  return <div data-testid="case-clue-investigators">
    {value.map((item, index) => <div key={`${item.clue_no}-${index}`}>{item.clue_no ? `${item.clue_no}：` : ""}{item.name}</div>)}
  </div>;
}

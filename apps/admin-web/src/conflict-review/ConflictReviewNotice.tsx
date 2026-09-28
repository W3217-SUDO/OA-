import { Alert, Button, Collapse, Space } from "antd";
import { openConflictReview } from "./events";
import { ConflictReviewCheckButton } from "./ConflictReviewCheckButton";
import { conflictKindLabel, conflictStatusLabel } from "./types";
import type { ConflictReviewGuard } from "./useConflictReview";

export function ConflictReviewNotice({ guard }: { guard: ConflictReviewGuard }) {
  const checkButton = guard.state?.can_check ? <ConflictReviewCheckButton recordId={guard.state.record_id} refreshRecordId={guard.recordId} /> : null;
  if (guard.error) return <Alert type="error" showIcon title={guard.error} action={<Button size="small" onClick={guard.reload}>重试</Button>} />;
  if (guard.loading) return <Alert type="info" showIcon title="正在读取利益冲突审查状态" />;
  const review = guard.state?.review;
  if (!review) return guard.state?.blocking ? <Alert type="warning" showIcon title={guard.state.message || "请先保存资料并完成利益冲突审查"} action={checkButton} /> : null;
  const blocked = Boolean(guard.state?.blocking);
  const expired = review.status === "expired" || (blocked && !review.blocking);
  const unresolved = review.findings.some((item) => item.status === "pending" && item.unresolved);
  const names = review.findings.filter((item) => item.status === "pending" || item.status === "rejected").map((item) => `${item.rule_id} ${item.title}`).join("；");
  return <Alert
    className="conflict-review-notice"
    type={blocked ? review.kind === "absolute" ? "error" : "warning" : "success"}
    showIcon
    title={expired ? "业务资料已变化，请重新核实利益冲突" : blocked ? `${unresolved ? "本业务有待核实的" : "本业务存在"}${conflictKindLabel(review.kind)}利益冲突情况，请核实${review.kind === "relative" ? "或取得书面豁免" : ""}` : `利益冲突审查：${conflictStatusLabel(review.status)}`}
    description={<Space orientation="vertical" style={{ width: "100%" }}>
      <span>{names || "查看审查记录与处理意见。"}</span>
      {guard.state?.message && <span>{guard.state.message}</span>}
      {guard.blocked && <span>核查通过前，普通审批通过、用印和立案暂不可继续。</span>}
      <Collapse size="small" style={{ width: "100%" }} items={[{ key: "guidance", label: "审核建议", children: review.findings.map((finding) => <div key={finding.rule_id}>
        <strong>{finding.rule_id} {finding.title}</strong><p>{finding.reason}</p>
        <p>所需事实：{finding.required_facts.join("、")}</p><p>人工核查边界：{finding.manual_boundary}</p>
        {finding.branches?.map((branch) => <p key={branch.action}>{branch.condition}：{branch.description}</p>)}
      </div>) }]} />
      <Space wrap>{guard.state?.can_view && <Button size="small" onClick={() => openConflictReview(review.id, review.source_record_id)}>查看审查记录</Button>}{checkButton}</Space>
    </Space>}
  />;
}

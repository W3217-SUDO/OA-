import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Collapse, Descriptions, Empty, Space, Spin, Tag, message } from "antd";
import { api } from "../api";
import { ConflictReviewActions } from "./ConflictReviewActions";
import { ConflictReviewCheckButton } from "./ConflictReviewCheckButton";
import { notifyConflictReviewUpdated } from "./events";
import { conflictKindLabel, conflictStatusLabel } from "./types";
import type { ConflictAttachment, ConflictReview } from "./types";
import "./conflict-review.css";

export function ConflictReviewPanel({ reviewId }: { reviewId: number }) {
  const [review, setReview] = useState<ConflictReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const activeRequest = useRef<AbortController | null>(null);
  const load = useCallback(async () => {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<ConflictReview>(`/conflict-reviews/${reviewId}`, { signal: controller.signal });
      if (!controller.signal.aborted) setReview(data);
    } catch (cause: any) { if (!controller.signal.aborted) setError(cause?.response?.data?.detail || "审查记录加载失败"); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [reviewId]);
  useEffect(() => { setReview(null); void load(); return () => activeRequest.current?.abort(); }, [load]);
  const saved = async () => {
    await load();
    if (review) notifyConflictReviewUpdated(review.source_record_id);
  };
  const download = async (attachment: ConflictAttachment) => {
    try {
      const { data } = await api.get(`/conflict-reviews/${reviewId}/attachments/${attachment.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = url;
      link.download = attachment.original_name;
      link.click();
      URL.revokeObjectURL(url);
    } catch (cause: any) { message.error(typeof cause?.response?.data?.detail === "string" ? cause.response.data.detail : "豁免附件下载失败"); }
  };
  if (!review) return error ? <Alert type="error" showIcon title={error} action={<Button onClick={() => void load()}>重试</Button>} /> : <Spin />;
  return <Spin spinning={loading}><div className="conflict-review-panel">
    {error && <Alert type="error" showIcon title={error} action={<Button onClick={() => void load()}>重试</Button>} />}
    <Alert type={review.blocking ? review.kind === "absolute" ? "error" : "warning" : "success"} showIcon title={`利益冲突审查：${conflictStatusLabel(review.status)}`} description={review.blocking ? "本业务仍受阻断，普通审批通过、用印和立案不能继续。请逐条核实下列情况。" : "审查结果已保存；请返回原业务页面继续办理，系统仍会校验最新事实。"} />
    <Descriptions bordered size="small" column={2} items={[
      { key: "no", label: "业务编号", children: review.source_no }, { key: "module", label: "业务类型", children: review.source_module },
      { key: "title", label: "业务名称", children: review.source_title, span: 2 },
      { key: "submitter", label: "提交人", children: review.submitter }, { key: "updated", label: "更新时间", children: review.updated_at },
    ]} />
    {review.missing_facts.length > 0 && <Alert type="warning" showIcon title="事实资料不足，仍须核实" description={<ul className="conflict-review-evidence">{review.missing_facts.map((fact, index) => <li key={index}>{fact}</li>)}</ul>} />}
    {review.findings.length ? review.findings.map((finding) => <section key={finding.rule_id} className={`conflict-review-finding ${finding.kind}`}>
      <h4><Tag color={finding.kind === "absolute" ? "red" : "gold"}>{conflictKindLabel(finding.kind)}</Tag>{finding.rule_id} {finding.title}</h4>
      <Tag>{conflictStatusLabel(finding.status)}</Tag>
      <p>{finding.reason}</p>
      {finding.unresolved && <p>待核实：资料不足不能视为无冲突，请补充理由或材料后交由审核人员确认。</p>}
      {finding.evidence.length > 0 && <ul className="conflict-review-evidence">{finding.evidence.map((fact, index) => <li key={index}>{fact}</li>)}</ul>}
      <Collapse size="small" items={[{ key: "guidance", label: "审核建议与所需事实", children: <>
        <p><strong>所需事实：</strong>{finding.required_facts.join("、")}</p>
        <p><strong>人工核查边界：</strong>{finding.manual_boundary}</p>
        {finding.branches?.map((branch) => <p key={branch.action}><strong>{branch.condition}：</strong>{branch.description}</p>)}
      </> }]} />
      {finding.feedback && <p><strong>提交人反馈：</strong>{finding.feedback.reason}（{finding.feedback.by}，{finding.feedback.at}）</p>}
      {finding.decision && <p><strong>审核意见：</strong>{finding.decision.reason}（{finding.decision.by}，{finding.decision.at}）</p>}
    </section>) : <Empty description="此审查没有已登记的规则命中" />}
    {review.attachments.length > 0 && <div><strong>书面豁免材料</strong><Space wrap>{review.attachments.map((item) => <Button type="link" key={item.id} onClick={() => void download(item)}>{item.original_name}</Button>)}</Space></div>}
    <ConflictReviewActions review={review} onSaved={saved} />
    <Space><Button onClick={() => void load()}>刷新审查记录</Button>{review.can_check && <ConflictReviewCheckButton recordId={review.source_record_id} onChecked={load} />}</Space>
  </div></Spin>;
}

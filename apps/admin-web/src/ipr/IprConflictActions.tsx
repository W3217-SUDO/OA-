import { useState } from "react";
import { Button, Popover, Space, Tag, message } from "antd";
import { api } from "../api";
import { ConflictReviewNotice } from "../conflict-review/ConflictReviewNotice";
import { useConflictReview } from "../conflict-review/useConflictReview";
import type { ConflictRecordState, ConflictReview } from "../conflict-review/types";

export function IprConflictActions({ recordId, mode, onSubmit, onReview, detail = false, summary }: {
  recordId: number;
  mode: "submit" | "review";
  onSubmit?: () => void;
  onReview?: (approved: boolean) => void;
  detail?: boolean;
  summary?: Pick<ConflictReview, "id" | "blocking" | "kind">;
}) {
  const [inspecting, setInspecting] = useState(false);
  const [validating, setValidating] = useState(false);
  const conflict = useConflictReview(recordId, detail || inspecting);
  const blocked = detail || inspecting ? conflict.blocked : Boolean(summary?.blocking);
  const kind = conflict.state?.review?.kind || summary?.kind;
  const proceed = async () => {
    setValidating(true);
    try {
      const { data } = await api.get<ConflictRecordState>(`/conflict-reviews/record/${recordId}`);
      if (data.blocking) { setInspecting(true); return; }
      if (mode === "submit") onSubmit?.();
      else onReview?.(true);
    } catch (error: any) { message.error(error?.response?.data?.detail || "利益冲突状态读取失败"); }
    finally { setValidating(false); }
  };
  return <Space size={0} wrap>
    {blocked && kind && <Tag color={kind === "absolute" ? "red" : "gold"}>{kind === "absolute" ? "绝对冲突待核查" : kind === "relative" ? "相对冲突待核查" : "专项待核实"}</Tag>}
    {mode === "submit" ? <Button type={detail ? "primary" : "link"} disabled={blocked} loading={validating} onClick={() => void proceed()}>{detail ? "提交立案审核" : "提交审核"}</Button> : <>
      <Button type="link" disabled={blocked} loading={validating} onClick={() => void proceed()}>通过</Button>
      <Button type="link" danger onClick={() => onReview?.(false)}>驳回</Button>
    </>}
    <Popover open={inspecting} onOpenChange={setInspecting} trigger="click" title="利益冲突审查" content={<div style={{ width: 440, maxWidth: "75vw" }}><ConflictReviewNotice guard={conflict} /></div>}>
      <Button type="link" danger={kind === "absolute" && blocked}>利冲审查</Button>
    </Popover>
  </Space>;
}

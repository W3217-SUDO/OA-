import { useEffect, useState } from "react";
import { Alert, Button, Form, Input, Select, Space, message } from "antd";
import { api } from "../api";
import { AttachmentFileInput } from "../components/common/AttachmentContent";
import type { ConflictAttachment, ConflictReview } from "./types";

type FeedbackAction = "false_positive" | "waiver" | "stop";
type DecisionAction = "false_positive" | "waiver" | "reject";

export function ConflictReviewActions({ review, onSaved }: { review: ConflictReview; onSaved: () => Promise<void> }) {
  const [feedbackForm] = Form.useForm();
  const [decisionForm] = Form.useForm();
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const feedbackRuleId = Form.useWatch("rule_id", feedbackForm);
  const feedbackAction = Form.useWatch("action", feedbackForm) as FeedbackAction | undefined;
  const decisionRuleId = Form.useWatch("rule_id", decisionForm);
  const pending = review.findings.filter((item) => item.status === "pending");
  const options = pending.map((item) => ({ value: item.rule_id, label: `${item.rule_id} ${item.title}` }));
  const feedbackFinding = pending.find((item) => item.rule_id === feedbackRuleId);
  const decisionFinding = pending.find((item) => item.rule_id === decisionRuleId);
  const pendingAbsolute = pending.some((item) => item.kind === "absolute");
  const waiverAllowed = decisionFinding?.kind === "relative" && !pendingAbsolute
    && decisionFinding.feedback?.action === "waiver"
    && decisionFinding.feedback.attachment_ids.some((id) => review.attachments.some((attachment) => attachment.id === id && attachment.current === true));

  useEffect(() => {
    feedbackForm.resetFields();
    decisionForm.resetFields();
    feedbackForm.setFieldsValue({ rule_id: options[0]?.value, action: "false_positive" });
    decisionForm.setFieldsValue({ rule_id: options[0]?.value });
    setFile(null);
    setFileInputKey((value) => value + 1);
  }, [review.id, review.fingerprint]);
  useEffect(() => {
    if (!pending.some((item) => item.rule_id === feedbackForm.getFieldValue("rule_id"))) feedbackForm.setFieldValue("rule_id", options[0]?.value);
    if (!pending.some((item) => item.rule_id === decisionForm.getFieldValue("rule_id"))) decisionForm.setFieldValue("rule_id", options[0]?.value);
  }, [review.updated_at, feedbackForm, decisionForm]);

  const upload = async () => {
    if (!file) return message.warning("请选择书面豁免文件");
    setBusy(true);
    try {
      const payload = new FormData();
      payload.append("file", file);
      const { data } = await api.post<ConflictAttachment>(`/conflict-reviews/${review.id}/attachments`, payload);
      feedbackForm.setFieldValue("attachment_ids", [...new Set([...(feedbackForm.getFieldValue("attachment_ids") || []), data.id])]);
      setFile(null);
      setFileInputKey((value) => value + 1);
      await onSaved();
      message.success("书面豁免文件已上传，请填写说明后提交反馈");
    } catch (error: any) { message.error(error?.response?.data?.detail || "豁免文件上传失败"); }
    finally { setBusy(false); }
  };
  const sendFeedback = async () => {
    try {
      const values = await feedbackForm.validateFields();
      const action = values.action as FeedbackAction;
      const attachmentIds: number[] = values.attachment_ids || [];
      if (action === "waiver" && !attachmentIds.length) return message.warning("请上传并选择有效的书面豁免文件");
      if (action !== "stop" && !pending.some((item) => item.rule_id === values.rule_id)) return message.warning("请选择当前待核查规则");
      setBusy(true);
      await api.post(`/conflict-reviews/${review.id}/feedback`, { rule_id: action === "stop" ? undefined : values.rule_id, action, reason: values.reason.trim(), attachment_ids: action === "waiver" ? attachmentIds : [], revision: review.revision });
      await onSaved();
      feedbackForm.setFieldValue("reason", "");
      message.success(action === "stop" ? "已登记停止代理" : "反馈已提交，等待利益冲突审核人员核查");
    } catch (error: any) { if (!error?.errorFields) message.error(error?.response?.data?.detail || "反馈提交失败"); }
    finally { setBusy(false); }
  };
  const decide = async (decision: DecisionAction) => {
    try {
      const values = await decisionForm.validateFields();
      setBusy(true);
      await api.post(`/conflict-reviews/${review.id}/decision`, { rule_id: values.rule_id, decision, reason: values.reason.trim(), fingerprint: review.fingerprint, revision: review.revision });
      await onSaved();
      decisionForm.setFieldValue("reason", "");
      message.success("利益冲突核查意见已保存");
    } catch (error: any) { if (!error?.errorFields) message.error(error?.response?.data?.detail || "核查处理失败"); }
    finally { setBusy(false); }
  };

  if (!review.can_feedback && !review.can_review) return null;
  return <div className="conflict-review-actions">
    {review.can_feedback && <>
      <h4>提交人反馈</h4>
      <Form form={feedbackForm} layout="vertical" disabled={busy}>
        <Form.Item name="rule_id" label="反馈对应的规则" rules={feedbackAction === "stop" ? [] : [{ required: true, message: "请选择规则" }]}><Select options={options} onChange={() => { if (feedbackAction === "waiver") feedbackForm.setFieldValue("action", "false_positive"); }} /></Form.Item>
        <Form.Item name="action" label="处理方式" rules={[{ required: true }]}><Select options={[
          { value: "false_positive", label: "认为是误判，提交理由" },
          { value: "waiver", label: "相对利益冲突，已取得书面豁免", disabled: feedbackFinding?.kind !== "relative" },
          { value: "stop", label: "停止代理（含客户不同意豁免）" },
        ]} /></Form.Item>
        <Form.Item name="reason" label="理由或说明" rules={[{ required: true, whitespace: true, message: "请填写具体理由或说明" }]}><Input.TextArea rows={3} maxLength={4000} showCount /></Form.Item>
        {feedbackAction === "waiver" && <>
          <Form.Item label="上传书面豁免函"><Space wrap><AttachmentFileInput key={fileInputKey} onFileChange={setFile} disabled={busy} /><Button disabled={!file} loading={busy} onClick={() => void upload()}>上传</Button></Space></Form.Item>
          <Form.Item name="attachment_ids" label="本次反馈引用的豁免文件"><Select mode="multiple" placeholder="选择已上传文件" options={review.attachments.filter((item) => item.current === true).map((item) => ({ value: item.id, label: item.original_name }))} /></Form.Item>
          <Alert type="warning" showIcon title="上传文件不等于审核通过。须由具有利益冲突审批权限的人员核查书面豁免后放行。" />
        </>}
        <Button type="primary" loading={busy} onClick={() => void sendFeedback()}>提交反馈</Button>
      </Form>
    </>}
    {review.can_review && pending.length > 0 && <>
      <h4>利益冲突核查</h4>
      <Form form={decisionForm} layout="vertical" disabled={busy}>
        <Form.Item name="rule_id" label="待核查规则" rules={[{ required: true, message: "请选择规则" }]}><Select options={options} /></Form.Item>
        <Form.Item name="reason" label="核查理由" rules={[{ required: true, whitespace: true, message: "请填写具体核查理由" }]}><Input.TextArea rows={3} maxLength={4000} showCount /></Form.Item>
        <Space wrap>
          <Button type="primary" loading={busy} onClick={() => void decide("false_positive")}>判断为误判，审核通过</Button>
          <Button disabled={!waiverAllowed || busy} onClick={() => void decide("waiver")}>相对禁止，已获豁免，审核通过</Button>
          <Button danger loading={busy} onClick={() => void decide("reject")}>存在利益冲突，不通过</Button>
        </Space>
        {pendingAbsolute && <p>绝对利益冲突不能通过豁免放行；存在未决绝对冲突时，先完成绝对冲突核查。</p>}
      </Form>
    </>}
  </div>;
}

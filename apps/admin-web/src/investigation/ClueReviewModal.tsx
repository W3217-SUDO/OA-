import { useEffect, useRef, useState } from "react";
import { Modal, Form, Input, Radio, Alert, Button, Spin, Space } from "antd";
import { CheckCircleOutlined } from "@ant-design/icons";
import type { Row } from "./types";
import { api } from "../api";

interface ClueReviewModalProps {
  open: boolean;
  clueReviewing: Row | null;
  clueReviewForm: any;
  projectedPersonDisplayName: (displayName: unknown, username: unknown) => string;
  onOk: () => void | Promise<void>;
  onCancel: () => void;
  onOpenClue: (serialNo: string) => void;
  onOpenCase: (serialNo: string) => void;
  embedded?: boolean;
}

export default function ClueReviewModal({
  open,
  clueReviewing,
  clueReviewForm,
  projectedPersonDisplayName,
  onOk,
  onCancel,
  onOpenClue,
  onOpenCase,
  embedded = false,
}: ClueReviewModalProps) {
  const [conflicts, setConflicts] = useState<{ clues: string[]; cases: string[]; case_search_available: boolean } | null>(null);
  const [conflictError, setConflictError] = useState("");
  // 审批要等冲突复核，约需一两秒；提交中锁住按钮，防止连点重复审批（280200）。
  const [submitting, setSubmitting] = useState<boolean | null>(null);
  const submittingRef = useRef(false);
  const submit = async (approved?: boolean) => {
    if (submittingRef.current) return;
    submittingRef.current = true;
    setSubmitting(approved ?? true);
    try {
      if (approved !== undefined) clueReviewForm.setFieldValue("approved", approved);
      await onOk();
    } catch {
      // 表单校验未通过时由表单自己提示。
    } finally {
      submittingRef.current = false;
      setSubmitting(null);
    }
  };
  useEffect(() => {
    if (!open || !clueReviewing || clueReviewing.status !== "待审批") {
      setConflicts(null);
      setConflictError("");
      return;
    }
    let active = true;
    setConflicts(null);
    setConflictError("");
    api.get(`/investigations/clues/${clueReviewing.id}/conflicts`)
      .then(({ data }) => { if (active) setConflicts(data); })
      .catch((error) => { if (active) setConflictError(error?.response?.data?.detail || "疑似冲突加载失败"); });
    return () => { active = false; };
  }, [open, clueReviewing?.id, clueReviewing?.status]);

  const conflictLinks = (values: string[], onOpen: (serialNo: string) => void) =>
    values.length ? <Space size={4} wrap>{values.map((serialNo) => <Button key={serialNo} type="link" onClick={() => onOpen(serialNo)}>{serialNo}</Button>)}</Space> : "无";
  const content = (
    <>
      {clueReviewing?.status === "待审批" && (
        <div className="clue-review-conflicts">
          {conflictError ? <Alert type="error" showIcon title={conflictError} /> : !conflicts ? <Spin size="small" /> : <>
            <div>疑似冲突线索：{conflictLinks(conflicts.clues, onOpenClue)}</div>
            <div>疑似冲突案件：{conflicts.case_search_available ? conflictLinks(conflicts.cases, onOpenCase) : "未录入被调查对象或生产者，无法比对"}</div>
          </>}
        </div>
      )}
      <Form form={clueReviewForm} layout="vertical">
        {clueReviewing?.status === "待客户审核" && (
          <div className="form-grid audit-reference">
            <Form.Item label="上一级审核员">
              <Input
                value={projectedPersonDisplayName(
                  clueReviewing.data.reviewer_display_name,
                  clueReviewing.data.reviewer,
                )}
                readOnly
              />
            </Form.Item>
            <Form.Item label="上一级审核意见">
              <Input.TextArea
                value={clueReviewing.data.review_comment || "—"}
                readOnly
                rows={2}
              />
            </Form.Item>
          </div>
        )}
        <Form.Item
          label="审核结果"
          name="approved"
          rules={[{ required: true }]}
          hidden={embedded}
        >
          <Radio.Group>
            <Radio value={true}>
              <CheckCircleOutlined />{" "}
              {clueReviewing?.status === "待客户审核"
                ? "客户确认通过，进入待取证"
                : "内部审批通过，进入客户审核或取证"}
            </Radio>
            <Radio value={false}>驳回修改</Radio>
          </Radio.Group>
        </Form.Item>
        <Form.Item
          label={
            clueReviewing?.status === "待客户审核"
              ? "客户反馈/驳回原因"
              : "审核意见/驳回原因"
          }
          name="comment"
          rules={[{ required: true, min: 2 }]}
        >
          <Input.TextArea rows={4} />
        </Form.Item>
      </Form>
    </>
  );
  if (embedded) {
    return <section className="clue-audit-review">
      <h3>{clueReviewing?.status === "待客户审核" ? "客户审核确认" : "线索审批"}</h3>
      {content}
      <Space className="clue-audit-review-actions">
        <Button type="primary" loading={submitting === true} disabled={submitting === false || (clueReviewing?.status === "待审批" && (!conflicts || Boolean(conflictError)))}
          onClick={() => submit(true)}>{submitting === true ? "提交中" : "同意"}</Button>
        <Button danger loading={submitting === false} disabled={submitting === true || (clueReviewing?.status === "待审批" && (!conflicts || Boolean(conflictError)))}
          onClick={() => submit(false)}>{submitting === false ? "提交中" : "拒绝"}</Button>
      </Space>
    </section>;
  }
  return <Modal
    open={open}
    title={`${clueReviewing?.status === "待客户审核" ? "客户审核确认" : "线索内部审批"}：${clueReviewing?.serial_no || ""}`}
    okText="提交审核"
    cancelText="取消"
    okButtonProps={{ disabled: clueReviewing?.status === "待审批" && (!conflicts || Boolean(conflictError)) }}
    confirmLoading={submitting !== null}
    onOk={() => submit()}
    onCancel={onCancel}
  >{content}</Modal>;
}

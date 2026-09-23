import { useEffect, useState } from "react";
import { Modal, Form, Input, Radio, Alert, Button, Spin, Space } from "antd";
import { CheckCircleOutlined } from "@ant-design/icons";
import type { Row } from "./types";
import { api } from "../api";

interface ClueReviewModalProps {
  open: boolean;
  clueReviewing: Row | null;
  clueReviewForm: any;
  projectedPersonDisplayName: (displayName: unknown, username: unknown) => string;
  onOk: () => void;
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
  const [conflicts, setConflicts] = useState<{ clues: string[]; cases: string[] } | null>(null);
  const [conflictError, setConflictError] = useState("");
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
            <div>疑似冲突案件：{conflictLinks(conflicts.cases, onOpenCase)}</div>
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
        <Button type="primary" disabled={clueReviewing?.status === "待审批" && (!conflicts || Boolean(conflictError))}
          onClick={() => { clueReviewForm.setFieldValue("approved", true); onOk(); }}>同意</Button>
        <Button danger disabled={clueReviewing?.status === "待审批" && (!conflicts || Boolean(conflictError))}
          onClick={() => { clueReviewForm.setFieldValue("approved", false); onOk(); }}>拒绝</Button>
      </Space>
    </section>;
  }
  return <Modal
    open={open}
    title={`${clueReviewing?.status === "待客户审核" ? "客户审核确认" : "线索内部审批"}：${clueReviewing?.serial_no || ""}`}
    okText="提交审核"
    cancelText="取消"
    okButtonProps={{ disabled: clueReviewing?.status === "待审批" && (!conflicts || Boolean(conflictError)) }}
    onOk={onOk}
    onCancel={onCancel}
  >{content}</Modal>;
}

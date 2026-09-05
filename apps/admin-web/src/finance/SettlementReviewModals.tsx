import { Input,Modal } from "antd";

interface SettlementReviewModalsProps {
  // 普通结算申请
  generalApplyTargets: any[];
  generalApplyComment: string;
  generalApplyBusy: boolean;
  onGeneralApplyCommentChange: (value: string) => void;
  onGeneralApplySubmit: () => void;
  onGeneralApplyCancel: () => void;

  // 普通结算审核
  generalReviewTargets: any[];
  generalReviewApproved: boolean;
  generalReviewComment: string;
  generalReviewBusy: boolean;
  onGeneralReviewCommentChange: (value: string) => void;
  onGeneralReviewSubmit: () => void;
  onGeneralReviewCancel: () => void;

  // 普通结算付款
  generalPaymentTargets: any[];
  generalPaymentAction: string;
  generalPaymentComment: string;
  generalPaymentBusy: boolean;
  onGeneralPaymentCommentChange: (value: string) => void;
  onGeneralPaymentSubmit: () => void;
  onGeneralPaymentCancel: () => void;

  // 普通结算重新申请
  generalReapplyTargets: any[];
  generalReapplyComment: string;
  generalReapplyBusy: boolean;
  onGeneralReapplyCommentChange: (value: string) => void;
  onGeneralReapplySubmit: () => void;
  onGeneralReapplyCancel: () => void;

  // 归档费结算审核
  archiveReviewTargets: any[];
  archiveReviewApproved: boolean;
  archiveReviewComment: string;
  archiveReviewBusy: boolean;
  onArchiveReviewCommentChange: (value: string) => void;
  onArchiveReviewSubmit: () => void;
  onArchiveReviewCancel: () => void;

  // 归档费结算回滚
  archiveRollbackTargets: any[];
  archiveRollbackComment: string;
  archiveRollbackBusy: boolean;
  isArchiveRejectedRoute: boolean;
  onArchiveRollbackCommentChange: (value: string) => void;
  onArchiveRollbackSubmit: () => void;
  onArchiveRollbackCancel: () => void;

  // 归档费重新申请
  archiveReapplyTargets: any[];
  archiveReapplyComment: string;
  archiveReapplyBusy: boolean;
  onArchiveReapplyCommentChange: (value: string) => void;
  onArchiveReapplySubmit: () => void;
  onArchiveReapplyCancel: () => void;
}

export function SettlementReviewModals({
  generalApplyTargets,
  generalApplyComment,
  generalApplyBusy,
  onGeneralApplyCommentChange,
  onGeneralApplySubmit,
  onGeneralApplyCancel,

  generalReviewTargets,
  generalReviewApproved,
  generalReviewComment,
  generalReviewBusy,
  onGeneralReviewCommentChange,
  onGeneralReviewSubmit,
  onGeneralReviewCancel,

  generalPaymentTargets,
  generalPaymentAction,
  generalPaymentComment,
  generalPaymentBusy,
  onGeneralPaymentCommentChange,
  onGeneralPaymentSubmit,
  onGeneralPaymentCancel,

  generalReapplyTargets,
  generalReapplyComment,
  generalReapplyBusy,
  onGeneralReapplyCommentChange,
  onGeneralReapplySubmit,
  onGeneralReapplyCancel,

  archiveReviewTargets,
  archiveReviewApproved,
  archiveReviewComment,
  archiveReviewBusy,
  onArchiveReviewCommentChange,
  onArchiveReviewSubmit,
  onArchiveReviewCancel,

  archiveRollbackTargets,
  archiveRollbackComment,
  archiveRollbackBusy,
  isArchiveRejectedRoute,
  onArchiveRollbackCommentChange,
  onArchiveRollbackSubmit,
  onArchiveRollbackCancel,

  archiveReapplyTargets,
  archiveReapplyComment,
  archiveReapplyBusy,
  onArchiveReapplyCommentChange,
  onArchiveReapplySubmit,
  onArchiveReapplyCancel,
}: SettlementReviewModalsProps) {
  return (
    <>
      <Modal
        className="finance-settlement-review-modal"
        open={generalApplyTargets.length > 0}
        title="申请结算"
        okText="申请结算"
        cancelText="取消"
        confirmLoading={generalApplyBusy}
        onOk={onGeneralApplySubmit}
        onCancel={onGeneralApplyCancel}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>备注:</span>
          <Input
            value={generalApplyComment}
            maxLength={2000}
            onChange={(event) => onGeneralApplyCommentChange(event.target.value)}
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={generalReviewTargets.length > 0}
        title={generalReviewApproved ? "同意结算" : "拒绝结算"}
        okText={generalReviewApproved ? "同意" : "提交"}
        cancelText="取消"
        confirmLoading={generalReviewBusy}
        onOk={onGeneralReviewSubmit}
        onCancel={onGeneralReviewCancel}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>备注:</span>
          <Input
            value={generalReviewComment}
            maxLength={2000}
            onChange={(event) => onGeneralReviewCommentChange(event.target.value)}
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={generalPaymentTargets.length > 0}
        title={
          generalPaymentAction === "paid"
            ? "标记已支付"
            : "回退结算"
        }
        okText="提交"
        cancelText="取消"
        confirmLoading={generalPaymentBusy}
        onOk={onGeneralPaymentSubmit}
        onCancel={onGeneralPaymentCancel}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>
            {generalPaymentAction === "rollback"
              ? "审核备注:"
              : "备注:"}
          </span>
          <Input
            value={generalPaymentComment}
            maxLength={2000}
            onChange={(event) => onGeneralPaymentCommentChange(event.target.value)}
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={archiveReviewTargets.length > 0}
        title={archiveReviewApproved ? "同意结算" : "拒绝结算"}
        okText={archiveReviewApproved ? "同意" : "提交"}
        cancelText="取消"
        confirmLoading={archiveReviewBusy}
        onOk={onArchiveReviewSubmit}
        onCancel={onArchiveReviewCancel}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>备注:</span>
          <Input
            value={archiveReviewComment}
            maxLength={2000}
            onChange={(event) => onArchiveReviewCommentChange(event.target.value)}
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={archiveRollbackTargets.length > 0}
        title={isArchiveRejectedRoute ? "回滚归档费" : "回滚归档费结算"}
        okText="回滚"
        cancelText="取消"
        confirmLoading={archiveRollbackBusy}
        onOk={onArchiveRollbackSubmit}
        onCancel={onArchiveRollbackCancel}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>{isArchiveRejectedRoute ? "审核备注:" : "备注:"}</span>
          <Input
            value={archiveRollbackComment}
            maxLength={2000}
            onChange={(event) => onArchiveRollbackCommentChange(event.target.value)}
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={archiveReapplyTargets.length > 0}
        title="重新申请"
        okText="提交"
        cancelText="取消"
        confirmLoading={archiveReapplyBusy}
        onOk={onArchiveReapplySubmit}
        onCancel={onArchiveReapplyCancel}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>备注:</span>
          <Input
            value={archiveReapplyComment}
            maxLength={2000}
            onChange={(event) => onArchiveReapplyCommentChange(event.target.value)}
          />
        </label>
      </Modal>
      <Modal
        className="finance-settlement-review-modal"
        open={generalReapplyTargets.length > 0}
        title="重新申请结算"
        okText="提交"
        cancelText="取消"
        confirmLoading={generalReapplyBusy}
        onOk={onGeneralReapplySubmit}
        onCancel={onGeneralReapplyCancel}
        destroyOnHidden
      >
        <label className="finance-settlement-review-field">
          <span>备注:</span>
          <Input
            value={generalReapplyComment}
            maxLength={2000}
            onChange={(event) => onGeneralReapplyCommentChange(event.target.value)}
          />
        </label>
      </Modal>
    </>
  );
}

export default SettlementReviewModals;

export const CONFLICT_REVIEW_OPEN_EVENT = "sunhold:conflict-review-open";
export const CONFLICT_REVIEW_UPDATED_EVENT = "sunhold:conflict-review-updated";
export type ConflictReviewOpenDetail = { reviewId: number; recordId?: number };

export function openConflictReview(reviewId: number, recordId?: number) {
  if (!Number.isInteger(reviewId) || reviewId <= 0) return;
  window.dispatchEvent(new CustomEvent<ConflictReviewOpenDetail>(CONFLICT_REVIEW_OPEN_EVENT, { detail: { reviewId, recordId } }));
}

export function notifyConflictReviewUpdated(recordId: number) {
  window.dispatchEvent(new CustomEvent(CONFLICT_REVIEW_UPDATED_EVENT, { detail: { recordId } }));
}

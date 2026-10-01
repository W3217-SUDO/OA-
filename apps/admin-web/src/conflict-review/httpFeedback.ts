import type { AxiosError, AxiosInstance, AxiosResponse } from 'axios'
import { message } from 'antd'
import { notifyConflictReviewUpdated, openConflictReview } from './events'
import type { ConflictRecordState } from './types'

type ConflictReviewNotice = {
  id: number
  source_record_id: number
  blocking: boolean
  summary: string
}

type ConflictReviewResponse = {
  data?: { conflict_review?: ConflictReviewNotice }
  conflict_review?: ConflictReviewNotice
  pending_reviews?: Array<{ conflict_review?: ConflictReviewNotice }>
  items?: Array<{ conflict_review?: ConflictReviewNotice; data?: { conflict_review?: ConflictReviewNotice } }>
}

type ConflictReviewRequired = {
  code: 'CONFLICT_REVIEW_REQUIRED'
  record_id: number | string
  message: string
}

type ConflictReviewError = AxiosError & { conflictReview?: ConflictReviewRequired }
type ConflictReviewLoadError = { response?: { status?: number; data?: { detail?: string } } }

async function presentConflictReview(api: AxiosInstance, recordId: number, blockingMessage: string) {
  const sessionToken = localStorage.getItem('access_token')
  const pendingMessage = `${blockingMessage}；请由提交人或利益冲突审批人员处理`
  try {
    const { data } = await api.get<ConflictRecordState>(`/conflict-reviews/record/${recordId}`)
    if (localStorage.getItem('access_token') !== sessionToken) return
    if (data.can_view && data.review) openConflictReview(data.review.id, data.record_id)
    else message.warning(pendingMessage)
  } catch (error) {
    if (localStorage.getItem('access_token') !== sessionToken) return
    const response = error && typeof error === 'object' && 'response' in error
      ? (error as ConflictReviewLoadError).response
      : undefined
    if (response?.status === 403) message.warning(pendingMessage)
    else message.error(response?.data?.detail || '利益冲突审查状态加载失败')
  }
}

export function handleConflictReviewResponse(response: AxiosResponse, api: AxiosInstance) {
  const method = String(response.config.method || 'get').toLowerCase()
  if (method === 'get') return

  const payload = response.data as ConflictReviewResponse | undefined
  const reviews = [
    payload?.data?.conflict_review,
    payload?.conflict_review,
    ...(Array.isArray(payload?.pending_reviews) ? payload.pending_reviews.map(item => item.conflict_review) : []),
    ...(Array.isArray(payload?.items) ? payload.items.flatMap(item => [item.conflict_review, item.data?.conflict_review]) : []),
  ].filter((review): review is ConflictReviewNotice => Number.isInteger(review?.id))

  reviews.forEach(review => notifyConflictReviewUpdated(review.source_record_id))
  const pendingReview = reviews.find(review => review.blocking)
  if (pendingReview) void presentConflictReview(api, pendingReview.source_record_id, pendingReview.summary)
}

export function handleConflictReviewError(error: ConflictReviewError, api: AxiosInstance) {
  const responseData = error.response?.data as { detail?: ConflictReviewRequired | string } | undefined
  const detail = responseData?.detail
  if (error.response?.status !== 409 || !detail || typeof detail === 'string' || detail.code !== 'CONFLICT_REVIEW_REQUIRED') return

  error.conflictReview = detail
  responseData.detail = detail.message
  notifyConflictReviewUpdated(Number(detail.record_id))
  void presentConflictReview(api, Number(detail.record_id), detail.message)
}

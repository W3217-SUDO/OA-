import axios from 'axios'
import { message } from 'antd'
import { notifyConflictReviewUpdated, openConflictReview } from './conflict-review/events'
import type { ConflictRecordState } from './conflict-review/types'

export const AUTH_EXPIRED_EVENT = 'sunhold:auth-expired'
export const api = axios.create({baseURL:'/api/v1'})
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

async function presentConflictReview(recordId: number, blockingMessage: string) {
  const sessionToken = localStorage.getItem('access_token')
  const pendingMessage = `${blockingMessage}；请由提交人或利益冲突审批人员处理`
  try {
    const { data } = await api.get<ConflictRecordState>(`/conflict-reviews/record/${recordId}`)
    if (localStorage.getItem('access_token') !== sessionToken) return
    if (data.can_view && data.review) openConflictReview(data.review.id, data.record_id)
    else message.warning(pendingMessage)
  } catch (error: any) {
    if (localStorage.getItem('access_token') !== sessionToken) return
    if (error?.response?.status === 403) message.warning(pendingMessage)
    else message.error(error?.response?.data?.detail || '利益冲突审查状态加载失败')
  }
}

api.interceptors.response.use(
  response=>{
    const method = String(response.config.method || 'get').toLowerCase()
    if (method !== 'get') {
      const reviews = [
        response.data?.data?.conflict_review,
        response.data?.conflict_review,
        ...(Array.isArray(response.data?.pending_reviews) ? response.data.pending_reviews.map((item: any) => item.conflict_review) : []),
        ...(Array.isArray(response.data?.items) ? response.data.items.flatMap((item: any) => [item.conflict_review, item.data?.conflict_review]) : []),
      ].filter(review => Number.isInteger(review?.id))
      reviews.forEach(review => notifyConflictReviewUpdated(review.source_record_id))
      const pendingReview = reviews.find(review => review.blocking)
      if (pendingReview) void presentConflictReview(pendingReview.source_record_id, pendingReview.summary)
    }
    return response
  },
  error=>{
    const isLoginRequest=String(error.config?.url||'').includes('/auth/login')
    if(error.response?.status===401&&!isLoginRequest&&localStorage.getItem('access_token')){
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
    }
    const detail = error.response?.data?.detail
    if (error.response?.status === 409 && detail?.code === 'CONFLICT_REVIEW_REQUIRED') {
      error.conflictReview = detail
      error.response.data.detail = detail.message
      notifyConflictReviewUpdated(Number(detail.record_id))
      void presentConflictReview(Number(detail.record_id), detail.message)
    }
    return Promise.reject(error)
  },
)

import axios from 'axios'
import { notifyConflictReviewUpdated, openConflictReview } from './conflict-review/events'

export const AUTH_EXPIRED_EVENT = 'sunhold:auth-expired'
export const api = axios.create({baseURL:'/api/v1'})
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  response=>{
    const method = String(response.config.method || 'get').toLowerCase()
    if (method !== 'get') {
      const reviews = [
        response.data?.data?.conflict_review,
        response.data?.conflict_review,
        ...(Array.isArray(response.data?.pending_reviews) ? response.data.pending_reviews.map((item: any) => item.conflict_review) : []),
        ...(Array.isArray(response.data?.items) ? response.data.items.map((item: any) => item.conflict_review) : []),
      ].filter(review => Number.isInteger(review?.id))
      reviews.forEach(review => notifyConflictReviewUpdated(review.source_record_id))
      const pendingReview = reviews.find(review => review.blocking)
      if (pendingReview) openConflictReview(pendingReview.id, pendingReview.source_record_id)
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
      openConflictReview(Number(detail.review_id), Number(detail.record_id))
    }
    return Promise.reject(error)
  },
)

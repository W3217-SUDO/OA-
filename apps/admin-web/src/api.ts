import axios from 'axios'
import { handleConflictReviewError, handleConflictReviewResponse } from './conflict-review/httpFeedback'

export const AUTH_EXPIRED_EVENT = 'sunhold:auth-expired'
export const api = axios.create({baseURL:'/api/v1'})
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  // 带上当前页面：后端按“账号持有这个页面”放行该页发出的读取，页面顺带读取别的中心数据时不再报没有菜单权限。
  const page = typeof window === 'undefined' ? '' : new URLSearchParams(window.location.search).get('page') || ''
  if (page && !config.headers['X-OA-Page']) config.headers['X-OA-Page'] = encodeURIComponent(page).slice(0, 200)
  return config
})

api.interceptors.response.use(
  response=>{
    handleConflictReviewResponse(response, api)
    return response
  },
  error=>{
    const isLoginRequest=String(error.config?.url||'').includes('/auth/login')
    if(error.response?.status===401&&!isLoginRequest&&localStorage.getItem('access_token')){
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
    }
    handleConflictReviewError(error, api)
    return Promise.reject(error)
  },
)

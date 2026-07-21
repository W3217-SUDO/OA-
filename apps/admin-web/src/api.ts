import axios from 'axios'

export const AUTH_EXPIRED_EVENT = 'sunhold:auth-expired'
export const api = axios.create({baseURL:'/api/v1'})
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  response=>response,
  error=>{
    const isLoginRequest=String(error.config?.url||'').includes('/auth/login')
    if(error.response?.status===401&&!isLoginRequest&&localStorage.getItem('access_token')){
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
    }
    return Promise.reject(error)
  },
)

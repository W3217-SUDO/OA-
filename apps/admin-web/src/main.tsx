import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ThemeModeProvider } from './theme/ThemeModeProvider'
import './styles.css'
import './dashboard.css'
import './huzhi-login.css'
import './theme/theme.css'
import { installHasPolyfill } from './legacyHasPolyfill'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'

// 日期选择器的月份、星期跟随 dayjs 语言：设成中文（antd 的 zh_CN 只管按钮文字），一周从周一开始。
dayjs.locale('zh-cn')

// 钉钉手机内核（Chrome 100）不支持 :has()，按构建时登记的条件给元素补类名。
installHasPolyfill()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><ThemeModeProvider><App/></ThemeModeProvider></React.StrictMode>
)

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register('/service-worker.js')
  })
}

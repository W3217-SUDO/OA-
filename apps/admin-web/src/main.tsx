import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ThemeModeProvider } from './theme/ThemeModeProvider'
import './styles.css'
import './dashboard.css'
import './huzhi-login.css'
import './theme/theme.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><ThemeModeProvider><App/></ThemeModeProvider></React.StrictMode>
)

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register('/service-worker.js')
  })
}

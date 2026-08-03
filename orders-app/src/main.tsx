import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'
import { App } from './App'
import { ThemeProvider } from './hooks/useTheme'
import { ToastProvider } from './ui/Toast'
import './index.css'

// Service worker: приложение кэшируется целиком и работает офлайн.
// Новая версия подхватывается автоматически при следующем открытии.
registerSW({ immediate: true })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <ToastProvider>
        <App />
      </ToastProvider>
    </ThemeProvider>
  </StrictMode>,
)

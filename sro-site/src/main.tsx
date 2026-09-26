import React from 'react'
import { flushSync } from 'react-dom'
import ReactDOM from 'react-dom/client'
import '@fontsource-variable/onest'
import '@fontsource-variable/brygada-1918'
import './index.css'
import App from './App'
import { setSiteRoot } from './lib/site'

// Главная лежит в корне: префикса до корня у неё нет.
setSiteRoot('')

// Первая отрисовка — синхронно (flushSync), а сам скрипт в html помечен
// blocking="render" (плагин в vite.config.ts): браузер не показывает страницу,
// пока она не собрана. Без этого плавный переход между страницами снимал бы
// новую страницу пустой — корень у неё заполняет скрипт.
const root = ReactDOM.createRoot(document.getElementById('root')!)
flushSync(() =>
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  ),
)

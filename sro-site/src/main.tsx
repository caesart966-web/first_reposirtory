import React from 'react'
import ReactDOM from 'react-dom/client'
import '@fontsource-variable/onest'
import '@fontsource-variable/brygada-1918'
import './index.css'
import App from './App'
import { setSiteRoot } from './lib/site'

// Главная лежит в корне: префикса до корня у неё нет.
setSiteRoot('')

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

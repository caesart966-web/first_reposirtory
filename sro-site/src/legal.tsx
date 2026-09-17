import React from 'react'
import ReactDOM from 'react-dom/client'
import '@fontsource-variable/inter'
import './index.css'
import { LegalPage } from './components/LegalPage'
import { setSiteRoot } from './lib/site'

// Точка входа страницы с документами о персональных данных
// (/politika-konfidencialnosti/). Глубина вложенности — в её HTML
// (data-root), как и у остальных страниц: страница объявляет о себе сама.
const mount = document.getElementById('root')!
setSiteRoot(mount.dataset.root ?? '../')

ReactDOM.createRoot(mount).render(
  <React.StrictMode>
    <LegalPage />
  </React.StrictMode>,
)

import React from 'react'
import ReactDOM from 'react-dom/client'
import '@fontsource-variable/inter'
import './index.css'
import { ServicePage } from './components/ServicePage'
import { serviceBySlug } from './content/services'
import { setSiteRoot } from './lib/site'

// Точка входа страниц услуг (/uslugi/…). Какая именно страница — в её HTML
// (data-service), глубина вложенности — там же (data-root): страница
// объявляет о себе сама, а не угадывается из адреса. Страницы услуг лежат на
// два уровня ниже корня, поэтому по умолчанию '../../'.
const mount = document.getElementById('root')!
setSiteRoot(mount.dataset.root ?? '../../')

const service = serviceBySlug(mount.dataset.service ?? '')
// Нет такой услуги — уводим на главную, а не показываем белый экран.
if (!service) {
  location.replace('../../')
} else {
  ReactDOM.createRoot(mount).render(
    <React.StrictMode>
      <ServicePage service={service} />
    </React.StrictMode>,
  )
}

import React from 'react'
import ReactDOM from 'react-dom/client'
import '@fontsource-variable/inter'
import './index.css'
import { DetailPage } from './components/DetailPage'
import { detailBySlug } from './content/sroDetails'
import { setSiteRoot } from './lib/site'

// Точка входа страниц видов СРО. Какая именно страница — написано в её HTML
// (data-sro), туда же вынесена глубина вложенности (data-root): страница
// объявляет о себе сама, а не угадывается из адреса.
const mount = document.getElementById('root')!
setSiteRoot(mount.dataset.root ?? '../')

const detail = detailBySlug(mount.dataset.sro ?? '')
// Нет такого вида — уводим на главную, а не показываем белый экран.
if (!detail) {
  location.replace('../')
} else {
  ReactDOM.createRoot(mount).render(
    <React.StrictMode>
      <DetailPage detail={detail} />
    </React.StrictMode>,
  )
}

import React from 'react'
import { renderToString } from 'react-dom/server'
import App from './App'
import { DetailPage } from './components/DetailPage'
import { ServicePage } from './components/ServicePage'
import { detailBySlug } from './content/sroDetails'
import { serviceBySlug } from './content/services'
import { setSiteRoot } from './lib/site'

// Текст страниц прямо в HTML (15.10.2026). Собирается при сборке
// (vite build --ssr, затем scripts/prerender.mjs) теми же компонентами,
// что рисуют страницу в браузере, и вписывается в <div id="root">.
// Нужен поисковику, который не выполняет JavaScript: без этого он видел
// пустую страницу с одним заголовком в <title>.
//
// В браузере страница по-прежнему собирается скриптом заново (createRoot,
// не hydrateRoot): часть разметки зависит от устройства (мышь или палец,
// какая страница открыта), и сверка с сервером спотыкалась бы на ней.
// Готовый текст до сборки спрятан (класс pre-wait, prerender.mjs), поэтому
// посетитель видит сайт ровно таким, как раньше.

export type Target = { root: string; sro?: string; service?: string }

export function render({ root, sro, service }: Target): string {
  setSiteRoot(root)
  let tree: React.ReactNode
  if (sro !== undefined) {
    const detail = detailBySlug(sro)
    if (!detail) throw new Error(`Нет вида СРО «${sro}»`)
    tree = <DetailPage detail={detail} />
  } else if (service !== undefined) {
    const data = serviceBySlug(service)
    if (!data) throw new Error(`Нет услуги «${service}»`)
    tree = <ServicePage service={data} />
  } else {
    tree = <App />
  }
  return renderToString(<React.StrictMode>{tree}</React.StrictMode>)
}

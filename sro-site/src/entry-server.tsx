import React from 'react'
import { renderToString } from 'react-dom/server'
import App from './App'
import { ArticlePage } from './components/ArticlePage'
import { ArticlesIndex } from './components/ArticlesIndex'
import { DetailPage } from './components/DetailPage'
import { ServicePage } from './components/ServicePage'
import { ARTICLES, articleBySlug } from './content/articles'
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

// page="stati" — список статей, article — сама статья (data-page
// и data-article в HTML страницы, как data-sro и data-service).
export type Target = { root: string; sro?: string; service?: string; page?: string; article?: string }

/** Слаги статей — prerender.mjs сверяет с ними страницы в dist. */
export const ARTICLE_SLUGS = ARTICLES.map((a) => a.slug)

export function render({ root, sro, service, page, article }: Target): string {
  setSiteRoot(root)
  let tree: React.ReactNode
  if (article !== undefined) {
    const data = articleBySlug(article)
    if (!data) throw new Error(`Нет статьи «${article}»`)
    tree = <ArticlePage article={data} />
  } else if (page === 'stati') {
    tree = <ArticlesIndex />
  } else if (sro !== undefined) {
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

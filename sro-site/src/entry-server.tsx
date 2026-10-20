import React from 'react'
import { renderToString } from 'react-dom/server'
import App from './App'
import { ArticlePage } from './components/ArticlePage'
import { ArticlesIndex } from './components/ArticlesIndex'
import { DetailPage } from './components/DetailPage'
import { ServicePage } from './components/ServicePage'
import { ARTICLES, articleBySlug } from './content/articles'
import { SRO_DETAILS, detailBySlug } from './content/sroDetails'
import { SERVICE_PAGES, serviceBySlug } from './content/services'
import { setPagePath, setSiteRoot } from './lib/site'

// Текст страниц прямо в HTML (15.10.2026). Собирается при сборке
// (vite build --ssr, затем scripts/prerender.mjs) теми же компонентами,
// что рисуют страницу в браузере, и вписывается в <div id="root">.
// Нужен поисковику, который не выполняет JavaScript: без этого он видел
// пустую страницу с одним заголовком в <title>.
//
// С 20.10.2026 браузер эту разметку не пересобирает, а подхватывает
// (hydrateRoot, lib/start.tsx): она видна сразу, до скрипта, и на телефоне
// первый экран появляется на 0,7–0,9 с раньше. Всё, что зависит от
// устройства (мышь или палец) и от адреса (подсветка в меню), сделано так,
// чтобы первая отрисовка в браузере совпадала с этой: адрес страницы
// передаёт prerender.mjs (path), устройство решается после подхвата.

// page="stati" — список статей, article — сама статья (data-page
// и data-article в HTML страницы, как data-sro и data-service).
// path — адрес страницы от корня сайта ('/sro-stroiteley/'), как его увидит
// меню в браузере (lib/site.ts, isCurrentPage).
export type Target = { root: string; path?: string; sro?: string; service?: string; page?: string; article?: string }

/** Слаги статей — prerender.mjs сверяет с ними страницы в dist. */
export const ARTICLE_SLUGS = ARTICLES.map((a) => a.slug)

/** Опечатка в `on` у статьи молча убрала бы её из «Статей по теме»:
 *  prerender.mjs вызывает проверку и роняет сборку. */
export function checkArticlePlaces() {
  const known = new Set([...SRO_DETAILS.map((d) => d.slug), ...SERVICE_PAGES.map((s) => s.slug)])
  const wrong = ARTICLES.flatMap((a) => a.on.filter((place) => !known.has(place)).map((place) => `${a.slug}: «${place}»`))
  if (wrong.length) throw new Error(`Неизвестные страницы в on у статей: ${wrong.join(', ')}`)
}

export function render({ root, path, sro, service, page, article }: Target): string {
  setSiteRoot(root)
  setPagePath(path ?? '/')
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

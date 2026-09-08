import type { APIRoute } from 'astro'
import { getCollection } from 'astro:content'
import { SITE } from '../config/site'

// Лента базы знаний.
//
// Зачем она сайту, который никто не читает в RSS-читалке. Лента — это
// машинный список материалов с датами: по ней робот видит, что на сайте
// появилось нового, не обходя все двадцать шесть статей. Яндекс.Вебмастер
// принимает её отдельным источником, агрегаторы и боты в мессенджерах
// подхватывают сами. Стоит она сорок строк и не требует ни одной
// зависимости, поэтому пусть будет.
//
// Полные тексты статей сюда не кладём: лента должна вести на сайт,
// а не заменять его.

const escape = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

export const GET: APIRoute = async ({ site }) => {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '')
  const abs = (path: string) => new URL(base + path, site).toString()

  const articles = (await getCollection('articles')).sort(
    (a, b) =>
      (b.data.updated ?? b.data.published).getTime() - (a.data.updated ?? a.data.published).getTime(),
  )

  const items = articles
    .map((a) => {
      const url = abs(`/baza-znaniy/${a.id}/`)
      return [
        '    <item>',
        `      <title>${escape(a.data.title)}</title>`,
        `      <link>${url}</link>`,
        `      <guid isPermaLink="true">${url}</guid>`,
        `      <description>${escape(a.data.excerpt)}</description>`,
        `      <pubDate>${(a.data.updated ?? a.data.published).toUTCString()}</pubDate>`,
        '    </item>',
      ].join('\n')
    })
    .join('\n')

  const latest = articles[0]?.data
  const built = (latest ? (latest.updated ?? latest.published) : new Date()).toUTCString()

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>База знаний — ${escape(SITE.brand)}</title>
    <link>${abs('/baza-znaniy/')}</link>
    <description>Разборы норм о саморегулировании: кому нужно членство в СРО, сколько оно стоит, как проверить свою СРО и что изменилось в законе.</description>
    <language>ru</language>
    <lastBuildDate>${built}</lastBuildDate>
    <atom:link href="${abs('/rss.xml')}" rel="self" type="application/rss+xml" />
${items}
  </channel>
</rss>
`

  return new Response(body, {
    headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' },
  })
}

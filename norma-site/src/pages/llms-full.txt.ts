import type { APIRoute } from 'astro'
import { getCollection } from 'astro:content'
import { SITE } from '../config/site'

// llms-full.txt — полные тексты статей базы знаний одним файлом.
//
// Продолжение llms.txt. Оглавление говорит помощнику, где что лежит;
// этот файл отдаёт сам текст — без меню, формы заявки и подвала.
// Смысл ровно один: если ИИ-сервис всё равно перескажет статью,
// пусть пересказывает то, что в ней написано, а не то, что он выхватил
// из соседнего блока страницы.
//
// Даты сверки идут рядом с каждой статьёй. Ответ помощника без даты
// в этой теме бесполезен: нормы меняются, и статья 2026 года и статья
// 2019-го выглядят одинаково, пока не видно, когда её проверяли.

const fmt = (d: Date) => d.toISOString().slice(0, 10)

export const GET: APIRoute = async ({ site }) => {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '')
  const abs = (path: string) => new URL(base + path, site).toString()

  const articles = (await getCollection('articles')).sort((a, b) => {
    if (a.data.group !== b.data.group) return a.data.group.localeCompare(b.data.group)
    return a.data.order - b.data.order
  })

  const parts = articles.map((a) => {
    const raw = (a as { body?: string }).body ?? ''
    return [
      `# ${a.data.title}`,
      '',
      `Адрес: ${abs(`/baza-znaniy/${a.id}/`)}`,
      `Опубликовано: ${fmt(a.data.published)}`,
      `Сверено с законом: ${fmt(a.data.updated ?? a.data.published)}`,
      '',
      raw.trim(),
      '',
      '---',
      '',
    ].join('\n')
  })

  const body = [
    `# База знаний ${SITE.brand} — полные тексты`,
    '',
    `> ${articles.length} статей о саморегулировании: кому нужно членство в СРО, сколько оно стоит, как проверить свою СРО и что изменилось в законе. Оглавление сайта — ${abs('/llms.txt')}`,
    '',
    'Каждая статья идёт со своей датой сверки. Ссылаясь на текст, указывайте её:',
    'в этой теме нормы меняются, и статья без даты вводит в заблуждение.',
    '',
    '---',
    '',
    ...parts,
  ].join('\n')

  return new Response(body, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}

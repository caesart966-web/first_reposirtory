// Отдаёт собранный сайт по подпапке — точно так же, как это делает GitHub Pages.
// Нужен, чтобы проверить превью-сборку до публикации.
//
// Запуск: node scripts/serve-subpath.mjs /first_reposirtory/norma/ 4321

import { createServer } from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { join, extname, resolve } from 'node:path'

const BASE = process.argv[2] || '/'
const PORT = Number(process.argv[3] || 4321)
const DIST = resolve('dist')

const types = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
  '.php': 'text/plain; charset=utf-8', // Pages не выполняет PHP — отдаёт как текст
}

createServer(async (req, res) => {
  const url = decodeURIComponent((req.url || '/').split('?')[0])

  if (!url.startsWith(BASE)) {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' })
    res.end('404 — вне базового пути ' + BASE)
    return
  }

  let rel = url.slice(BASE.length) || ''
  let file = join(DIST, rel)

  try {
    const info = await stat(file).catch(() => null)
    if (!info || info.isDirectory()) file = join(file, 'index.html')
    const body = await readFile(file)
    res.writeHead(200, { 'Content-Type': types[extname(file)] || 'application/octet-stream' })
    res.end(body)
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' })
    res.end('<h1>404</h1>')
  }
}).listen(PORT, '127.0.0.1', () => {
  console.log(`Сайт открыт: http://127.0.0.1:${PORT}${BASE}`)
})

import { defineConfig } from 'astro/config'
import sitemap from '@astrojs/sitemap'

// Куда собираем сайт.
//
// Боевой режим (свой домен):   SITE_URL=https://ваш-домен.ru  BASE_PATH=/
// Превью на GitHub Pages:      SITE_URL=https://<логин>.github.io  BASE_PATH=/<репозиторий>/norma/  NOINDEX=1
//
// NOINDEX=1 закрывает сборку от поисковиков (мета-тег robots и robots.txt) —
// черновик с превью-ссылкой не должен попасть в выдачу. Боевая сборка на своём
// домене делается без NOINDEX.
const SITE_URL = process.env.SITE_URL || 'https://example.ru'
const BASE_PATH = process.env.BASE_PATH || '/'

export default defineConfig({
  site: SITE_URL,
  base: BASE_PATH,
  trailingSlash: 'always',
  // Политика обработки данных индексируется наравне с остальными страницами:
  // поисковики считают её признаком добросовестного сайта.
  integrations: [sitemap()],
  build: {
    format: 'directory',
    inlineStylesheets: 'auto',
  },
})

import { createHash } from 'node:crypto'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Скрипт страницы — render-blocking: браузер не рисует страницу, пока скрипт
// её не собрал. Нужно плавному переходу между страницами (@view-transition
// в index.css): иначе новая страница снималась бы пустой. Первого показа
// это не задерживает — до скрипта на странице и так пусто.
const renderBlockingEntry = {
  name: 'render-blocking-entry',
  transformIndexHtml: {
    order: 'post' as const,
    handler: (html: string) =>
      html.replace(/<script type="module" crossorigin/g, '<script type="module" blocking="render" crossorigin'),
  },
}

// Отпечатки картинок из public/img (01.10.2026). Картинки лежат под
// постоянными именами, и браузер, однажды скачав hero-day.webp, показывал
// сохранённую копию и после заливки новой: у заказчика на первом экране
// стоял дневной кадр от 17.09 вместо нынешнего крана. asset() дописывает
// к адресу ?v=<первые 8 знаков md5 содержимого> — поменялся файл, поменялся
// и адрес, а неизменённые кадры остаются в кеше.
const imgDir = resolve(__dirname, 'public/img')
const assetVersions = Object.fromEntries(
  readdirSync(imgDir)
    .filter((name) => /\.(avif|webp|png|jpe?g|svg)$/i.test(name))
    .map((name) => [
      `img/${name}`,
      createHash('md5').update(readFileSync(resolve(imgDir, name))).digest('hex').slice(0, 8),
    ]),
)

// Раздел «Статьи» (15.10.2026): список stati/index.html и по папке на статью.
// Папки пишет scripts/build-articles.mjs из content/articles.ts, поэтому
// точки входа собираются обходом, а не списком: новая статья не требует
// правки конфигурации.
const statiDir = resolve(__dirname, 'stati')
const articleInputs = existsSync(statiDir)
  ? Object.fromEntries(
      readdirSync(statiDir, { withFileTypes: true })
        .filter((entry) => entry.isDirectory() && existsSync(resolve(statiDir, entry.name, 'index.html')))
        .map((entry) => [`statya-${entry.name}`, resolve(statiDir, entry.name, 'index.html')]),
    )
  : {}

// base: './' — собранный сайт работает из любого подкаталога (хостинг, GitHub Pages).
//
// Точек входа одиннадцать: главная, три страницы видов СРО и семь страниц услуг. Каждая — обычный
// статический html со своим адресом: роутера в браузере нет, поэтому ссылки
// работают и без JS, поисковик видит три отдельные страницы, а хостингу не
// нужен фолбэк на index.html. Рукописные пути внутри компонентов (картинки
// из public/, якоря на секции главной) знают о своей глубине через
// src/lib/site.ts — см. комментарий там.
export default defineConfig({
  plugins: [react(), renderBlockingEntry],
  base: './',
  define: { __ASSET_VERSIONS__: JSON.stringify(assetVersions) },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        stroiteli: resolve(__dirname, 'sro-stroiteley/index.html'),
        proektirovshchiki: resolve(__dirname, 'sro-proektirovshchikov/index.html'),
        izyskateli: resolve(__dirname, 'sro-izyskateley/index.html'),
        // Страницы услуг: семь адресов под /uslugi/, точка входа src/service.tsx.
        usluga_vstuplenie: resolve(__dirname, 'uslugi/vstuplenie-v-sro/index.html'),
        usluga_podbor: resolve(__dirname, 'uslugi/podbor-i-proverka-sro/index.html'),
        usluga_dokumenty: resolve(__dirname, 'uslugi/dokumenty/index.html'),
        usluga_nrs: resolve(__dirname, 'uslugi/specialisty-nrs/index.html'),
        usluga_nok: resolve(__dirname, 'uslugi/nok/index.html'),
        usluga_uroven: resolve(__dirname, 'uslugi/uroven-otvetstvennosti/index.html'),
        usluga_proverki: resolve(__dirname, 'uslugi/soprovozhdenie-proverok/index.html'),
        // Статьи: список и сами статьи, точка входа src/stati.tsx.
        ...(existsSync(resolve(statiDir, 'index.html')) ? { stati: resolve(statiDir, 'index.html') } : {}),
        ...articleInputs,
      },
    },
  },
})

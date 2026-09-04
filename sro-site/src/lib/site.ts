// Где страница лежит относительно корня сайта.
//
// Сайт собирается несколькими точками входа: главная в корне и три страницы
// видов СРО в подпапках. Собранные Vite ресурсы (js, css, шрифты) он
// расставляет сам, а вот пути, написанные руками, — нет: './img/desk.webp'
// на странице /sro-stroiteley/ превратится в /sro-stroiteley/img/desk.webp,
// и картинка не найдётся. Якоря такие же: '#services' внутри подпапки ведёт
// в никуда, потому что секции живут на главной.
//
// Поэтому оба вида ссылок проходят через asset() и anchor(). Точка входа
// объявляет свою глубину один раз — setSiteRoot('../') — и дальше о ней
// можно не думать.
//
// Проверку «а не забыли ли вызвать» делает набор pages.mjs: он открывает
// каждую страницу и требует, чтобы все картинки реально загрузились, а
// ссылки шапки и подвала вели на существующие адреса.
let root = ''

export function setSiteRoot(value: string) {
  root = value
}

/** Путь к файлу из public/: asset('./img/desk.webp'). */
export const asset = (path: string) => root + path.replace(/^\.\//, '')

/** Ссылка на секцию главной: anchor('#services'). */
export const anchor = (hash: string) => root + hash

/** Главная страница: на ней самой — наверх, со вложенной — на её адрес. */
export const home = () => root || '#top'

/** Адрес страницы вида СРО: page('sro-stroiteley'). */
export const page = (dir: string) => `${root}${dir}/`

/** Адрес главной с уже выбранным видом СРО: home + '?sro=construction#quiz'. */
export const quizWithType = (slug: string) => `${root}?sro=${slug}#quiz`

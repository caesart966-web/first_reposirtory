import '@fontsource-variable/onest'
import '@fontsource-variable/brygada-1918'
import './index.css'
import { ArticlePage } from './components/ArticlePage'
import { ArticlesIndex } from './components/ArticlesIndex'
import { articleBySlug } from './content/articles'
import { markArrival } from './lib/arrival'
import { setSiteRoot } from './lib/site'
import { start } from './lib/start'

// Точка входа раздела «Статьи»: список (/stati/) и сами статьи
// (/stati/<slug>/). Какая страница — в её HTML: data-article у статьи,
// у списка его нет; глубина — data-root. Страницы пишет
// scripts/build-articles.mjs из content/articles.ts.
const mount = document.getElementById('root')!
// Пришли со своей страницы — без вступления (lib/arrival.ts).
markArrival()

const slug = mount.dataset.article
setSiteRoot(mount.dataset.root ?? (slug ? '../../' : '../'))

const article = slug ? articleBySlug(slug) : undefined
// Статьи с таким адресом нет — уводим к списку, а не показываем белый экран.
if (slug && !article) {
  location.replace('../')
} else {
  // Готовая разметка подхватывается — см. lib/start.tsx.
  start(mount, article ? <ArticlePage article={article} /> : <ArticlesIndex />)
}

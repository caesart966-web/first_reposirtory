import '@fontsource-variable/onest'
import '@fontsource-variable/brygada-1918'
import './index.css'
import { DetailPage } from './components/DetailPage'
import { detailBySlug } from './content/sroDetails'
import { markArrival } from './lib/arrival'
import { setSiteRoot } from './lib/site'
import { start } from './lib/start'

// Точка входа страниц видов СРО. Какая именно страница — написано в её HTML
// (data-sro), туда же вынесена глубина вложенности (data-root): страница
// объявляет о себе сама, а не угадывается из адреса.
const mount = document.getElementById('root')!
// Пришли со своей страницы — без вступления (lib/arrival.ts).
markArrival()

setSiteRoot(mount.dataset.root ?? '../')

const detail = detailBySlug(mount.dataset.sro ?? '')
// Нет такого вида — уводим на главную, а не показываем белый экран.
if (!detail) {
  location.replace('../')
} else {
  // Готовая разметка подхватывается — см. lib/start.tsx.
  start(mount, <DetailPage detail={detail} />)
}

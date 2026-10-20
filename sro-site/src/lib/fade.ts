// Фотография, которая грузится заметно долго, проступает, когда готова,
// а не возникает рывком посреди открытой страницы (01.10.2026, заказчик:
// «чтобы картинки тоже плавно появлялись при переключении»).
//
// Подключается как ref у <img>. До загрузки кадр всё равно не нарисован,
// поэтому прозрачность 0 на это время ничего не меняет на экране. Пришёл
// быстро (до 0,2 с — из кеша браузера, при переходе между страницами чаще
// всего так) — показывается сразу: его прикрывает сама смена страниц,
// а медленное проявление готового кадра на главной давало бы вспышку —
// обложка на миг светлела бы до бумаги под ней. Пришёл позже — сначала
// раскодируется (decode), потом проступает за 0,7 с. При «уменьшить
// движение» длительность гасит общее правило index.css.
const SLOW_MS = 200

export function fadeIn(img: HTMLImageElement | null) {
  if (!img || img.dataset.fade || (img.complete && img.naturalWidth > 0)) return
  const start = performance.now()
  img.dataset.fade = 'wait'
  img.style.opacity = '0'
  const show = (slow: boolean) => {
    img.dataset.fade = slow ? 'done' : 'fast'
    if (slow) img.style.transition = 'opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1)'
    img.style.opacity = ''
  }
  img.addEventListener(
    'load',
    () => {
      if (performance.now() - start < SLOW_MS) show(false)
      else void img.decode().catch(() => {}).then(() => show(true))
    },
    { once: true },
  )
  img.addEventListener('error', () => show(false), { once: true })
}

// Кадр первого экрана (главная, шапки страниц), 20.10.2026. На первом заходе
// поверх кадра идёт «проявление» (.hero-develop гаснет 2,6 с) — оно и есть
// плавное появление. С тех пор как скрипт не ждёт отрисовки, он почти всегда
// подхватывает страницу раньше, чем кадр загрузился, и fadeIn прятал бы кадр
// до загрузки и раскодирования, а потом проявлял ещё раз поверх проявления:
// на медленном телефонном интернете главная картинка появлялась на ~1 с
// позже, а у «СРО строителей» браузер и вовсе не засчитывал её показ
// (Largest Contentful Paint). Пока проявление идёт, кадр показывается сам,
// как только загрузится, под гаснущим листом. Не успел до конца проявления
// (очень медленная сеть) — проступает сам, как у fadeIn. Пришли со своей
// страницы (проявления нет) — обычный fadeIn.
const developing = () =>
  document
    .getAnimations()
    .some((a) => (a as CSSAnimation).animationName === 'develop' && a.playState === 'running')

export function fadeInFirstScreen(img: HTMLImageElement | null) {
  if (!img || img.dataset.fade) return
  if (!developing()) return fadeIn(img)
  if (img.complete) return
  img.dataset.fade = 'develop'
  img.addEventListener(
    'load',
    () => {
      if (developing()) return
      // Проявление кончилось раньше кадра: прячем до первой отрисовки
      // (обработчик load идёт раньше неё) и проступаем со следующего кадра.
      img.style.opacity = '0'
      requestAnimationFrame(() => {
        img.style.transition = 'opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1)'
        img.style.opacity = ''
      })
    },
    { once: true },
  )
}

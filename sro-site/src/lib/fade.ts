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

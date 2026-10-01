// Переход внутри сайта без рывка (01.10.2026, заказчик: «дёргается, когда
// открываю раздел, и когда выхожу — тоже»).
//
// Страница, открытая с другой страницы сайта или кнопкой «Назад», не
// проигрывает вступление: кадр не «проявляется» из чёрного, заголовок
// не поднимается по словам, блоки первого экрана не выплывают. Её и так
// показывает плавная смена страниц (@view-transition в index.css), а
// вступление поверх смены читалось как подёргивание: страница
// проступала, и тут же всё в ней начинало ехать заново. На главной после
// «Назад» обложка ещё две секунды разгоралась из чёрного.
// Вступление осталось для первого захода на сайт — по ссылке из поиска,
// из мессенджера, набранным адресом.
//
// Классы на <html>: arrived — насовсем (снимает анимации первого экрана),
// arrived-settling — на время смены (снимает переходы .reveal у блоков,
// которые уже в кадре; ниже кадра блоки выплывают при прокрутке, как всегда).
// Вызывается до первой отрисовки: скрипт страницы блокирует отрисовку.
export function markArrival() {
  const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined
  let inside = nav?.type === 'back_forward'
  try {
    inside ||= Boolean(document.referrer) && new URL(document.referrer).origin === location.origin
  } catch {
    // Испорченный referrer — значит, вступление.
  }
  if (!inside) return
  const html = document.documentElement
  html.classList.add('arrived', 'arrived-settling')
  window.setTimeout(() => html.classList.remove('arrived-settling'), 1200)
}

export const arrivedFromSite = () => document.documentElement.classList.contains('arrived-settling')

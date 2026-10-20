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
// С 20.10.2026 скрипт страницы не блокирует отрисовку: готовая разметка
// видна раньше, чем он выполнится. Поэтому то же самое делает строчка
// в <head> (scripts/prerender.mjs) — до первой отрисовки — и ставит
// data-arrival; здесь тогда делать нечего. markArrival остался для
// страницы без готовой разметки (npm run dev). arrived-settling снимает
// lib/mounted.ts — через 1,2 с после подхвата страницы.
export function markArrival() {
  if (document.documentElement.hasAttribute('data-arrival')) return
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
}

export const arrivedFromSite = () => document.documentElement.classList.contains('arrived-settling')

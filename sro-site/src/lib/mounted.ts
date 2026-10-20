// Страница подхвачена скриптом (20.10.2026).
//
// До 20.10.2026 готовый текст страницы (scripts/prerender.mjs) был спрятан
// классом pre-wait, пока скрипт не соберёт страницу заново (createRoot),
// а сам скрипт блокировал отрисовку (blocking="render"). На телефоне
// с медленным интернетом первый экран появлялся только через ~1,9 с —
// столько шёл и выполнялся скрипт. Теперь готовая разметка видна сразу,
// а скрипт её подхватывает (hydrateRoot) — без пересборки и без мигания.
//
// markMounted зовёт компонент Mounted (ниже) из своего эффекта: эффект
// родителя срабатывает после эффектов всех вложенных компонентов, то есть
// когда блоки в кадре уже отмечены видимыми (ui/Reveal.tsx). Класс mounted:
// - отменяет запасной pre-late (скрипт не пришёл за 4 с — prerender.mjs);
// - снимает «всё видно», которое держится, пока пришедшая со своей страницы
//   страница ещё не подхвачена (html.arrived-settling:not(.mounted) в index.css);
// - через 1,2 с снимает arrived-settling, как раньше делал markArrival.
export function markMounted() {
  const html = document.documentElement
  html.classList.remove('pre-wait')
  html.classList.add('mounted')
  if (html.classList.contains('arrived-settling')) {
    window.setTimeout(() => html.classList.remove('arrived-settling'), 1200)
  }
}

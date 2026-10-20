import React, { type ReactNode } from 'react'
import ReactDOM from 'react-dom/client'
import { Mounted } from './Mounted'
import { setPagePath } from './site'

// Запуск страницы — общий для всех точек входа (20.10.2026).
//
// Текст страницы лежит в HTML готовым (scripts/prerender.mjs) и виден сразу,
// до скрипта. Скрипт его не пересобирает, а подхватывает (hydrateRoot):
// навешивает обработчики на ту же разметку. Для этого первая отрисовка
// в браузере обязана совпасть с готовой разметкой узел в узел — поэтому
// всё, что зависит от устройства (мышь или палец, «уменьшить движение»),
// решается в эффектах или через useSyncExternalStore, а не прямо в отрисовке.
// Расхождение React пишет ошибкой в консоль — её ловит scripts/test-site.mjs.
//
// Без готовой разметки (npm run dev) корень пустой, и страница собирается
// обычным образом.
export function start(mount: HTMLElement, page: ReactNode) {
  setPagePath(location.pathname)
  const tree = (
    <React.StrictMode>
      <Mounted>{page}</Mounted>
    </React.StrictMode>
  )
  if (mount.firstElementChild) ReactDOM.hydrateRoot(mount, tree)
  else ReactDOM.createRoot(mount).render(tree)
}

import { useSyncExternalStore } from 'react'

// Компьютер — это мышь или трекпад: указатель точный и умеет наведение.
// Ширина экрана здесь не годится: планшет в альбомной ориентации шире
// ноутбука, а приложения на нём открываются как на телефоне — обычным
// переходом по ссылке.
const QUERY = '(hover: hover) and (pointer: fine)'

// С 20.10.2026 страница приходит готовой разметкой, и браузер её подхватывает
// (hydrateRoot), а не рисует заново. Готовая разметка собрана без браузера —
// там «не компьютер» (false). useSyncExternalStore при подхвате берёт то же
// false и сразу после него перерисовывает ссылку с настоящим значением:
// без него ссылки мессенджеров на компьютере остались бы без новой вкладки.
// Подписка нужна для ноутбуков с сенсорным экраном: подключили мышь —
// запрос поменялся.
const subscribe = (onChange: () => void) => {
  const query = window.matchMedia(QUERY)
  query.addEventListener('change', onChange)
  return () => query.removeEventListener('change', onChange)
}

export function useDesktopPointer(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    () => false,
  )
}

import { useEffect, useState } from 'react'

// Компьютер — это мышь или трекпад: указатель точный и умеет наведение.
// Ширина экрана здесь не годится: планшет в альбомной ориентации шире
// ноутбука, а приложения на нём открываются как на телефоне — обычным
// переходом по ссылке.
const QUERY = '(hover: hover) and (pointer: fine)'

// Страница рисуется только в браузере (index.html пустой), поэтому первое
// значение берём сразу — без мигания «ссылка → кнопка» после отрисовки.
// Подписка нужна для ноутбуков с сенсорным экраном: подключили мышь —
// запрос поменялся.
export function useDesktopPointer(): boolean {
  const [desktop, setDesktop] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(QUERY).matches,
  )

  useEffect(() => {
    const query = window.matchMedia(QUERY)
    const onChange = () => setDesktop(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  return desktop
}

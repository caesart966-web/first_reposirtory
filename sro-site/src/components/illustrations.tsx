// Фирменные SVG-иллюстрации сайта: тонкая линейная графика, цвет наследуется
// от родителя через currentColor. Без растровых изображений и внешних запросов.
//
// Силуэт города (CitySkyline) удалён 30.08.2026, сетка чертежа (BlueprintGrid)
// — 24.09.2026 вместе с прежним первым экраном. Обе восстанавливаются из
// истории git, если оформление вернётся к линейной графике.
type Props = { className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }

// Знак компании: весы под фронтоном (с 25.09.2026, выбор заказчика из четырёх
// вариантов). Коромысло весов — треугольник фронтона: это и фронтон здания
// суда, и кровля дома, то есть закон и стройка — ровно то, чем занимается
// компания. Толстое и тонкое, как у гравюры: фронтон, колонна и чаши плотные,
// подвесы тоньше. Толщины подобраны под высоту 24–32px: тоньше 1,4 подвесы
// на такой высоте пропадают.
//
// Те же координаты — в public/favicon.svg, public/404.html
// и scripts/build-og.mjs: меняете знак — меняйте во всех четырёх.
// Прежний знак (весы без колонны, viewBox 0 0 46 26) — в истории git.
export function ScalesMark({ className = '' }: Props) {
  return (
    <svg
      className={className}
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="-1 2 50 37.4"
      fill="currentColor"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3.2 12.6 24 3.6l20.8 9Z" fill="none" strokeWidth="2.2" />
      <path d="M24 12.6v20" fill="none" strokeWidth="2.4" />
      <path d="M5.2 13.4.6 25.2m4.6-11.8 4.6 11.8m33-11.8-4.6 11.8m4.6-11.8 4.6 11.8" fill="none" strokeWidth="1.4" />
      <path d="M-.4 25.2h11.2q-5.6 7.2-11.2 0Zm37.6 0h11.2q-5.6 7.2-11.2 0Z" stroke="none" />
      <path d="M20.4 32.4h7.2l2.2 4.2H18.2Z" stroke="none" />
      <path d="M16.2 37.9h15.6" fill="none" strokeWidth="1.6" />
    </svg>
  )
}

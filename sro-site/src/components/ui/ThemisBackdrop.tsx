import { asset } from '../../lib/site'

// Фирменный водяной знак: архивная гравюра «Themis» позади всего контента.
// Зафиксирован во вьюпорте, контент проезжает поверх. Вне потока, не ловит
// клики, скрыт от скринридеров.
//
// Почему mix-blend-multiply: у гравюры прямоугольная белая подложка, вырезать
// её из растра нечем. При multiply белое становится прозрачным само, остаётся
// только штрих.
//
// Высота всегда меньше 100vh и всегда задана в vh — только так фигура целиком
// помещается по вертикали на любом экране. Ширина кадра равна 0.586 высоты,
// поэтому при этих коэффициентах картинка не упирается в боковые края даже на
// самом узком телефоне. Центр смещён на 32px вниз, иначе на низких ноутбуках
// голова уходит под липкую шапку.
//
// Маска центрована по фигуре и держит сплошную зону до 60% радиуса: голова,
// весы и кисть с мечом идут в полную силу, книзу фигура растворяется — иначе
// нижний срез кадра читается как случайная линейка.
//
// Прозрачность задана в index.css (.themis-backdrop img) — там же зафиксирован
// потолок по ТЗ (не выше 0.06) и более деликатное значение для телефона.
export function ThemisBackdrop() {
  return (
    <div
      className="themis-backdrop pointer-events-none fixed inset-0 z-0 select-none overflow-hidden"
      aria-hidden="true"
    >
      <img
        src={asset('./img/themis.webp')}
        alt=""
        width={938}
        height={1600}
        loading="lazy"
        decoding="async"
        className="
          absolute w-auto max-w-none
          h-[58vh] sm:h-[76vh] lg:h-[84vh]
          top-[calc(50%+32px)] -translate-y-1/2
          left-1/2 -translate-x-1/2 sm:left-auto sm:translate-x-0
          sm:right-0 lg:right-[3%] xl:right-[8%]
          mix-blend-multiply
          [mask-image:radial-gradient(78%_64%_at_50%_44%,#000_0%,#000_60%,transparent_100%)]
          [-webkit-mask-image:radial-gradient(78%_64%_at_50%_44%,#000_0%,#000_60%,transparent_100%)]
        "
      />
    </div>
  )
}

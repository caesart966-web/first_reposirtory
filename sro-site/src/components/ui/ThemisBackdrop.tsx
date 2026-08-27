// Фирменный водяной знак: архивная гравюра «Themis» во всю высоту экрана.
// Зафиксирован во вьюпорте, контент проезжает поверх. Вне потока, не ловит
// клики, скрыт от скринридеров.
//
// Почему mix-blend-multiply: у гравюры прямоугольная белая подложка, вырезать
// её из растра нечем. При multiply белое становится прозрачным само, остаётся
// только штрих.
//
// Почему hidden sm:block: на 360px в кадр попадает случайный фрагмент драпировки —
// читается как посторонняя линия, а не как фактура.
//
// Прозрачность задана в index.css (.themis-backdrop img) — там же зафиксирован
// потолок по ТЗ: не выше 0.06.
export function ThemisBackdrop() {
  return (
    <div
      className="themis-backdrop pointer-events-none fixed inset-0 z-0 select-none overflow-hidden"
      aria-hidden="true"
    >
      <img
        src="./img/themis.webp"
        alt=""
        width={938}
        height={1600}
        loading="lazy"
        decoding="async"
        className="
          absolute right-[-14%] top-1/2 h-[135vh] w-auto max-w-none -translate-y-1/2
          mix-blend-multiply
          hidden sm:block lg:right-[-2%] xl:right-[3%]
          [mask-image:radial-gradient(58%_52%_at_58%_50%,#000_0%,#000_42%,transparent_100%)]
          [-webkit-mask-image:radial-gradient(58%_52%_at_58%_50%,#000_0%,#000_42%,transparent_100%)]
        "
      />
    </div>
  )
}

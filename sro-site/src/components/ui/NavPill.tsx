import { ArrowUpRight } from 'lucide-react'
import type { ReactNode } from 'react'

// Кнопка-пилюля «куда ведёт строка»: название страницы и кружок со стрелкой,
// высота 56 px, как у кнопок размера lg (ui/Button.tsx). Сама по себе
// не ссылка — стоит внутри строки-ссылки с классом group, и нажимается вся
// строка; при наведении на строку пилюля заливается графитом, кружок
// светлеет и поворачивается.
//
// Где ставится (29.09.2026): только там, где строка говорит об одном,
// а ведёт на страницу с другим названием — «Скоро договор, а членства
// в СРО нет» → «Вступление в СРО», «Что входит в каждый документ» →
// «Подготовка документов». Там, где название строки и есть страница
// («СРО строителей», «Услуги по теме»), — простой кружок со стрелкой:
// подпись повторила бы заголовок. Стрелка в каждой кнопке сайта перестала
// бы что-либо значить — это и есть примета шаблона.
export function NavPill({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex h-14 items-center justify-between gap-4 justify-self-start rounded-full border border-neutral-300 bg-neutral-50 pl-6 pr-2 text-[15px] font-medium text-neutral-950 transition-colors duration-500 ease-silk group-hover:border-neutral-950 group-hover:bg-neutral-950 group-hover:text-neutral-50 ${className}`}
    >
      {children}
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-neutral-950 text-neutral-50 transition-all duration-700 ease-silk group-hover:rotate-45 group-hover:bg-neutral-50 group-hover:text-neutral-950">
        <ArrowUpRight className="h-5 w-5" aria-hidden="true" />
      </span>
    </span>
  )
}

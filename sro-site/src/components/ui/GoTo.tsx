import { ArrowRight } from 'lucide-react'
import type { ReactNode } from 'react'

// «Куда ведёт строка»: подпись и стрелка, без рамки и кружка (с 01.10.2026).
//
// Раньше переход на страницу показывали кружки со стрелкой — в конце строк,
// в углу карточек, в «пилюле» с подписью. Их было по пять–семь на экране,
// и тот же кружок стоял в кнопке «Связаться»: главное действие страницы
// тонуло среди одинаковых значков. Теперь правило одно: кружок со стрелкой —
// только в кнопках «Связаться» (ui/Button.tsx, arrow), он значит «написать
// мне»; переход на другую страницу — стрелка, как в оглавлении документа.
//
// Стоит внутри ссылки с классом group: нажимается вся строка, а при
// наведении подпись подчёркивается и стрелка сдвигается вправо.
// Без подписи — одна стрелка (строки, где название и есть страница).
// tone: ink — чернилами; muted — серым, при наведении чернилами
// (подпись-подсказка рядом с крупным названием); light — на тёмной карточке.
const TONE = {
  ink: 'text-neutral-950',
  muted: 'text-neutral-600 group-hover:text-neutral-950',
  light: 'text-neutral-50',
} as const

export function GoTo({
  children,
  tone = 'ink',
  className = '',
}: {
  children?: ReactNode
  tone?: keyof typeof TONE
  className?: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-2 font-medium transition-colors duration-500 ease-silk ${TONE[tone]} ${className}`}
    >
      {children && (
        <span className="bg-[linear-gradient(currentColor,currentColor)] bg-[length:0%_1px] bg-left-bottom bg-no-repeat pb-0.5 transition-[background-size] duration-700 ease-silk group-hover:bg-[length:100%_1px] group-focus-visible:bg-[length:100%_1px]">
          {children}
        </span>
      )}
      <ArrowRight
        className={`shrink-0 transition-transform duration-500 ease-silk group-hover:translate-x-1 group-focus-visible:translate-x-1 ${
          children ? 'h-4 w-4' : 'h-5 w-5'
        }`}
        aria-hidden="true"
      />
    </span>
  )
}

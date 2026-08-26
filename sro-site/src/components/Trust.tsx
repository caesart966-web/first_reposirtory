import { FileSignature, HandCoins, Lock, RussianRuble, UserRound } from 'lucide-react'
import { Reveal } from './ui/Reveal'

const ITEMS = [
  { icon: FileSignature, label: 'Договор' },
  { icon: RussianRuble, label: 'Прозрачная стоимость' },
  { icon: HandCoins, label: 'Без скрытых платежей' },
  { icon: UserRound, label: 'Личная работа' },
  { icon: Lock, label: 'Конфиденциальность' },
]

export function Trust() {
  return (
    <section className="border-y border-neutral-200/70 bg-neutral-50/70 py-9">
      <Reveal className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-center gap-x-10 gap-y-4 px-4 sm:px-6 lg:px-8">
        {ITEMS.map((item) => (
          <div key={item.label} className="flex items-center gap-2.5 text-sm font-medium text-neutral-700">
            <item.icon className="h-5 w-5 text-accent-600" aria-hidden="true" />
            {item.label}
          </div>
        ))}
      </Reveal>
    </section>
  )
}

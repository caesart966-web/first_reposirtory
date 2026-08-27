import { FACTS, isPlaceholder } from '../content/facts'
import { Reveal } from './ui/Reveal'

// Лозунги вроде «прозрачная стоимость» ничего не сообщают: их пишут все.
// Полоса под первым экраном показывает факты, которые можно проверить.
const ITEMS = [
  { value: FACTS.yearsOfPractice, label: 'лет занимаюсь СРО' },
  { value: FACTS.companies, label: 'компаний сопровождал' },
  { value: FACTS.regions, label: 'регионов России' },
  { value: FACTS.responseTime, label: 'срок ответа на заявку' },
]

export function Trust() {
  return (
    <section className="border-y border-neutral-200/70 bg-neutral-50/55 py-10">
      <Reveal className="mx-auto grid w-full max-w-5xl grid-cols-2 gap-8 px-4 sm:px-6 lg:grid-cols-4 lg:px-8">
        {ITEMS.map((item) => (
          <div key={item.label}>
            {/* Пока вместо цифры стоит плейсхолдер, набираем его мелко:
                крупным кеглем длинная строка в скобках ломает сетку. */}
            <p
              className={`font-bold tracking-tight text-neutral-950 tabular-nums ${
                isPlaceholder(item.value) ? 'break-words text-base' : 'text-3xl'
              }`}
            >
              {item.value}
            </p>
            <p className="mt-1 text-sm text-neutral-600">{item.label}</p>
          </div>
        ))}
      </Reveal>
    </section>
  )
}

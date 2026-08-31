import { ChevronDown } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Ответ может быть не только строкой: где уместно — ссылка на нужную секцию,
// чтобы не пересказывать её содержимое второй раз.
const ITEMS: { q: string; a: ReactNode }[] = [
  {
    q: 'Сколько времени занимает вступление?',
    a: 'Срок зависит от готовности документов, требований выбранной СРО и наличия специалистов НРС. После короткого разбора вашей ситуации назову реалистичный срок именно для вашего случая — без обещаний «для всех».',
  },
  {
    q: 'Какие документы нужны?',
    a: 'Базовый набор — заявление, регистрационные документы, сведения об организации и документы специалистов. Точный список зависит от конкретной СРО и видов работ: составлю его под вашу ситуацию и помогу собрать недостающее.',
  },
  {
    q: 'Можно ли вступить без специалистов НРС?',
    a: 'Наличие специалистов в национальном реестре — одно из ключевых требований к членам СРО. Если специалистов пока нет, разберём вашу ситуацию и обсудим законные варианты её решения.',
  },
  {
    q: 'Сколько стоит?',
    // Единственный ответ, который не отвечал: отсылал на два экрана назад,
    // к разделу, где цифры тоже нет. Теперь отвечает на месте (формулировкой
    // из «Стоимости») и ведёт вперёд — к квизу, а не против течения страницы.
    a: (
      <>
        Платить нужно только за работу: разговоры и разбор задачи не тарифицируются, сколько
        бы их ни потребовалось. Цена работы зависит от вида СРО и объёма — что уже готово,
        а что придётся собирать. Точную сумму назову письменно до начала. Быстрее всего —{' '}
        <a href="#quiz" className="font-medium text-accent-700 underline underline-offset-2">
          ответить на несколько вопросов в форме ниже
        </a>
        .
      </>
    ),
  },
  {
    q: 'Можно ли подобрать другую СРО?',
    a: 'Да. Если условия текущей СРО не устраивают, помогу сравнить альтернативы, проверить их и корректно оформить переход.',
  },
  {
    q: 'Можно ли всё оформить дистанционно?',
    a: 'Да, как правило, весь процесс проходит дистанционно: вопросы решаем по телефону, в мессенджерах и по почте, документы — в электронном виде или курьерской доставкой. Приезжать лично обычно не нужно; если встреча всё же понадобится, обсудим удобный формат.',
  },
  {
    q: 'Как проверить СРО?',
    a: 'По открытым государственным реестрам и документам самой организации: действующий статус, требования к членам, состояние компенсационных фондов. Такую проверку я провожу до подачи документов и оплаты взносов.',
  },
  {
    q: 'Чем отличается частный специалист от крупной компании?',
    a: 'Ответственностью и скоростью. За результат отвечает один исполнитель, а не цепочка отделов: не нужно объяснять задачу заново на каждом этапе, решения принимаются быстрее, и история вашей компании не теряется при передаче. И нет наценки за бренд.',
  },
]

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <Section id="faq" size="compact" className="bg-neutral-50/55">
      <SectionHeading eyebrow="FAQ" title="Частые вопросы" />
      <Reveal className="mt-10">
        <div className="mx-auto max-w-3xl divide-y divide-neutral-200 rounded-2xl border border-neutral-200 bg-white shadow-card">
          {ITEMS.map((item, index) => {
            const open = openIndex === index
            return (
              <div key={item.q}>
                <h3>
                  <button
                    type="button"
                    onClick={() => setOpenIndex(open ? null : index)}
                    aria-expanded={open}
                    aria-controls={`faq-panel-${index}`}
                    id={`faq-button-${index}`}
                    className="flex w-full items-center justify-between gap-4 px-5 py-5 text-left font-semibold text-neutral-900 transition hover:text-accent-700 sm:px-7"
                  >
                    {item.q}
                    <ChevronDown
                      className={`h-5 w-5 shrink-0 text-neutral-500 transition-transform duration-300 ${
                        open ? 'rotate-180 text-accent-600' : ''
                      }`}
                      aria-hidden="true"
                    />
                  </button>
                </h3>
                <div
                  id={`faq-panel-${index}`}
                  role="region"
                  aria-labelledby={`faq-button-${index}`}
                  aria-hidden={!open}
                  className={`grid transition-all duration-300 ease-in-out ${
                    open ? 'visible grid-rows-[1fr] opacity-100' : 'invisible grid-rows-[0fr] opacity-0'
                  }`}
                >
                  <div className="overflow-hidden">
                    <p className="px-5 pb-6 text-neutral-600 sm:px-7">{item.a}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </Reveal>
    </Section>
  )
}

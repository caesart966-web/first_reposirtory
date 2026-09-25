import { Plus } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Ответ может быть не только строкой: где уместно — ссылка на нужную секцию,
// чтобы не пересказывать её содержимое второй раз.
//
// id — адрес вопроса: на #faq-check ведёт карточка «Проверка СРО» из «Услуг»,
// и по такой ссылке вопрос раскрывается сам (см. эффект ниже). Без этого
// ссылка привозила бы к закрытому списку, где нужный ответ ещё надо найти.
const ITEMS: { id: string; q: string; a: ReactNode }[] = [
  {
    id: 'time',
    q: 'Сколько времени занимает вступление?',
    a: 'Срок зависит от готовности документов, требований выбранной СРО и наличия специалистов НРС. По закону саморегулируемая организация рассматривает заявление не более двух месяцев; на практике решение обычно принимается быстрее. Точный срок для вашего случая назову после разбора документов.',
  },
  {
    id: 'docs',
    q: 'Какие документы нужны?',
    a: 'Базовый набор — заявление, регистрационные документы, сведения об организации и документы специалистов. Точный список зависит от конкретной СРО и видов работ: составлю его под вашу ситуацию и помогу собрать недостающее.',
  },
  {
    id: 'nrs',
    q: 'Можно ли вступить без специалистов НРС?',
    // Самый частый стопор, и короткого ответа ему мало: раньше здесь было
    // «обсудим законные варианты», после чего человек уходил ровно с тем же
    // непониманием. Варианты разобраны отдельной секцией, отсюда ссылка.
    a: (
      <>
        Нет. Не менее двух специалистов, включённых в национальный реестр и работающих по
        основному месту работы, — обязательное требование к члену СРО. Если таких сотрудников
        пока нет, есть три законных варианта: проверить действующих сотрудников, включить
        своего специалиста в реестр или принять в штат специалиста, уже состоящего в нём.
        Подробнее в разделе{' '}
        <a href="#nrs" className="font-medium text-accent-700 underline underline-offset-2">
          «Специалисты НРС»
        </a>
        .
      </>
    ),
  },
  {
    id: 'price',
    q: 'Сколько стоит?',
    // Единственный ответ, который не отвечал: отсылал на два экрана назад,
    // к разделу, где цифры тоже нет. Теперь отвечает на месте (формулировкой
    // из «Стоимости») и ведёт вперёд — к квизу, а не против течения страницы.
    a: (
      <>
        Консультации бесплатны на любом этапе. Оплачивается только работа: подготовка
        документов и сопровождение. Стоимость зависит от вида СРО и объёма работы и
        согласовывается письменно до начала. Назову её после короткого разговора —{' '}
        <a href="#contacts" className="font-medium text-accent-700 underline underline-offset-2">
          позвоните или напишите
        </a>
        .
      </>
    ),
  },
  {
    id: 'choose',
    q: 'Можно ли подобрать другую СРО?',
    a: 'Да. Если условия текущей СРО не устраивают, помогу сравнить альтернативы, проверить их и корректно оформить переход.',
  },
  {
    id: 'remote',
    q: 'Можно ли всё оформить дистанционно?',
    a: 'Да, как правило, весь процесс проходит дистанционно: вопросы решаем по телефону, в мессенджерах и по почте, документы — в электронном виде или курьерской доставкой. Приезжать лично обычно не нужно; если встреча всё же понадобится, обсудим удобный формат.',
  },
  {
    id: 'check',
    q: 'Как проверить СРО?',
    a: 'По открытым государственным реестрам и документам самой организации: действующий статус, требования к членам, состояние компенсационных фондов. Такую проверку я провожу до подачи документов и оплаты взносов.',
  },
  {
    id: 'one',
    q: 'Чем отличается работа с одним специалистом от крупной компании?',
    a: 'За результат отвечает один специалист, а не цепочка отделов: задачу не нужно объяснять заново на каждом этапе, вопросы решаются быстрее, а сведения о вашей компании не теряются при передаче между сотрудниками.',
  },
]

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  // Ссылка вида #faq-check раскрывает свой вопрос: при загрузке страницы
  // с таким адресом и при переходе по ссылке с этой же страницы (hashchange).
  useEffect(() => {
    const openFromHash = () => {
      const match = window.location.hash.match(/^#faq-([a-z]+)$/)
      if (!match) return
      const index = ITEMS.findIndex((item) => item.id === match[1])
      if (index < 0) return
      setOpenIndex(index)
      // Раскрытие одного вопроса сворачивает открытый выше по списку, и
      // страница «уезжает» на высоту его ответа — цель оказывалась под шапкой.
      // Доводим прокрутку, когда анимация сворачивания (300 мс) закончилась.
      window.setTimeout(() => {
        document.getElementById(`faq-${match[1]}`)?.scrollIntoView({ block: 'start' })
      }, 350)
    }
    openFromHash()
    window.addEventListener('hashchange', openFromHash)
    return () => window.removeEventListener('hashchange', openFromHash)
  }, [])

  return (
    <Section id="faq">
      <div className="grid gap-12 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-20">
        <div>
          <SectionHeading eyebrow="Вопросы" title="Частые вопросы" />
        </div>
        {/* Вопросы строками с тонкими линейками, без карточки: знак «+»
            поворачивается в «×», ответ раскрывается мягко, на той же кривой
            silk, что и все переходы сайта. */}
        <Reveal className="border-t border-neutral-300">
          {ITEMS.map((item, index) => {
            const open = openIndex === index
            return (
              <div key={item.q} id={`faq-${item.id}`} className="scroll-mt-24 border-b border-neutral-300">
                <h3>
                  <button
                    type="button"
                    onClick={() => setOpenIndex(open ? null : index)}
                    aria-expanded={open}
                    aria-controls={`faq-panel-${index}`}
                    id={`faq-button-${index}`}
                    className="group flex w-full items-center justify-between gap-6 py-6 text-left"
                  >
                    <span className="font-display text-[1.45rem] font-medium leading-snug text-neutral-950 transition-colors duration-500 group-hover:text-accent-700 sm:text-[1.6rem]">
                      {item.q}
                    </span>
                    <Plus
                      className={`h-5 w-5 shrink-0 text-neutral-950 transition-transform duration-700 ease-silk ${
                        open ? 'rotate-45' : ''
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
                  className={`grid transition-all duration-700 ease-silk ${
                    open ? 'visible grid-rows-[1fr] opacity-100' : 'invisible grid-rows-[0fr] opacity-0'
                  }`}
                >
                  <div className="overflow-hidden">
                    <p className="max-w-2xl pb-7 leading-relaxed text-neutral-600">{item.a}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </Reveal>
      </div>
    </Section>
  )
}

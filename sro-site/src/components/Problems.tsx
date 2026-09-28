import { ArrowUpRight } from 'lucide-react'
import { serviceBySlug } from '../content/services'
import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Три типовые ситуации. Каждая строка ведёт на страницу услуги, где ситуация
// разобрана подробно: сроки — на «Вступление в СРО» (порядок и сроки по
// закону), документы — на «Подготовку документов», НРС — на «Специалистов
// НРС». До 25.09.2026 две строки вели в «Связаться» и в короткий раздел
// главной: человек нажимал стрелку за подробностями и попадал на телефон.
// Подпись у стрелки — название страницы, куда она ведёт.
//
// Строки, а не карточки: раздел должен читаться иначе, чем сетка услуг ниже.
//
// Текст переписан 28.09.2026: заказчик попросил убрать то, что выдаёт текст
// нейросети. Заголовки — словами клиента, как он сам описал бы свою
// ситуацию, а не канцелярскими «Срочное вступление» и «Вопрос по…».
// Ушли одинаковые по ритму фразы из трёх глаголов («проверю, укажу
// и помогу»), подпись «Выберите ситуацию, похожую на вашу: по каждой — …»,
// объяснявшая читателю, что делать с разделом, и надзаголовок «Типовые
// ситуации», повторявший заголовок. Смысл каждой строки прежний.
const target = (slug: string) => {
  const service = serviceBySlug(slug)
  if (!service) throw new Error(`Нет страницы услуги: ${slug}`)
  return { href: page(service.path), action: service.short }
}

const SCENARIOS = [
  {
    title: 'Скоро договор, а членства в СРО нет',
    text: 'Скажу, реально ли успеть к вашей дате и что для этого понадобится от вас.',
    ...target('vstuplenie'),
  },
  {
    title: 'Документы собраны, нужна проверка',
    text: 'Посмотрю комплект до подачи в СРО и помогу исправить то, что найду.',
    ...target('dokumenty'),
  },
  {
    title: 'Нет специалистов в НРС',
    text: 'Проверю, подходят ли ваши сотрудники. Если нет, расскажу, какие варианты даёт закон.',
    ...target('nrs'),
  },
]

export function Problems() {
  return (
    <Section id="problems">
      <SectionHeading title="С чем обычно обращаются" />
      <div className="mt-14 border-t border-neutral-300">
        {SCENARIOS.map((scenario, index) => (
          <Reveal key={scenario.title} delay={index * 90}>
            <a
              href={scenario.href}
              className="group grid gap-4 border-b border-neutral-300 py-8 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-10 sm:py-10"
            >
              <span className="min-w-0">
                <span className="block font-display text-[1.75rem] font-medium leading-tight text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-accent-700 sm:text-[2.1rem]">
                  {nbsp(scenario.title)}
                </span>
                <span className="mt-3 block max-w-2xl leading-relaxed text-neutral-600">
                  {nbsp(scenario.text)}
                </span>
              </span>
              <span className="inline-flex items-center gap-2 text-sm font-medium text-neutral-950">
                {scenario.action}
                <span className="flex h-11 w-11 items-center justify-center rounded-full border border-neutral-300 transition-all duration-700 ease-silk group-hover:rotate-45 group-hover:border-neutral-950 group-hover:bg-neutral-950 group-hover:text-neutral-50">
                  <ArrowUpRight className="h-5 w-5" aria-hidden="true" />
                </span>
              </span>
            </a>
          </Reveal>
        ))}
      </div>
    </Section>
  )
}

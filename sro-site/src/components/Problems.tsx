import { ArrowUpRight } from 'lucide-react'
import { serviceBySlug } from '../content/services'
import { anchor, page } from '../lib/site'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Три типовые ситуации. Раньше каждая строка открывала квиз с готовым
// ответом; квиза больше нет, и строка ведёт туда, где ситуация разобрана
// подробно: документы — на страницу услуги, НРС — в раздел о специалистах,
// сроки — в «Связаться», потому что срок называется только после разговора.
//
// Строки, а не карточки: раздел должен читаться иначе, чем сетка услуг
// ниже. Крупная цифра слева — номер, а не украшение: ситуаций ровно три.
const documentsPage = serviceBySlug('dokumenty')

const SCENARIOS = [
  {
    title: 'Срочное вступление в СРО',
    text: 'Подходит срок заключения договора, а членства в СРО ещё нет. Оценю, какие сроки реальны в вашей ситуации, и назову, что потребуется от вас.',
    href: '#contacts',
    action: 'Обсудить сроки',
  },
  {
    title: 'Нужна проверка документов',
    text: 'Проверю подготовленный комплект до подачи в СРО, укажу на недочёты и помогу их устранить.',
    href: documentsPage ? page(documentsPage.path) : anchor('#documents'),
    action: 'Подготовка документов',
  },
  {
    title: 'Вопрос по специалистам НРС',
    text: 'Разберу требования к образованию, стажу и документам специалистов и предложу порядок действий.',
    href: anchor('#nrs'),
    action: 'Специалисты НРС',
  },
]

export function Problems() {
  return (
    <Section id="problems">
      <SectionHeading
        eyebrow="Типовые ситуации"
        title="С чем обычно обращаются"
        subtitle="Выберите ситуацию, похожую на вашу: по каждой — что делаю и с чего начать."
      />
      <div className="mt-14 border-t border-neutral-300">
        {SCENARIOS.map((scenario, index) => (
          <Reveal key={scenario.title} delay={index * 90}>
            <a
              href={scenario.href}
              className="group grid gap-3 border-b border-neutral-300 py-8 sm:grid-cols-[5rem_minmax(0,1fr)_auto] sm:items-baseline sm:gap-8 sm:py-10"
            >
              <span className="font-display text-2xl text-neutral-500 sm:text-3xl" aria-hidden="true">
                0{index + 1}
              </span>
              <span className="min-w-0">
                <span className="block font-display text-[1.75rem] font-medium leading-tight text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-accent-700 sm:text-[2.1rem]">
                  {scenario.title}
                </span>
                <span className="mt-3 block max-w-2xl leading-relaxed text-neutral-600">
                  {scenario.text}
                </span>
              </span>
              <span className="inline-flex items-center gap-2 text-sm font-medium text-neutral-950">
                {scenario.action}
                <span className="flex h-9 w-9 items-center justify-center rounded-full border border-neutral-300 transition-all duration-700 ease-silk group-hover:rotate-45 group-hover:border-neutral-950 group-hover:bg-neutral-950 group-hover:text-neutral-50">
                  <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                </span>
              </span>
            </a>
          </Reveal>
        ))}
      </div>
    </Section>
  )
}

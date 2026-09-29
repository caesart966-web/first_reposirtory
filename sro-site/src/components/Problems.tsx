import { serviceBySlug } from '../content/services'
import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { NavPill } from './ui/NavPill'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Три типовые ситуации. Каждая строка ведёт на страницу услуги, где ситуация
// разобрана подробно: сроки — на «Вступление в СРО» (порядок и сроки по
// закону), документы — на «Подготовку документов», НРС — на «Специалистов
// НРС». До 25.09.2026 две строки вели в «Связаться» и в короткий раздел
// главной: человек нажимал стрелку за подробностями и попадал на телефон.
// Подпись на кнопке — название страницы, куда она ведёт.
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
      <SectionHeading title="С чем обращаются" />
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
              {/* Кнопка-пилюля с названием страницы (ui/NavPill.tsx). Все три
                  одной ширины — стрелки стоят в одну линию. До 29.09.2026
                  здесь была подпись мелким шрифтом у кружка 44 px — заказчик
                  попросил «чуть больше и профессиональнее». */}
              <NavPill className="sm:w-[17rem] sm:justify-self-end">{scenario.action}</NavPill>
            </a>
          </Reveal>
        ))}
      </div>
    </Section>
  )
}

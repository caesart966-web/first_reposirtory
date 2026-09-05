import { Scale, UserPlus, UserSearch, Users } from 'lucide-react'
import { anchor } from '../lib/site'
import { ButtonLink } from './ui/Button'
import { cardHoverStatic } from './ui/card'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Специалисты НРС — то, обо что чаще всего спотыкаются на входе в СРО.
//
// В FAQ ответ на это есть, но короткий. Здесь варианты названы прямо, все
// три, в деловом тоне: требование закона, потом что делать. Отдельный блок,
// а не строчка в услугах: в «Услугах» НРС и НОК стоят карточками «помогу
// с тем-то», а вопрос у посетителя другой — «у меня их нет, мне можно?».
//
// Тон намеренно ровный, без острот и афоризмов: заказчик попросил, чтобы
// текст читался как написанный специалистом по СРО, а не сочинённый.

// id — для ссылок из «Услуг»: карточка «НОК» ведёт сюда, ко второму варианту.
const WAYS = [
  {
    id: 'nrs-own',
    icon: UserSearch,
    title: 'Проверить действующих сотрудников',
    text: 'Нередко сотрудник с подходящим образованием и стажем уже работает в компании, но в реестр не внесён. Проверю дипломы, стаж и должностные обязанности и определю, соответствует ли он требованиям.',
  },
  {
    id: 'nrs-nok',
    icon: UserPlus,
    title: 'Включить своего специалиста в реестр',
    text: 'Для включения в НРС требуются профильное высшее образование, стаж работы по специальности и действующее свидетельство о независимой оценке квалификации: с сентября 2022 года НОК обязательна. Подготовлю комплект документов и подам заявление.',
  },
  {
    id: 'nrs-hire',
    icon: Users,
    title: 'Принять в штат специалиста из реестра',
    text: 'Специалист, уже включённый в НРС, оформляется по основному месту работы: это условие закона. Перед оформлением проверю его сведения в реестре.',
  },
]

export function Specialists() {
  return (
    <Section id="nrs">
      <SectionHeading
        eyebrow="Специалисты НРС"
        title="Специалисты НРС: требование закона и варианты решения"
        subtitle="Для членства в СРО в штате организации должно быть не менее двух специалистов, включённых в национальный реестр. Если таких сотрудников пока нет, вопрос решается: ниже три законных варианта."
      />

      {/* Сначала норма, потом варианты. Иначе получается разговор о способах
          обойти требование, а требование настоящее и никуда не денется. */}
      <Reveal className="mt-10">
        <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-card sm:p-7">
          <div className="flex items-start gap-3.5">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-50 text-accent-600">
              <Scale className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-neutral-950">Требование закона</h3>
              <p className="mt-2 text-sm leading-relaxed text-neutral-600">
                В штате члена СРО по основному месту работы должно быть не менее двух
                специалистов по организации работ, сведения о которых внесены в национальный
                реестр специалистов (НРС). Специализация зависит от вида СРО: организация
                строительства, подготовки проектной документации или инженерных изысканий.
                Работа по совместительству не учитывается.
              </p>
              <span className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-600">
                <Scale className="h-3 w-3 shrink-0" aria-hidden="true" />
                ст. 55.5-1, ст. 55.6 ГрК РФ
              </span>
            </div>
          </div>
        </div>
      </Reveal>

      <div className="mt-6 grid gap-4 sm:gap-5 lg:grid-cols-3">
        {WAYS.map((way, index) => (
          <Reveal key={way.title} delay={index * 70} className="h-full scroll-mt-24" id={way.id}>
            {/* Карточка только читается — подсветка есть, подъёма нет:
                приподнятая карточка обещает клик, а кликать тут нечего. */}
            <article
              className={`h-full rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6 ${cardHoverStatic}`}
            >
              <div className="flex items-center gap-3.5 sm:block">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-50 text-accent-600 sm:h-11 sm:w-11">
                  <way.icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <h3 className="font-semibold text-neutral-950 sm:mt-5">{way.title}</h3>
              </div>
              <p className="mt-2.5 text-sm leading-relaxed text-neutral-600 sm:mt-2">{way.text}</p>
            </article>
          </Reveal>
        ))}
      </div>

      {/* Оговорка на месте: сайт держится на том, что здесь не обещают
          невозможного. «Аренда» специалиста — первое, что предлагают
          посредники, и об этом стоит сказать самим. */}
      <Reveal delay={80} className="mt-6">
        <div className="rounded-2xl border-l-4 border-accent-500 bg-accent-50/70 p-6 sm:p-7">
          <h3 className="font-semibold text-neutral-950">Что важно учитывать</h3>
          <p className="mt-2.5 text-sm leading-relaxed text-neutral-700">
            «Аренда» специалистов и фиктивное трудоустройство задачу не решают: соответствие
            требованиям СРО проверяет не только при приёме в члены, но и в ходе последующего
            контроля.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-neutral-700">
            Свидетельство о независимой оценке квалификации действует ограниченный срок. После
            его истечения специалист исключается из реестра, и организация перестаёт
            соответствовать требованию о двух специалистах. При сопровождении членства
            отслеживаю эти сроки заранее.
          </p>
        </div>
      </Reveal>

      <Reveal delay={120} className="mt-8 text-center">
        <p className="text-neutral-600">
          Не уверены, соответствует ли ваш сотрудник требованиям? Пришлите документы: проверю
          и дам ответ.
        </p>
        <ButtonLink href={anchor('#quiz')} size="lg" className="mt-5">
          Проверить сотрудника
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

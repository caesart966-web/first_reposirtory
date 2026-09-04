import { Scale, UserPlus, UserSearch, Users } from 'lucide-react'
import { anchor } from '../lib/site'
import { ButtonLink } from './ui/Button'
import { cardHoverStatic } from './ui/card'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Специалисты НРС — то, обо что чаще всего спотыкаются на входе в СРО.
//
// В FAQ ответ на это был, но короткий: «разберём вашу ситуацию и обсудим
// законные варианты». Для самого частого стопора этого мало — человек уходит
// со страницы ровно в том же непонимании, с каким пришёл. Здесь варианты
// названы прямо, все три.
//
// Отдельный блок, а не строчка в услугах: в «Услугах» НРС и НОК стоят
// карточками «помогу с тем-то», и это ответ на вопрос «что вы делаете».
// А вопрос у посетителя другой — «у меня их нет, мне вообще можно?».

const WAYS = [
  {
    icon: UserSearch,
    title: 'Посмотреть, кто уже есть у вас',
    text: 'Часто подходящий человек в компании работает, просто не внесён в реестр. Смотрим образование, стаж и должностные обязанности — и сразу видно, есть кандидат или нет.',
  },
  {
    icon: UserPlus,
    title: 'Внести своего специалиста в реестр',
    text: 'Нужны профильное высшее образование, стаж и действующее свидетельство о независимой оценке квалификации: с сентября 2022 года НОК обязательна для включения в реестр. Документы готовлю и подаю я.',
  },
  {
    icon: Users,
    title: 'Взять специалиста со стороны',
    text: 'Того, кто уже включён в реестр. Условие одно и оно жёсткое — основное место работы у вас. Проверю кандидата по реестру до того, как вы его оформите.',
  },
]

export function Specialists() {
  return (
    <Section id="nrs">
      <SectionHeading
        eyebrow="Специалисты НРС"
        title="Нет специалистов в реестре — это ещё не отказ"
        subtitle="Требование о двух специалистах — то, обо что чаще всего спотыкаются. Оно обязательное, но выполнимое: ниже три законных пути и честно о том, чего делать нельзя."
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
              <h3 className="font-semibold text-neutral-950">Что требует закон</h3>
              <p className="mt-2 text-sm leading-relaxed text-neutral-600">
                Не менее двух специалистов по организации работ, сведения о которых включены
                в национальный реестр, — и по основному месту работы, а не по совместительству.
                Специализация зависит от вида СРО: организация строительства, подготовки
                проектной документации или инженерных изысканий.
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
          <Reveal key={way.title} delay={index * 70} className="h-full">
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
          посредники, и об этом честнее сказать самому. */}
      <Reveal delay={80} className="mt-6">
        <div className="rounded-2xl border-l-4 border-accent-500 bg-accent-50/70 p-6 sm:p-7">
          <h3 className="font-semibold text-neutral-950">Чего я делать не буду</h3>
          <p className="mt-2.5 text-sm leading-relaxed text-neutral-700">
            Оформлять специалиста, который у вас не работает. «Аренда» специалиста и
            фиктивное трудоустройство — не лазейка, а риск: соответствие требованиям
            проверяют не только на входе, СРО контролирует его и дальше.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-neutral-700">
            И ещё один срок, о котором забывают: свидетельство о независимой оценке
            квалификации действует ограниченное время. Истекло — специалист выбывает
            из реестра, а компания перестаёт соответствовать требованию о двух
            специалистах. Если сопровождаю членство, за этим слежу я.
          </p>
        </div>
      </Reveal>

      <Reveal delay={120} className="mt-8 text-center">
        <p className="text-neutral-600">
          Не знаете, подходит ли ваш сотрудник? Опишите ситуацию — посмотрю по документам
          и скажу прямо, без «нужно приходить и разбираться».
        </p>
        <ButtonLink href={anchor('#quiz')} size="lg" className="mt-5">
          Разобрать мою ситуацию
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

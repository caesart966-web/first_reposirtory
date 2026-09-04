import { ArrowLeft, ArrowRight, Check, Scale } from 'lucide-react'
import type { SroDetail } from '../content/sroDetails'
import { LAW } from '../content/sroDetails'
import { anchor, home, quizWithType } from '../lib/site'
import { Footer } from './Footer'
import { Header } from './Header'
import { LegalProvider } from './LegalDocs'
import { MobileBar } from './MobileBar'
import { ButtonLink } from './ui/Button'
import { Figure } from './ui/Figure'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'
import { ThemisBackdrop } from './ui/ThemisBackdrop'

// Ссылка на норму. Не украшение: на странице есть суммы и пороги, и каждый
// из них посетитель должен уметь проверить сам, не веря нам на слово.
function Law({ children }: { children: string }) {
  return (
    <span className="mt-1.5 inline-flex items-center gap-1.5 rounded-md bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-600">
      <Scale className="h-3 w-3 shrink-0" aria-hidden="true" />
      {children}
    </span>
  )
}

function FundTable({
  caption,
  rows,
  law,
}: {
  caption: string
  rows: { limit: string; amount: string }[]
  law: string
}) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6">
      <h3 className="font-semibold text-neutral-950">{caption}</h3>
      <Law>{law}</Law>
      {/* Таблица прокручивается внутри себя, а не тянет за собой страницу:
          две колонки с суммами на 360px в строку не помещаются. */}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[280px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-neutral-200 text-left align-bottom">
              <th className="pb-2 pr-4 font-medium text-neutral-600">
                Обязательства по одному договору
              </th>
              <th className="pb-2 text-right font-medium text-neutral-600">Взнос</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.limit} className="border-b border-neutral-100 last:border-0">
                <td className="py-2.5 pr-4 text-neutral-700">{row.limit}</td>
                <td className="py-2.5 text-right font-semibold tabular-nums text-neutral-950">
                  {row.amount}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function DetailPage({ detail }: { detail: SroDetail }) {
  return (
    <LegalProvider>
      <div id="top" className="relative">
        <ThemisBackdrop />
        <div className="relative z-10">
          <Header />
          <main>
            {/* Первый экран страницы: заголовок, короткая строка и хлебная
                крошка назад. Кадр — тот же, что на карточке главной: человек
                пришёл с неё и должен узнать, куда попал. */}
            <Section size="compact" className="bg-accent-50/60">
              <Reveal>
                <a
                  href={anchor('#types')}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-accent-700 transition hover:text-accent-800"
                >
                  <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden="true" />
                  Все виды СРО
                </a>
              </Reveal>
              <div className="mt-6 grid gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] lg:items-center lg:gap-14">
                <Reveal>
                  <h1 className="text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl lg:text-[2.6rem] lg:leading-[1.1]">
                    {detail.title}
                  </h1>
                  <p className="mt-5 text-lg text-neutral-600">{detail.lead}</p>
                  <div className="mt-7 flex flex-wrap gap-3">
                    <ButtonLink href={quizWithType(detail.slug)} size="lg">
                      Обсудить задачу
                    </ButtonLink>
                  </div>
                </Reveal>
                <Reveal delay={90}>
                  <Figure {...detail.card.image} ratio="aspect-[16/9]" />
                </Reveal>
              </div>
            </Section>

            {/* Кому членство обязательно. Каждый пункт — с нормой: это ответ
                на вопрос «а мне точно надо», и отвечать на него без ссылки
                на закон значило бы продавать, а не объяснять. */}
            <Section>
              <Reveal>
                <h2 className="text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl">
                  Членство обязательно, если
                </h2>
              </Reveal>
              <div className="mt-8 grid gap-4 sm:gap-5 lg:grid-cols-2">
                {detail.who.map((item, index) => (
                  <Reveal key={item.text} delay={(index % 2) * 70} className="h-full">
                    <div className="h-full rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6">
                      <div className="flex gap-3.5">
                        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-accent-50 text-accent-600">
                          <Check className="h-3.5 w-3.5" aria-hidden="true" />
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm leading-relaxed text-neutral-700">{item.text}</p>
                          <Law>{item.law}</Law>
                        </div>
                      </div>
                    </div>
                  </Reveal>
                ))}
              </div>
              <Reveal className="mt-6 rounded-2xl border border-neutral-200 bg-neutral-50 p-5 text-sm leading-relaxed text-neutral-700 sm:p-6">
                {/* Отдельной строкой и на каждой странице: «допуск СРО» до сих
                    пор ищут в поиске, и человек, пришедший за ним, должен
                    сразу понять, что искать нужно другое. */}
                <strong className="font-semibold text-neutral-950">
                  Свидетельств о допуске СРО не существует с 1 июля 2017 года.
                </strong>{' '}
                Их отменили, а право выполнять работы подтверждается членством в
                саморегулируемой организации и выпиской из реестра. Если вам предлагают
                «купить допуск» — предлагают то, чего нет.
                <Law>{LAW.noAdmission}</Law>
              </Reveal>
            </Section>

            {/* Область деятельности: что именно закрывает этот вид СРО. */}
            <Section size="compact" className="bg-neutral-50/55">
              <Reveal>
                <h2 className="text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl">
                  Что входит в область деятельности
                </h2>
                <p className="mt-3 max-w-2xl text-neutral-600">{detail.card.text}</p>
              </Reveal>
              <Reveal className="mt-7 flex flex-wrap gap-2.5">
                {detail.scope.map((item) => (
                  <span
                    key={item}
                    className="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-800"
                  >
                    {item}
                  </span>
                ))}
              </Reveal>
            </Section>

            {/* Взносы. Главная цифра страницы — и главный риск: без оговорки
                про минимумы таблица читается окончательным счётом. */}
            <Section>
              <Reveal>
                <h2 className="text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl">
                  Взносы в компенсационные фонды
                </h2>
                <p className="mt-3 max-w-3xl text-neutral-600">
                  Взнос в фонд возмещения вреда вносят все члены СРО. Взнос в фонд обеспечения
                  договорных обязательств — только те, кто собирается участвовать в закупках
                  по 44-ФЗ и 223-ФЗ.
                </p>
              </Reveal>
              <div className="mt-8 grid gap-5 lg:grid-cols-2">
                <Reveal className="h-full">
                  <FundTable
                    caption="Компенсационный фонд возмещения вреда"
                    rows={detail.funds.harm.rows}
                    law={detail.funds.harm.law}
                  />
                </Reveal>
                <Reveal delay={70} className="h-full">
                  <FundTable
                    caption="Компенсационный фонд обеспечения договорных обязательств"
                    rows={detail.funds.contract.rows}
                    law={detail.funds.contract.law}
                  />
                </Reveal>
              </div>
              <Reveal className="mt-6 rounded-2xl border border-neutral-200 bg-neutral-50 p-5 text-sm leading-relaxed text-neutral-700 sm:p-6">
                <strong className="font-semibold text-neutral-950">
                  Это минимумы, установленные законом.
                </strong>{' '}
                Меньше СРО брать не вправе, но своими внутренними документами может установить
                больше. Кроме взносов в фонды у каждой СРО есть вступительный и членские взносы —
                их размер она определяет сама. Точные суммы по конкретной организации назову
                после того, как мы определимся, куда вступаем.
                <Law>{LAW.funds}</Law>
              </Reveal>
            </Section>

            {/* Требования к специалистам и срок — общие для всех трёх видов. */}
            <Section size="compact" className="bg-neutral-50/55">
              <div className="grid gap-5 lg:grid-cols-2">
                <Reveal className="h-full">
                  <div className="h-full rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6">
                    <h3 className="font-semibold text-neutral-950">Специалисты в НРС</h3>
                    <p className="mt-2.5 text-sm leading-relaxed text-neutral-600">
                      Для членства нужны не менее двух специалистов, включённых в национальный
                      реестр специалистов, по месту основной работы. Это одно из ключевых
                      требований, и чаще всего именно оно тормозит вступление.
                    </p>
                    <Law>{LAW.specialists}</Law>
                  </div>
                </Reveal>
                <Reveal delay={70} className="h-full">
                  <div className="h-full rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6">
                    <h3 className="font-semibold text-neutral-950">Срок рассмотрения заявления</h3>
                    <p className="mt-2.5 text-sm leading-relaxed text-neutral-600">
                      Закон даёт саморегулируемой организации не более двух месяцев на
                      рассмотрение заявления о приёме. На практике решение принимают быстрее,
                      но обещать конкретный срок за СРО я не могу — это её часть работы.
                    </p>
                    <Law>{LAW.term}</Law>
                  </div>
                </Reveal>
                {detail.regional && (
                  <Reveal delay={140} className="h-full lg:col-span-2">
                    <div className="h-full rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6">
                      <h3 className="font-semibold text-neutral-950">Региональный принцип</h3>
                      <p className="mt-2.5 text-sm leading-relaxed text-neutral-600">
                        Строительная компания или предприниматель вступает только в ту СРО,
                        которая зарегистрирована в том же субъекте Российской Федерации, где
                        зарегистрирована сама компания. На проектировщиков и изыскателей это
                        правило не распространяется — они выбирают СРО в любом регионе.
                      </p>
                      <Law>{LAW.membership}</Law>
                    </div>
                  </Reveal>
                )}
              </div>
            </Section>

            {/* Закрывающий призыв: возвращает на главную, в квиз, с уже
                выбранным видом СРО — человек не отвечает второй раз на то,
                что выбрал кликом по карточке. */}
            <Section size="key" className="bg-accent-950">
              <Reveal className="mx-auto max-w-3xl text-center">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent-300">
                  Заявка
                </p>
                <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">
                  Разберём вашу ситуацию
                </h2>
                <p className="mt-4 text-lg text-neutral-300">
                  {/* Название вида подставляем как есть: toLowerCase() превращал
                      аббревиатуру в «сро строителей». */}
                  Отвечу на вопросы по {detail.card.title}, подберу организацию и назову
                  порядок действий. Консультация бесплатная.
                </p>
                <div className="mt-8 flex flex-wrap justify-center gap-3">
                  <ButtonLink href={quizWithType(detail.slug)} variant="inverse" size="lg">
                    Оставить заявку
                    <ArrowRight className="h-4 w-4 shrink-0" aria-hidden="true" />
                  </ButtonLink>
                  <ButtonLink href={home()} variant="outlineInverse" size="lg">
                    На главную
                  </ButtonLink>
                </div>
              </Reveal>
            </Section>
          </main>
          <Footer />
          <div
            className="md:hidden"
            style={{ height: 'calc(4rem + env(safe-area-inset-bottom))' }}
            aria-hidden="true"
          />
          <MobileBar />
        </div>
      </div>
    </LegalProvider>
  )
}

import { ArrowLeft, ArrowRight, Check, FileText, Scale } from 'lucide-react'
import type { SroDetail } from '../content/sroDetails'
import {
  DOCS_LAW,
  DOCS_SPECIALISTS,
  DOCS_SRO,
  FUNDS_CONFIRMED,
  LAW,
  STEPS,
} from '../content/sroDetails'
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

// Шаг порядка вступления. Номер крупный и приглушённый, чтобы лента шагов
// читалась лентой, а не списком; исполнитель помечен отдельно — половину шагов
// делает не кандидат, и это стоит видеть сразу.
function Step({
  index,
  step,
}: {
  index: number
  step: { title: string; detail: string; law?: string; who: 'кандидат' | 'СРО' | 'мы' }
}) {
  // Сам <li> живёт в разметке ленты, а не здесь: вложенный <li> внутри <li>
  // — недопустимая вложенность, React ругается предупреждением в консоль,
  // и проверка «страница без ошибок» это ловит.
  return (
    <>
      {/* Вертикаль между номерами: без неё восемь шагов читаются восемью
          отдельными карточками, а это одна последовательность. Последний
          шаг линию не тянет — тянуть её некуда. */}
      <span
        aria-hidden="true"
        className="absolute left-[19px] top-11 h-[calc(100%-2.75rem)] w-px bg-neutral-200 group-last:hidden"
      />
      <span className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-accent-100 bg-accent-50 text-sm font-bold text-accent-700">
        {index + 1}
      </span>
      <div className="min-w-0 pt-1.5">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h3 className="font-semibold text-neutral-950">{step.title}</h3>
          <span className="rounded-md bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-600">
            {step.who === 'мы' ? 'делаю я' : step.who === 'СРО' ? 'делает СРО' : 'от вас'}
          </span>
        </div>
        <p className="mt-2 text-sm leading-relaxed text-neutral-600">{step.detail}</p>
        {step.law && <Law>{step.law}</Law>}
      </div>
    </>
  )
}

// Группа документов. Разделение на «требует закон» и «просит СРО» — не
// украшение: у посредников эти списки слиты в один, и человек считает, что
// договор аренды офиса требует кодекс. Он его не требует.
function DocGroup({
  title,
  hint,
  items,
  tone,
}: {
  title: string
  hint: string
  items: { title: string; detail: string; law?: string }[]
  tone: 'law' | 'sro'
}) {
  return (
    <div
      className={`h-full rounded-2xl border p-5 sm:p-6 ${
        tone === 'law' ? 'border-accent-100 bg-accent-50/40' : 'border-neutral-200 bg-white shadow-card'
      }`}
    >
      <h3 className="font-semibold text-neutral-950">{title}</h3>
      <p className="mt-1.5 text-sm text-neutral-600">{hint}</p>
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li key={item.title} className="flex gap-3">
            <FileText className="mt-0.5 h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
            <div className="min-w-0 text-sm">
              <span className="font-medium text-neutral-900">{item.title}</span>
              {item.detail && (
                <span className="block leading-relaxed text-neutral-600">{item.detail}</span>
              )}
              {item.law && <Law>{item.law}</Law>}
            </div>
          </li>
        ))}
      </ul>
    </div>
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

            {/* ШАГИ. Лента порядка вступления — то, ради чего человек и открыл
                страницу: он хочет понять, что будет происходить и что от него
                потребуется. У каждого шага помечен исполнитель: половину делает
                не кандидат, и это стоит видеть сразу. */}
            <Section>
              <Reveal>
                <h2 className="text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl">
                  Как проходит вступление
                </h2>
                <p className="mt-3 max-w-3xl text-neutral-600">
                  Порядок установлен законом и одинаков для всех трёх видов СРО. Сроки ниже —
                  только те, что установлены законом: обещать за организацию, что она уложится
                  быстрее, я не могу.
                </p>
              </Reveal>
              <Reveal className="mt-8">
                <ol className="mx-auto max-w-3xl">
                  {STEPS.map((step, index) => (
                    <li
                      key={step.title}
                      className="group relative flex list-none gap-5 pb-8 last:pb-0"
                    >
                      <Step index={index} step={step} />
                    </li>
                  ))}
                </ol>
              </Reveal>
            </Section>

            {/* ДОКУМЕНТЫ. Два списка, а не один: у посредников они слиты, и
                человек уверен, что договор аренды офиса требует кодекс. */}
            <Section size="compact" className="bg-neutral-50/55">
              <Reveal>
                <h2 className="text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl">
                  Какие документы понадобятся
                </h2>
                <p className="mt-3 max-w-3xl text-neutral-600">
                  Перечень в законе выглядит закрытым, но содержит отсылочный пункт — документы
                  о соответствии внутренним требованиям самой организации. Через него реальный
                  пакет всегда шире законного, поэтому списка ровно два и смешивать их нельзя.
                </p>
              </Reveal>
              <div className="mt-8 grid gap-5 lg:grid-cols-2">
                <Reveal className="h-full">
                  <DocGroup
                    tone="law"
                    title="Требует закон"
                    hint="Одинаково для любой СРО."
                    items={DOCS_LAW}
                  />
                </Reveal>
                <Reveal delay={70} className="h-full">
                  <DocGroup
                    tone="law"
                    title={`Специалисты в реестре — ${detail.specialistsField}`}
                    hint="Не менее двух, по основному месту работы."
                    items={DOCS_SPECIALISTS}
                  />
                </Reveal>
                <Reveal delay={140} className="h-full lg:col-span-2">
                  <DocGroup
                    tone="sro"
                    title="Что обычно просит сама СРО"
                    hint="Это НЕ требования кодекса, а внутренние документы конкретной организации: у разных СРО список разный. Точный — в её положении о членстве, и я сверяю его до подачи."
                    items={DOCS_SRO}
                  />
                </Reveal>
              </div>
            </Section>

            {/* ВЗНОСЫ. Таблицы сумм на странице нет намеренно — см. комментарий
                у FUNDS_CONFIRMED в content/sroDetails.ts. Коротко: проверка
                разошлась в первом уровне для строителей (60 или 90 млн ₽) и в
                номерах частей ст. 55.16, а сверить с текстом закона из этой
                среды нельзя — правовые источники закрыты сетевой политикой.
                Цифра, по которой человек переводит деньги, не может стоять
                «примерно». Объяснение устройства фондов при этом остаётся: оно
                верно независимо от конкретных сумм. */}
            <Section>
              <Reveal>
                <h2 className="text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl">
                  Взносы в компенсационные фонды
                </h2>
              </Reveal>
              <div className="mt-8 grid gap-5 lg:grid-cols-2">
                <Reveal className="h-full">
                  <div className="h-full rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6">
                    <h3 className="font-semibold text-neutral-950">Фонд возмещения вреда</h3>
                    <p className="mt-2.5 text-sm leading-relaxed text-neutral-600">
                      Платят все члены СРО без исключения. Размер взноса зависит от заявленного
                      уровня ответственности — то есть от суммы обязательств по одному договору:
                      чем крупнее договоры вы планируете, тем выше уровень и взнос.
                    </p>
                    <Law>{LAW.funds}</Law>
                  </div>
                </Reveal>
                <Reveal delay={70} className="h-full">
                  <div className="h-full rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6">
                    <h3 className="font-semibold text-neutral-950">
                      Фонд обеспечения договорных обязательств
                    </h3>
                    <p className="mt-2.5 text-sm leading-relaxed text-neutral-600">
                      Платят только те, кто заявил о намерении заключать договоры с использованием
                      конкурентных способов заключения договоров. Не собираетесь участвовать
                      в закупках — этот взнос вам не нужен, и переплачивать за него не надо.
                    </p>
                    <Law>{LAW.funds}</Law>
                  </div>
                </Reveal>
              </div>
              <Reveal className="mt-6 rounded-2xl border border-neutral-200 bg-neutral-50 p-5 text-sm leading-relaxed text-neutral-700 sm:p-6">
                <strong className="font-semibold text-neutral-950">
                  Точные суммы назову под вашу ситуацию, а не таблицей.
                </strong>{' '}
                Минимальные размеры взносов установлены законом и зависят от уровня
                ответственности; сверх них у каждой организации есть свои вступительный
                и членские взносы. Уплата в рассрочку и уплата третьими лицами не допускаются,
                освободить от взноса в компенсационный фонд СРО тоже не вправе — если такое
                предлагают, это повод насторожиться.
                <Law>{LAW.funds}</Law>
              </Reveal>
              {FUNDS_CONFIRMED && (
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
              )}
            </Section>

            {/* Требования к специалистам и срок — общие для всех трёх видов. */}
            <Section size="compact" className="bg-neutral-50/55">
              <div className="grid gap-5 lg:grid-cols-2">
                <Reveal className="h-full">
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
                  <Reveal delay={70} className="h-full">
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

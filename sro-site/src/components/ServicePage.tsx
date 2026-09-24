import { ArrowRight, Check } from 'lucide-react'
import { SRO_DETAILS } from '../content/sroDetails'
import { DOCS_IP, DOCS_LAW, DOCS_OOO, DOCS_SPECIALISTS, STEPS } from '../content/sroDetails'
import type { ServiceBlock, ServicePage as ServicePageData } from '../content/services'
import { anchor, page } from '../lib/site'
import { DocGroup, Law, Step } from './DetailPage'
import { Footer } from './Footer'
import { Header } from './Header'
import { Contact } from './Contact'
import { PageHero } from './PageHero'
import { MobileBar } from './MobileBar'
import { cardHover } from './ui/card'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'

// Страница услуги. Разметка собирается из блоков (content/services.ts):
// текст, карточки, список документов, оговорка, а также три «сборных»
// блока — шаги вступления, виды СРО и документы, — которые берут данные
// оттуда же, откуда страницы видов, чтобы факты не расходились.
//
// Своей вёрстки у страницы минимум: Law, Step и DocGroup общие с
// DetailPage. Семь страниц по одному шаблону — правка идёт в одном месте.

function Blocks({ block }: { block: ServiceBlock }) {
  if (block.kind === 'text') {
    return (
      <Reveal>
        <h2 className="font-display text-[1.8rem] font-medium leading-[1.08] text-neutral-950 min-[360px]:text-[2.1rem] sm:text-[2.7rem]">
          {block.title}
        </h2>
        {block.paragraphs.map((text) => (
          <p key={text} className="mt-4 max-w-3xl leading-relaxed text-neutral-600">
            {text}
          </p>
        ))}
        {block.law && <Law>{block.law}</Law>}
      </Reveal>
    )
  }

  if (block.kind === 'note') {
    return (
      <Reveal>
        <div className="rounded-3xl border-l-2 border-accent-500 bg-neutral-100 p-7 sm:p-9">
          <h2 className="font-semibold text-neutral-950">{block.title}</h2>
          {block.paragraphs.map((text) => (
            <p key={text} className="mt-2.5 text-sm leading-relaxed text-neutral-700">
              {text}
            </p>
          ))}
          {block.law && <Law>{block.law}</Law>}
        </div>
      </Reveal>
    )
  }

  if (block.kind === 'cards') {
    return (
      <>
        <Reveal>
          <h2 className="font-display text-[1.8rem] font-medium leading-[1.08] text-neutral-950 min-[360px]:text-[2.1rem] sm:text-[2.7rem]">
            {block.title}
          </h2>
          {block.intro && <p className="mt-3 max-w-3xl text-neutral-600">{block.intro}</p>}
        </Reveal>
        <div className="mt-8 grid gap-4 sm:gap-5 lg:grid-cols-2">
          {block.items.map((item, index) => (
            <Reveal key={item.title} delay={(index % 2) * 70} className="h-full">
              {/* Карточка читается, а не кликается: подсветка есть, подъёма
                  нет — подъём обещал бы клик (см. ui/card.ts). */}
              <div className="h-full rounded-2xl border border-neutral-200 bg-white p-5 transition-colors duration-200 hover:border-accent-300 sm:p-6">
                <div className="flex gap-3.5">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-accent-50 text-accent-600">
                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-neutral-950">{item.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-neutral-600">{item.text}</p>
                    {item.law && <Law>{item.law}</Law>}
                  </div>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </>
    )
  }

  if (block.kind === 'list') {
    return (
      <>
        <Reveal>
          <h2 className="font-display text-[1.8rem] font-medium leading-[1.08] text-neutral-950 min-[360px]:text-[2.1rem] sm:text-[2.7rem]">
            {block.title}
          </h2>
          {block.intro && <p className="mt-3 max-w-3xl text-neutral-600">{block.intro}</p>}
        </Reveal>
        <Reveal className="mt-8">
          <DocGroup title="" hint="" items={block.items} tone="sro" />
        </Reveal>
      </>
    )
  }

  if (block.kind === 'steps') {
    return (
      <>
        <Reveal>
          <h2 className="font-display text-[1.8rem] font-medium leading-[1.08] text-neutral-950 min-[360px]:text-[2.1rem] sm:text-[2.7rem]">
            {block.title}
          </h2>
          <p className="mt-3 max-w-3xl text-neutral-600">{block.intro}</p>
        </Reveal>
        <Reveal className="mt-8">
          <ol className="mx-auto max-w-3xl">
            {STEPS.map((step, index) => (
              <li key={step.title} className="group relative flex gap-5 pb-8 last:pb-0">
                <Step index={index} step={step} />
              </li>
            ))}
          </ol>
        </Reveal>
      </>
    )
  }

  if (block.kind === 'docs') {
    return (
      <>
        <Reveal>
          <h2 className="font-display text-[1.8rem] font-medium leading-[1.08] text-neutral-950 min-[360px]:text-[2.1rem] sm:text-[2.7rem]">
            {block.title}
          </h2>
          <p className="mt-3 max-w-3xl text-neutral-600">{block.intro}</p>
        </Reveal>
        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          <Reveal className="h-full">
            <DocGroup
              title="Требует закон"
              hint="Перечень из Градостроительного кодекса — он одинаков для всех СРО."
              items={DOCS_LAW}
              tone="law"
            />
          </Reveal>
          <Reveal delay={70} className="h-full">
            <DocGroup
              title="Документы специалистов"
              hint="На каждого из двух специалистов, включённых в национальный реестр."
              items={DOCS_SPECIALISTS}
              tone="law"
            />
          </Reveal>
          <Reveal className="h-full">
            <DocGroup
              title="Запрашивает СРО: ООО"
              hint="Список от организации, с которой я работаю. У другой СРО он может отличаться."
              items={DOCS_OOO}
              tone="sro"
            />
          </Reveal>
          <Reveal delay={70} className="h-full">
            <DocGroup
              title="Запрашивает СРО: ИП"
              hint="Список той же организации для индивидуального предпринимателя."
              items={DOCS_IP}
              tone="sro"
            />
          </Reveal>
        </div>
      </>
    )
  }

  // types
  return (
    <>
      <Reveal>
        <h2 className="font-display text-[1.8rem] font-medium leading-[1.08] text-neutral-950 min-[360px]:text-[2.1rem] sm:text-[2.7rem]">
          {block.title}
        </h2>
        <p className="mt-3 max-w-3xl text-neutral-600">{block.intro}</p>
      </Reveal>
      <div className="mt-8 grid gap-4 sm:gap-5 lg:grid-cols-3">
        {SRO_DETAILS.map((detail, index) => (
          <Reveal key={detail.slug} delay={(index % 3) * 70} className="h-full">
            <a
              href={page(detail.path)}
              className={`group/card flex h-full flex-col rounded-3xl border border-neutral-200 bg-neutral-50 p-6 sm:p-7 ${cardHover}`}
            >
              <h3 className="font-semibold text-neutral-950">{detail.card.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-neutral-600">{detail.card.text}</p>
              <span className="mt-auto inline-flex items-center gap-1.5 pt-4 text-sm font-semibold text-accent-700">
                Подробнее
                <ArrowRight
                  className="h-4 w-4 shrink-0 transition-transform duration-200 group-hover/card:translate-x-1"
                  aria-hidden="true"
                />
              </span>
            </a>
          </Reveal>
        ))}
      </div>
    </>
  )
}

export function ServicePage({ service }: { service: ServicePageData }) {
  return (
    <div id="top">
          <Header />
          <main>
            {/* Первый экран: крошка к услугам на главной, заголовок, строка. */}
            <PageHero
              backHref={anchor('#services')}
              backLabel="Все услуги"
              title={service.title}
              lead={service.lead}
            />

            {/* Блоки чередуют фон, чтобы длинная страница читалась разделами,
                а не одним полотном. */}
            {service.blocks.map((block, index) => (
              <Section
                key={block.title}
                size={block.kind === 'note' ? 'compact' : 'default'}
                className={index % 2 === 1 ? 'bg-neutral-100' : undefined}
              >
                <Blocks block={block} />
              </Section>
            ))}

            <Contact
              lead={`Отвечу на вопросы по теме «${service.short}», разберу вашу ситуацию и назову порядок действий. Консультация бесплатная — и первая, и все следующие.`}
            />
          </main>
          <Footer />
          <div
            className="md:hidden"
            style={{ height: 'calc(4rem + env(safe-area-inset-bottom))' }}
            aria-hidden="true"
          />
          <MobileBar />
    </div>
  )
}

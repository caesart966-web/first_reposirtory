import { DOCS_LAW, DOCS_SPECIALISTS, LAW } from '../content/sroDetails'
import type { ServiceBlock, ServicePage as ServicePageData } from '../content/services'
import { anchor } from '../lib/site'
import { nbsp } from '../lib/typo'
import { Footer } from './Footer'
import { Header } from './Header'
import { Contact } from './Contact'
import { PageExtras } from './PageExtras'
import { PageHero } from './PageHero'
import { MobileBar } from './MobileBar'
import { DocColumn, DocRow, H2, Head, Law, Part, SroDocs, StepsGrid, TypeRows } from './PageParts'
import { Reveal } from './ui/Reveal'

// Страница услуги. Разметка собирается из блоков (content/services.ts):
// текст, пункты, список документов, оговорка, а также три «сборных»
// блока — шаги вступления, виды СРО и документы, — которые берут данные
// оттуда же, откуда страницы видов, чтобы факты не расходились.
//
// С 28.09.2026 страницы услуг собраны из тех же частей, что страницы видов
// (PageParts.tsx): заказчик прислал снимок «Подготовки документов» с четырьмя
// рамками документов и лентой шагов и попросил привести к виду страниц СРО.
// Рамок и галочек в квадратиках больше нет — линейки, номера только там,
// где есть порядок (ordered у пунктов), норма — сноской.

// Текстовый раздел: заголовок слева, абзацы справа. Абзацы не растягиваются
// на всю ширину — строка в 1100 px читается хуже, чем в 650.
function TextBlock({ block }: { block: Extract<ServiceBlock, { kind: 'text' }> }) {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
      <Reveal>
        <h2 className={H2}>{nbsp(block.title)}</h2>
      </Reveal>
      <Reveal delay={80} className="lg:pt-2">
        {block.paragraphs.map((text) => (
          <p key={text} className="mb-4 text-[17px] leading-relaxed text-neutral-700 last:mb-0">
            {nbsp(text)}
          </p>
        ))}
        {block.law && <Law>{block.law}</Law>}
      </Reveal>
    </div>
  )
}

function Blocks({ block }: { block: ServiceBlock }) {
  if (block.kind === 'text') return <TextBlock block={block} />

  if (block.kind === 'note') {
    return (
      <Reveal className="max-w-3xl border-l-2 border-accent-400 pl-6 sm:pl-8">
        <h2 className="text-xl font-semibold leading-snug text-neutral-950">{nbsp(block.title)}</h2>
        {block.paragraphs.map((text) => (
          <p key={text} className="mt-2.5 text-[15px] leading-relaxed text-neutral-700">
            {nbsp(text)}
          </p>
        ))}
        {block.law && <Law>{block.law}</Law>}
      </Reveal>
    )
  }

  if (block.kind === 'cards') {
    // Три пункта — в три колонки, четыре — два на два: так сетка без хвоста.
    return (
      <>
        <Head title={block.title} lead={block.intro} />
        <ol
          className={`mt-10 grid border-t border-neutral-300 sm:grid-cols-2 sm:gap-x-10 ${
            block.items.length === 3 ? 'lg:grid-cols-3' : ''
          }`}
        >
          {block.items.map((item, index) => (
            <li key={item.title} className="border-b border-neutral-300 py-6">
              <Reveal delay={(index % 3) * 60}>
                {block.ordered && (
                  <span className="mb-4 block font-display text-[2rem] font-medium leading-none tabular-nums text-accent-500">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                )}
                <h3 className="text-[17px] font-semibold leading-snug text-neutral-950">{nbsp(item.title)}</h3>
                <p className="mt-1.5 text-[15px] leading-relaxed text-neutral-600">{nbsp(item.text)}</p>
                {item.law && <Law>{item.law}</Law>}
              </Reveal>
            </li>
          ))}
        </ol>
      </>
    )
  }

  if (block.kind === 'list') {
    return (
      <>
        <Head title={block.title} lead={block.intro} />
        <Reveal>
          <ul className="mt-10 grid border-t border-neutral-300 sm:grid-cols-2 sm:gap-x-10">
            {block.items.map((item) => (
              <DocRow key={item.title} item={item} icon="check" details />
            ))}
          </ul>
        </Reveal>
      </>
    )
  }

  if (block.kind === 'steps') {
    return (
      <>
        <Head title={block.title} lead={block.intro} />
        <StepsGrid />
      </>
    )
  }

  if (block.kind === 'docs') {
    // Страница «Подготовка документов» — опись с пояснениями: на неё ведёт
    // ссылка «Что входит в каждый документ» со страниц видов СРО.
    return (
      <>
        <Head title={block.title} lead={block.intro} />
        <Reveal className="mt-10 grid gap-10 md:grid-cols-2 lg:gap-12">
          <DocColumn title="Требует закон" hint="Одинаково для любой СРО." items={DOCS_LAW} law={LAW.membership} details />
          <DocColumn
            title="Специалисты в НРС"
            hint="На каждого из двух специалистов, по основному месту работы."
            items={DOCS_SPECIALISTS}
            law={LAW.specialists}
            details
          />
        </Reveal>
        <Reveal className="mt-14">
          <SroDocs details wide />
        </Reveal>
      </>
    )
  }

  // types
  return (
    <>
      <Head title={block.title} lead={block.intro} />
      <Reveal>
        <TypeRows />
      </Reveal>
    </>
  )
}

// Якорь раздела: «razdel-2». По нему ведёт строка «На этой странице»
// в шапке. Оговорки (note) в оглавление не идут — это вставки, а не разделы.
const blockId = (index: number) => `razdel-${index + 1}`

export function ServicePage({ service }: { service: ServicePageData }) {
  const toc = [
    ...service.blocks.flatMap((block, index) =>
      block.kind === 'note' ? [] : [{ id: blockId(index), title: block.title }],
    ),
    { id: 'stoimost', title: 'Сколько стоит' },
  ]
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
          image={service.image}
          toc={toc}
        />

        {/* Разделы чередуют фон, чтобы длинная страница читалась частями,
            а не одним полотном. */}
        {service.blocks.map((block, index) => (
          <Part key={block.title} id={blockId(index)} tint={index % 2 === 1} compact={block.kind === 'note'}>
            <Blocks block={block} />
          </Part>
        ))}

        {/* Фон — противоположный последнему блоку: они чередуются, и два
            соседних раздела одного цвета слились бы в один. */}
        <PageExtras related={service.related} muted={service.blocks.length % 2 === 1} />

        <Contact
          lead={`Отвечу на вопросы по теме «${service.short}», разберу вашу ситуацию и назову порядок действий. Консультация бесплатная — и первая, и все следующие.`}
        />
      </main>
      <Footer />
      <div className="md:hidden" style={{ height: 'calc(4rem + env(safe-area-inset-bottom))' }} aria-hidden="true" />
      <MobileBar />
    </div>
  )
}

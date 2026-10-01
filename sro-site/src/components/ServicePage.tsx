import { Check } from 'lucide-react'
import type { ServiceBlock, ServicePage as ServicePageData } from '../content/services'
import { anchor } from '../lib/site'
import { nbsp } from '../lib/typo'
import { Footer } from './Footer'
import { Header } from './Header'
import { Contact } from './Contact'
import { PageExtras } from './PageExtras'
import { PageHero } from './PageHero'
import { MobileBar } from './MobileBar'
import { DocInventory, DocRow, H2, Head, Law, Part, StepsGrid, TypeRows } from './PageParts'
import { Reveal } from './ui/Reveal'

// Страница услуги. Разметка собирается из блоков (content/services.ts):
// таблица «что — как», главная фраза, пункты, шкала, список дел,
// список документов, оговорка, а также три «сборных»
// блока — шаги вступления, виды СРО и документы, — которые берут данные
// оттуда же, откуда страницы видов, чтобы факты не расходились.
//
// С 28.09.2026 страницы услуг собраны из тех же частей, что страницы видов
// (PageParts.tsx): заказчик прислал снимок «Подготовки документов» с четырьмя
// рамками документов и лентой шагов и попросил привести к виду страниц СРО.
// Рамок и галочек в квадратиках больше нет — линейки, номера только там,
// где есть порядок (ordered у пунктов), норма — сноской.
// 29.09.2026 ушли и сплошные абзацы: «красиво расположить информацию,
// как у Apple, но не как у нейросети». Каждый раздел — в своей форме
// (см. ServiceBlock в content/services.ts).

type Of<K extends ServiceBlock['kind']> = Extract<ServiceBlock, { kind: K }>

// Таблица «что — как»: подпись слева, суть справа, как характеристики
// в спецификации. Для перечней, где у каждой строки своё название.
function RowsBlock({ block }: { block: Of<'rows'> }) {
  return (
    <>
      <Head title={block.title} lead={block.intro} />
      <Reveal>
        <dl className="mt-10 border-t border-neutral-300">
          {block.items.map((item) => (
            <div
              key={item.label}
              className="grid gap-1.5 border-b border-neutral-200 py-5 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)] sm:gap-10 lg:grid-cols-[minmax(0,19rem)_minmax(0,1fr)]"
            >
              <dt className="text-[17px] font-semibold leading-snug text-neutral-950">{nbsp(item.label)}</dt>
              <dd className="text-base leading-relaxed text-neutral-700">
                {nbsp(item.text)}
                {item.law && <Law>{item.law}</Law>}
              </dd>
            </div>
          ))}
        </dl>
        {block.law && <Law>{block.law}</Law>}
      </Reveal>
    </>
  )
}

// Главная фраза раздела крупно, с латунной чертой, как цитата нормы
// в «Специалистах НРС» на главной; под ней — пояснение и статья.
function StatementBlock({ block }: { block: Of<'statement'> }) {
  return (
    <>
      <Head title={block.title} />
      <Reveal className="mt-10 border-l-2 border-accent-400 pl-6 sm:pl-10">
        <p className="max-w-4xl font-display text-[1.55rem] font-medium leading-snug text-balance text-neutral-950 sm:text-[2rem] lg:text-[2.3rem]">
          {nbsp(block.quote)}
        </p>
        {block.text && <p className="mt-5 max-w-3xl text-[17px] leading-relaxed text-neutral-600">{nbsp(block.text)}</p>}
        {block.law && <Law>{block.law}</Law>}
      </Reveal>
    </>
  )
}

// Шкала по нарастающей: точки на одной линии, от светлой латуни к графиту —
// чем строже мера, тем темнее. Без номеров: это не шаги, которые проходят
// по очереди, а ступени строгости.
const SHADES = ['bg-accent-300', 'bg-accent-500', 'bg-accent-700', 'bg-accent-950']

function ScaleBlock({ block }: { block: Of<'scale'> }) {
  return (
    <>
      <Head title={block.title} lead={block.intro} />
      <Reveal>
        <ol className="relative mt-12 grid gap-8 sm:grid-cols-4 sm:gap-6">
          <span
            aria-hidden="true"
            className="absolute bottom-2 left-[7px] top-2 w-px bg-neutral-300 sm:bottom-auto sm:left-0 sm:right-0 sm:top-[7px] sm:h-px sm:w-auto"
          />
          {block.items.map((item, index) => (
            <li key={item} className="relative pl-9 sm:pl-0 sm:pt-10">
              <span
                aria-hidden="true"
                className={`absolute left-0 top-1 h-[15px] w-[15px] rounded-full sm:top-0 ${SHADES[Math.min(index, SHADES.length - 1)]}`}
              />
              <span className="block text-[17px] font-semibold leading-snug text-neutral-950">{nbsp(item)}</span>
            </li>
          ))}
        </ol>
        {block.note && (
          <p className="mt-10 max-w-3xl border-l-2 border-accent-400 pl-5 text-[15px] leading-relaxed text-neutral-700">
            {nbsp(block.note)}
          </p>
        )}
        {block.law && <Law>{block.law}</Law>}
      </Reveal>
    </>
  )
}

// «Что делаю я» — списком дел, а не абзацем через запятую. У вступления
// рядом «От вас»: так сразу видно, что остаётся на стороне клиента.
function ActionList({ items, muted = false }: { items: string[]; muted?: boolean }) {
  return (
    <ul className="border-t border-neutral-300">
      {items.map((item) => (
        <li key={item} className="flex gap-3 border-b border-neutral-200 py-3.5 text-[17px] leading-snug text-neutral-900">
          <Check className={`mt-1 h-4 w-4 shrink-0 ${muted ? 'text-neutral-400' : 'text-accent-500'}`} aria-hidden="true" />
          <span className="min-w-0">{nbsp(item)}</span>
        </li>
      ))}
    </ul>
  )
}

function ActionsBlock({ block }: { block: Of<'actions'> }) {
  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
      <Reveal>
        <h2 className={H2}>{nbsp(block.title)}</h2>
      </Reveal>
      <Reveal delay={80}>
        <ActionList items={block.mine} />
        {/* Что остаётся на человеке — под списком, строкой с подписью, а не
            второй колонкой «Делаю я / От вас»: подпись «Делаю я» под
            заголовком «Что делаю я» повторяла его слово в слово. */}
        {block.yours && (
          <div className="mt-8 grid gap-3 sm:grid-cols-[7rem_minmax(0,1fr)] sm:gap-6">
            <h3 className="pt-3.5 text-[15px] font-semibold text-neutral-950">От вас</h3>
            <ActionList items={block.yours} muted />
          </div>
        )}
      </Reveal>
    </div>
  )
}

function Blocks({ block }: { block: ServiceBlock }) {
  if (block.kind === 'rows') return <RowsBlock block={block} />
  if (block.kind === 'statement') return <StatementBlock block={block} />
  if (block.kind === 'scale') return <ScaleBlock block={block} />
  if (block.kind === 'actions') return <ActionsBlock block={block} />

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
    // Четыре этапа — в один ряд: порядок читается слева направо, как лента.
    const wide =
      block.items.length === 3 ? 'lg:grid-cols-3' : block.ordered && block.items.length === 4 ? 'lg:grid-cols-4' : ''
    return (
      <>
        <Head title={block.title} lead={block.intro} />
        <ol className={`mt-10 grid border-t border-neutral-300 sm:grid-cols-2 sm:gap-x-10 ${wide}`}>
          {block.items.map((item, index) => (
            <li key={item.title} className="border-b border-neutral-300 py-6">
              {/* Номер — только у этапов; у простого перечня вместо него
                  короткая латунная черта: пункт отмечен, но не пронумерован.
                  На телефоне номер слева от текста, как в шагах вступления
                  (StepsGrid): отдельной строкой над заголовком он добавлял
                  к каждому этапу по строке. */}
              <Reveal
                delay={(index % 3) * 60}
                className={block.ordered ? 'grid grid-cols-[3rem_minmax(0,1fr)] sm:block' : ''}
              >
                {block.ordered ? (
                  <span className="block font-display text-[1.75rem] font-medium leading-none tabular-nums text-accent-500 sm:mb-4 sm:text-[2rem]">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                ) : (
                  <span className="mb-5 block h-0.5 w-8 bg-accent-400" aria-hidden="true" />
                )}
                <div>
                  <h3 className="text-[17px] font-semibold leading-snug text-neutral-950">{nbsp(item.title)}</h3>
                  <p className="mt-1.5 text-[15px] leading-relaxed text-neutral-600">{nbsp(item.text)}</p>
                  {item.law && <Law>{item.law}</Law>}
                </div>
              </Reveal>
            </li>
          ))}
        </ol>
        {block.aside && (
          <Reveal className="mt-8 max-w-3xl border-l-2 border-accent-400 pl-5">
            <p className="text-[15px] leading-relaxed text-neutral-700">{nbsp(block.aside.text)}</p>
            {block.aside.law && <Law>{block.aside.law}</Law>}
          </Reveal>
        )}
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
        <DocInventory />
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
// «Что делаю я» (actions) и «Сколько стоит» — тоже нет (01.10.2026): они
// есть на каждой странице и в оглавлении ничего не сообщали, а на телефоне
// удлиняли его.
const blockId = (index: number) => `razdel-${index + 1}`

export function ServicePage({ service }: { service: ServicePageData }) {
  const toc = service.blocks.flatMap((block, index) =>
    block.kind === 'note' || block.kind === 'actions' ? [] : [{ id: blockId(index), title: block.title }],
  )
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
          lead={`Отвечу на вопросы по теме «${service.short}», разберу вашу ситуацию и назову порядок действий.`}
        />
      </main>
      <Footer />
      <MobileBar />
    </div>
  )
}

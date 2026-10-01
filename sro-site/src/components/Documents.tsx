import { IMAGES } from '../content/images'
import { asset, page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { PageLink } from './PageParts'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { SectionHeading } from './ui/Section'

// Опись на главной — только названия (01.10.2026): пояснения к каждому
// документу и подготовка по шагам — на странице «Подготовка документов»,
// куда ведёт строка под описью. С пояснениями раздел занимал полтора
// экрана компьютера и повторял ту страницу.
const DOCUMENTS = [
  'Заявление',
  'Регистрационные документы',
  'Документы организации',
  'Документы специалистов',
  'Документы НРС',
  'Сведения о квалификации',
  'Дополнительные документы',
]
const DOCS_PAGE = 'uslugi/dokumenty'

// Раздел стоит на фотографии папок во всю высоту (с 25.09.2026, выбор
// заказчика из двух макетов): на компьютере кадр слева, от края до края
// раздела, и растворяется к тексту; на телефоне и планшете — сверху и
// растворяется книзу. Это зеркало раздела «Как проходит работа» выше:
// там Фемида справа на графите, здесь папки слева на листе. Маски — в
// index.css (.docs-photo). Контраст подписей над растворённым краем
// меряет scripts/test-hero-contrast.mjs.
export function Documents() {
  return (
    <section
      id="documents"
      className="relative isolate overflow-hidden pb-20 pt-[22rem] sm:pb-28 sm:pt-[28rem] lg:pt-28"
    >
      <picture>
        {IMAGES.documents.srcAvif && <source type="image/avif" srcSet={asset(IMAGES.documents.srcAvif)} />}
        <img
          src={asset(IMAGES.documents.src)}
          alt=""
          aria-hidden="true"
          width={IMAGES.documents.width}
          height={IMAGES.documents.height}
          loading="lazy"
          decoding="async"
          className="docs-photo scroll-settle pointer-events-none absolute inset-x-0 top-0 -z-10 h-[24rem] w-full select-none object-cover object-[50%_30%] sm:h-[30rem] sm:object-[50%_40%] lg:inset-x-auto lg:left-0 lg:h-full lg:w-[42%] lg:object-[0%_50%] [@media(min-width:1440px)_and_(min-aspect-ratio:5/2)]:left-[max(0px,calc(50%-56.25rem))] [@media(min-width:1440px)_and_(min-aspect-ratio:5/2)]:w-[47.5rem]"
        />
      </picture>
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="lg:ml-[44%]">
          <SectionHeading title="Подготовлю пакет документов для вступления в СРО" />
          <Reveal delay={120}>
            <p className="mt-7 text-lg leading-relaxed text-neutral-600">
              {nbsp(
                'Соберу комплект под требования выбранной СРО и проверю каждый документ до подачи.',
              )}
            </p>
            <ButtonLink href="#contacts" size="lg" arrow className="mt-9">
              Проверить мои документы
            </ButtonLink>
          </Reveal>
          {/* Перечень — строками с тонкими линейками, как опись в деле, а не
              галочками в карточке: галочки означают «сделано», а это список
              того, что войдёт в пакет. С 1024 px — в две колонки, номера
              идут сверху вниз по колонке (grid-flow-col).
              Строка подсвечивается (.doc-row в index.css), но это не ссылка:
              на компьютере — при наведении, на телефоне — когда проходит
              середину экрана, ведь наведения там нет. */}
          <Reveal>
            <p className="mt-14 text-sm text-neutral-600">Что войдёт в пакет</p>
          </Reveal>
          <ol className="mt-5 grid border-t border-neutral-300 lg:grid-flow-col lg:grid-rows-4 lg:gap-x-10">
            {DOCUMENTS.map((title, index) => (
              <li key={title} className="doc-row border-b border-neutral-300">
                <Reveal delay={index * 50} className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-2 py-4">
                  <span className="doc-num pt-0.5 text-sm tabular-nums text-neutral-500">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <p className="doc-text font-medium text-neutral-950">{title}</p>
                </Reveal>
              </li>
            ))}
          </ol>
          <Reveal>
            <PageLink
              href={page(DOCS_PAGE)}
              text="Что входит в каждый документ"
              to="Подготовка документов"
              className="border-t-0 lg:mt-12 lg:border-t"
            />
          </Reveal>
        </div>
      </div>
    </section>
  )
}

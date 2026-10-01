import { IMAGES } from '../content/images'
import { LAW } from '../content/sroDetails'
import { fadeIn } from '../lib/fade'
import { asset, page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { Law, PageLink } from './PageParts'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { SectionHeading } from './ui/Section'

// Опись на главной — название и короткая строка «что это» (01.10.2026).
// Днём по разбору дизайнера здесь оставались одни названия, и заказчик
// спросил: «что подразумевается под „Дополнительными документами“?» —
// без пояснения пункт ничего не сообщал. Пояснения — те, что стояли здесь
// до разбора, по одной строке; седьмой пункт назван по сути: это то, что
// СРО запрашивает по своим требованиям, — закон отсылает к ним в перечне
// ст. 55.6 ГрК РФ (DOCS_LAW, «Документы о соответствии требованиям СРО»).
// Подробности о каждом документе — на странице «Подготовка документов»,
// куда ведёт строка под описью.
const DOCUMENTS: { title: string; text: string; law?: string }[] = [
  { title: 'Заявление', text: 'По форме выбранной СРО' },
  { title: 'Регистрационные документы', text: 'ОГРН или ОГРНИП, ИНН, устав' },
  { title: 'Документы организации', text: 'Сведения о компании и руководителе' },
  { title: 'Документы специалистов', text: 'Дипломы, подтверждение стажа' },
  { title: 'Документы НРС', text: 'Подтверждение включения специалистов в реестр' },
  { title: 'Сведения о квалификации', text: 'Удостоверения о повышении квалификации, НОК' },
  {
    title: 'Документы по требованиям СРО',
    text: 'Свои у каждой СРО — например, договор аренды',
    law: LAW.membership,
  },
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
          ref={fadeIn}
          className="docs-photo scroll-settle pointer-events-none absolute inset-x-0 top-0 -z-10 h-[24rem] w-full select-none object-cover object-[50%_30%] sm:h-[30rem] sm:object-[50%_40%] lg:inset-x-auto lg:left-0 lg:h-full lg:w-[42%] lg:object-[0%_50%] min-[1800px]:left-[max(0px,calc(50%-56.25rem))] min-[1800px]:w-[47.5rem]"
        />
      </picture>
      <div className="mx-auto w-full max-w-6xl min-[1800px]:max-w-7xl px-4 sm:px-6 lg:px-8">
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
              идут сверху вниз по колонке (grid-flow-col). Ряды — по своему
              содержимому (auto), а не равные: с равными все строки
              вытягивались до самой высокой, седьмой, и между ними стояли
              пустоты.
              Строка подсвечивается (.doc-row в index.css), но это не ссылка:
              на компьютере — при наведении, на телефоне — когда проходит
              середину экрана, ведь наведения там нет. */}
          <Reveal>
            <p className="mt-14 text-sm text-neutral-600">Что войдёт в пакет</p>
          </Reveal>
          <ol className="mt-5 grid border-t border-neutral-300 lg:grid-flow-col lg:grid-rows-[repeat(4,auto)] lg:gap-x-10">
            {DOCUMENTS.map((doc, index) => (
              <li key={doc.title} className="doc-row border-b border-neutral-300">
                <Reveal delay={index * 50} className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-2 py-4">
                  <span className="doc-num pt-0.5 text-sm tabular-nums text-neutral-500">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <div className="doc-text">
                    <p className="font-medium text-neutral-950">{nbsp(doc.title)}</p>
                    <p className="mt-1 text-sm leading-snug text-neutral-600">{nbsp(doc.text)}</p>
                    {doc.law && <Law>{doc.law}</Law>}
                  </div>
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

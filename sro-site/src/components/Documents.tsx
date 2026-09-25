import { asset } from '../lib/site'
import { nbsp } from '../lib/typo'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { SectionHeading } from './ui/Section'

const DOCUMENTS = [
  { title: 'Заявление', text: 'по форме выбранной СРО' },
  { title: 'Регистрационные документы', text: 'ОГРН / ОГРНИП, ИНН, устав' },
  { title: 'Документы организации', text: 'сведения о компании и руководителе' },
  { title: 'Документы специалистов', text: 'дипломы, подтверждение стажа' },
  { title: 'Документы НРС', text: 'подтверждение включения специалистов в реестр' },
  { title: 'Сведения о квалификации', text: 'удостоверения о повышении квалификации, НОК' },
  { title: 'Дополнительные документы', text: 'по требованиям конкретной СРО' },
]

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
        <source type="image/avif" srcSet={asset('./img/documents-photo.avif')} />
        <img
          src={asset('./img/documents-photo.webp')}
          alt=""
          aria-hidden="true"
          width={834}
          height={1252}
          loading="lazy"
          decoding="async"
          className="docs-photo scroll-settle pointer-events-none absolute inset-x-0 top-0 -z-10 h-[24rem] w-full select-none object-cover object-[50%_30%] sm:h-[30rem] sm:object-[50%_40%] lg:inset-x-auto lg:left-0 lg:h-full lg:w-[42%] lg:object-[0%_50%]"
        />
      </picture>
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="lg:ml-[44%]">
          <SectionHeading eyebrow="Документы" title="Подготовлю пакет документов для вступления в СРО" />
          <Reveal delay={120}>
            <p className="mt-7 text-lg leading-relaxed text-neutral-600">
              {nbsp(
                'Соберу комплект под требования конкретной СРО и проверю каждый документ до подачи — чтобы снизить риск замечаний и возвратов.',
              )}
            </p>
            <ButtonLink href="#contacts" size="lg" arrow className="mt-9">
              Проверить мои документы
            </ButtonLink>
          </Reveal>
          {/* Перечень — строками с тонкими линейками, как опись в деле, а не
              галочками в карточке: галочки означают «сделано», а это список
              того, что войдёт в пакет.
              Строка подсвечивается (.doc-row в index.css), но это не ссылка:
              на компьютере — при наведении, на телефоне — когда проходит
              середину экрана, ведь наведения там нет. */}
          <Reveal>
            <p className="mt-16 text-sm text-neutral-600">Что войдёт в пакет</p>
          </Reveal>
          <ol className="mt-5 border-t border-neutral-300">
            {DOCUMENTS.map((doc, index) => (
              <li key={doc.title} className="doc-row border-b border-neutral-300">
                <Reveal delay={index * 60} className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-2 py-5">
                  <span className="doc-num pt-0.5 text-sm tabular-nums text-neutral-500">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <p className="doc-text text-neutral-950">
                    <span className="font-medium">{doc.title}</span>
                    <span className="text-neutral-600"> — {nbsp(doc.text)}</span>
                  </p>
                </Reveal>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}

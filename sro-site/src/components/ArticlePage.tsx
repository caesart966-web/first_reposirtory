import { ARTICLES_PATH, ARTICLES_SORTED, articleLaws, readingMinutes, type Article, type ArticleBlock } from '../content/articles'
import { IMAGES } from '../content/images'
import { formatDate } from '../lib/date'
import { plural } from '../lib/plural'
import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { ArticleColumns } from './Articles'
import { Contact } from './Contact'
import { Footer } from './Footer'
import { Header } from './Header'
import { MobileBar } from './MobileBar'
import { PageExtras } from './PageExtras'
import { PageHero } from './PageHero'
import { Law } from './PageParts'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'

// Страница статьи (15.10.2026).
//
// Шапка та же, что у услуг (тёмная, с кадром, оглавление пилюлями), над
// заголовком — дата и время чтения, как в обычном журнале (без «Проверено
// по закону»: заказчик 16.10.2026 попросил убрать служебные формулировки). Дальше лист для чтения:
// колонка в 44rem (около 70 знаков в строке — длиннее глаз теряет начало
// следующей), первым — короткий ответ, потом разделы. Справа на компьютере
// столбец «Нормы в статье»: все статьи закона, на которые опирается текст,
// одним списком, и кнопка «Обсудить задачу». Он липкий и едет рядом с текстом.
// На телефоне столбца нет: нормы и так стоят под каждым абзацем.
//
// Внизу — «Сколько стоит» с услугами по теме (как у страниц услуг), другие
// статьи и «Связаться».

const sectionId = (index: number) => `razdel-${index + 1}`

function Block({ block }: { block: ArticleBlock }) {
  if (block.kind === 'p') {
    return (
      <div className="mt-5">
        <p className="text-[1.0625rem] leading-[1.75] text-neutral-800">{nbsp(block.text)}</p>
        {block.law && <Law>{block.law}</Law>}
      </div>
    )
  }

  if (block.kind === 'list') {
    const Tag = block.ordered ? 'ol' : 'ul'
    return (
      <Tag className="mt-5 space-y-4">
        {block.items.map((item, index) => (
          <li key={item.text} className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-2">
            {/* Номер — только у шагов; у перечня — латунная черта, как
                в «О компании» на главной. */}
            {block.ordered ? (
              <span className="font-display text-[1.25rem] font-medium leading-[1.4] tabular-nums text-accent-600">
                {index + 1}
              </span>
            ) : (
              <span className="mt-[0.85rem] h-px w-4 bg-accent-500" aria-hidden="true" />
            )}
            <span className="min-w-0">
              <span className="block text-[1.0625rem] leading-[1.7] text-neutral-800">{nbsp(item.text)}</span>
              {item.law && <Law>{item.law}</Law>}
            </span>
          </li>
        ))}
      </Tag>
    )
  }

  if (block.kind === 'rows') {
    return (
      <dl className="mt-6 border-t border-neutral-300">
        {block.items.map((item) => (
          <div key={item.label} className="grid gap-1.5 border-b border-neutral-200 py-5 sm:grid-cols-[minmax(0,13rem)_minmax(0,1fr)] sm:gap-8">
            <dt className="text-[1.0625rem] font-semibold leading-snug text-neutral-950">{nbsp(item.label)}</dt>
            <dd className="text-base leading-relaxed text-neutral-700">
              {nbsp(item.text)}
              {item.law && <Law>{item.law}</Law>}
            </dd>
          </div>
        ))}
      </dl>
    )
  }

  // note
  return (
    <div className="mt-7 border-l-2 border-accent-400 pl-5 sm:pl-6">
      <p className="text-[1.0625rem] font-semibold leading-snug text-neutral-950">{nbsp(block.title)}</p>
      <p className="mt-2 text-base leading-relaxed text-neutral-700">{nbsp(block.text)}</p>
      {block.law && <Law>{block.law}</Law>}
    </div>
  )
}

export function ArticlePage({ article }: { article: Article }) {
  const minutes = readingMinutes(article)
  const laws = articleLaws(article)
  const others = ARTICLES_SORTED.filter((a) => a.slug !== article.slug).slice(0, 3)
  const toc = article.sections.map((section, index) => ({ id: sectionId(index), title: section.title }))

  return (
    <div id="top">
      <Header />
      <main>
        <PageHero
          backHref={page(ARTICLES_PATH)}
          backLabel="Все статьи"
          title={article.title}
          lead={article.lead}
          image={IMAGES[article.image]}
          toc={toc}
          meta={`${formatDate(article.checked)} · ${minutes} ${plural(minutes, 'минута', 'минуты', 'минут')} чтения`}
        />

        <section className="py-14 sm:py-20">
          <div className="mx-auto grid w-full max-w-6xl gap-14 px-4 sm:px-6 lg:grid-cols-[minmax(0,44rem)_minmax(0,1fr)] lg:gap-20 lg:px-8 min-[1800px]:max-w-7xl">
            <article className="min-w-0">
              {/* Ответ сразу: человек пришёл из поиска с вопросом, и ответ
                  не должен ждать третьего экрана. */}
              <Reveal className="rounded-3xl bg-neutral-100 p-6 sm:p-8">
                <p className="text-sm font-medium text-accent-700">Коротко</p>
                <p className="mt-3 font-display text-[1.15rem] font-medium leading-snug text-neutral-950 sm:text-[1.5rem]">
                  {nbsp(article.answer)}
                </p>
              </Reveal>

              {article.sections.map((section, index) => (
                <Reveal key={section.title}>
                  <section id={sectionId(index)} className="pt-12 sm:pt-14">
                    <h2 className="font-display text-[1.65rem] font-medium leading-[1.12] text-balance text-neutral-950 sm:text-[2.1rem]">
                      {nbsp(section.title)}
                    </h2>
                    {section.blocks.map((block, i) => (
                      <Block key={i} block={block} />
                    ))}
                  </section>
                </Reveal>
              ))}

              {/* Служебной строки «Нормы в статье сверены…» под текстом нет
                  (16.10.2026, заказчик: «убрать, сделать человечнее»): статья
                  кончается разделом «Что я делаю», а дата стоит над заголовком. */}
            </article>

            {/* Столбец справа — только с 1024 px. Липкий: под шапкой
                (4rem) с запасом. */}
            {laws.length > 0 && (
              <aside className="hidden lg:block" aria-label="Нормы в статье">
                <div className="sticky top-28">
                  <p className="text-sm text-neutral-600">Нормы в статье</p>
                  <ul className="mt-4 border-t border-neutral-300">
                    {laws.map((law) => (
                      <li key={law} className="border-b border-neutral-200 py-3 text-[0.9375rem] leading-snug text-neutral-800">
                        {/* Номер документа не рвётся по дефису («8828-» / «ОГ/06»):
                            хвост с «№» — неразрывным куском, как в Law. */}
                        {law.includes('№') ? (
                          <>
                            {law.slice(0, law.lastIndexOf('№'))}
                            <span className="whitespace-nowrap">{law.slice(law.lastIndexOf('№'))}</span>
                          </>
                        ) : (
                          law
                        )}
                      </li>
                    ))}
                  </ul>
                  <ButtonLink href="#contacts" arrow className="mt-8">
                    Обсудить задачу
                  </ButtonLink>
                </div>
              </aside>
            )}
          </div>
        </section>

        <PageExtras related={article.related} muted />

        {others.length > 0 && (
          <Section size="compact">
            <Reveal>
              <h2 className="font-display text-[1.8rem] font-medium leading-[1.08] text-neutral-950 min-[360px]:text-[2.1rem] sm:text-[2.7rem]">
                Другие статьи
              </h2>
            </Reveal>
            <div className="mt-10">
              <ArticleColumns articles={others} />
            </div>
          </Section>
        )}

        <Contact />
      </main>
      <Footer />
      <MobileBar />
    </div>
  )
}

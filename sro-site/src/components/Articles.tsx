import { ARTICLES_PATH, ARTICLES_SORTED, type Article } from '../content/articles'
import { formatDate } from '../lib/date'
import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { GoTo } from './ui/GoTo'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Список статей строками на линейках — тот же приём, что «Услуги по теме»
// и опись документов: без карточек с тенями. Строка — дата сверки, название
// антиквой, одна строка о сути; нажимается вся строка.
//
// Дата слева — дата последней сверки статьи (checked): читателю важно,
// насколько свежий текст, а не когда он впервые появился.
export function ArticleRows({ articles }: { articles: Article[] }) {
  return (
    <ul className="border-t border-neutral-300">
      {articles.map((article, index) => (
        <li key={article.slug} className="border-b border-neutral-300">
          <Reveal delay={(index % 3) * 70}>
            <a
              href={page(`${ARTICLES_PATH}/${article.slug}`)}
              className="group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 py-6 sm:grid-cols-[9.5rem_minmax(0,1fr)_auto] sm:items-baseline sm:gap-8 sm:py-7"
            >
              {/* На телефоне дата и название — одной колонкой, стрелка справа,
                  как в статьях на главной (22.10.2026: здесь стрелки не было);
                  с 640 px обёртка исчезает (sm:contents) и строка делится
                  на дату, название и стрелку. */}
              <span className="min-w-0 sm:contents">
              <span className="block text-sm text-neutral-600">
                {formatDate(article.checked)}
              </span>
              <span className="mt-2 block min-w-0 sm:mt-0">
                <span className="block font-display text-[1.45rem] font-medium leading-tight text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-accent-700 sm:text-[1.7rem]">
                  {nbsp(article.title)}
                </span>
                <span className="mt-2 block max-w-2xl text-[0.9375rem] leading-relaxed text-neutral-600">
                  {nbsp(article.hint)}
                </span>
              </span>
              </span>
              {/* Стрелка без кружка: кружок — только у «Связаться». */}
              <GoTo />
            </a>
          </Reveal>
        </li>
      ))}
    </ul>
  )
}

// Статьи колонками — на главной и внизу статьи («Другие статьи»). Строки
// на широком экране оставляли пустой правую половину; три колонки ложатся
// в ширину раздела, как карточки услуг (короткая латунная черта вместо
// рамки, ссылкой вся колонка).
// На телефоне (до 640 px) — короткие строки, как услуги на главной: дата,
// название и стрелка справа, без строки о сути и «Читать» (16.10.2026,
// заказчик согласился: три колонки друг под другом занимали почти полтора
// экрана на и так длинной главной). Строка о сути остаётся в разметке.
export function ArticleColumns({ articles }: { articles: Article[] }) {
  return (
    <ul className="grid border-t border-neutral-300 sm:grid-cols-2 sm:gap-x-10 lg:grid-cols-3">
      {articles.map((article, index) => (
        <li key={article.slug} className="border-b border-neutral-300">
          <Reveal delay={(index % 3) * 80} className="h-full">
            <a
              href={page(`${ARTICLES_PATH}/${article.slug}`)}
              className="group flex h-full items-center justify-between gap-5 py-5 sm:flex-col sm:items-stretch sm:justify-start sm:gap-0 sm:py-8"
            >
              <span className="min-w-0 sm:flex sm:flex-1 sm:flex-col">
                <span className="mb-5 hidden h-0.5 w-8 bg-accent-400 sm:block" aria-hidden="true" />
                <span className="block text-sm text-neutral-600">{formatDate(article.checked)}</span>
                <span className="mt-1 block font-display text-[1.3rem] font-medium leading-tight text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-accent-700 sm:mt-2 sm:text-[1.6rem]">
                  {nbsp(article.title)}
                </span>
                <span className="mt-3 hidden text-[0.9375rem] leading-relaxed text-neutral-600 sm:block">
                  {nbsp(article.hint)}
                </span>
                <GoTo className="mt-auto hidden pt-6 text-[0.9375rem] sm:inline-flex">Читать</GoTo>
              </span>
              {/* На телефоне — одна стрелка справа, как в строках услуг. */}
              <GoTo className="sm:hidden" />
            </a>
          </Reveal>
        </li>
      ))}
    </ul>
  )
}

// Раздел главной: три свежие статьи и переход ко всем. Стоит между
// «О компании» (тёмный) и «Частыми вопросами» (светлый) на кремовом фоне:
// вопросы отвечают коротко, статьи — подробно, и рядом они читаются как
// одна тема.
export const HOME_ARTICLES = 3

export function LatestArticles() {
  if (ARTICLES_SORTED.length === 0) return null
  return (
    <Section id="articles" className="bg-neutral-100">
      <SectionHeading title="Статьи" subtitle="Подробные ответы на вопросы, которые задают перед вступлением в СРО." />
      <div className="mt-12 sm:mt-16">
        <ArticleColumns articles={ARTICLES_SORTED.slice(0, HOME_ARTICLES)} />
      </div>
      <Reveal className="mt-8">
        <a href={page(ARTICLES_PATH)} className="group inline-flex min-h-11 items-center">
          <GoTo className="text-[1.0625rem]">Все статьи</GoTo>
        </a>
      </Reveal>
    </Section>
  )
}

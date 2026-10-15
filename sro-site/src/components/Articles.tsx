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
// Дата слева — дата сверки с законом (checked), а не выхода: читателю важно,
// насколько свежа норма, а не когда текст впервые появился.
export function ArticleRows({ articles }: { articles: Article[] }) {
  return (
    <ul className="border-t border-neutral-300">
      {articles.map((article, index) => (
        <li key={article.slug} className="border-b border-neutral-300">
          <Reveal delay={(index % 3) * 70}>
            <a
              href={page(`${ARTICLES_PATH}/${article.slug}`)}
              className="group grid gap-2 py-6 sm:grid-cols-[9.5rem_minmax(0,1fr)_auto] sm:items-baseline sm:gap-8 sm:py-7"
            >
              <span className="text-sm text-neutral-600">
                <span className="sr-only">Проверено </span>
                {formatDate(article.checked)}
              </span>
              <span className="min-w-0">
                <span className="block font-display text-[1.45rem] font-medium leading-tight text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-accent-700 sm:text-[1.7rem]">
                  {nbsp(article.title)}
                </span>
                <span className="mt-2 block max-w-2xl text-[0.9375rem] leading-relaxed text-neutral-600">
                  {nbsp(article.hint)}
                </span>
              </span>
              {/* Стрелка без кружка: кружок — только у «Связаться». */}
              <GoTo className="hidden sm:inline-flex" />
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
// рамки, ссылкой вся колонка). На телефоне — одна под другой.
export function ArticleColumns({ articles }: { articles: Article[] }) {
  return (
    <ul className="grid border-t border-neutral-300 sm:grid-cols-2 sm:gap-x-10 lg:grid-cols-3">
      {articles.map((article, index) => (
        <li key={article.slug} className="border-b border-neutral-300">
          <Reveal delay={(index % 3) * 80} className="h-full">
            <a href={page(`${ARTICLES_PATH}/${article.slug}`)} className="group flex h-full flex-col py-7 sm:py-8">
              <span className="block h-0.5 w-8 bg-accent-400" aria-hidden="true" />
              <span className="mt-5 text-sm text-neutral-600">
                <span className="sr-only">Проверено </span>
                {formatDate(article.checked)}
              </span>
              <span className="mt-2 block font-display text-[1.45rem] font-medium leading-tight text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-accent-700 sm:text-[1.6rem]">
                {nbsp(article.title)}
              </span>
              <span className="mt-3 block text-[0.9375rem] leading-relaxed text-neutral-600">{nbsp(article.hint)}</span>
              <GoTo className="mt-auto pt-6 text-[0.9375rem]">Читать</GoTo>
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
      <SectionHeading title="Статьи" subtitle="Вопросы о вступлении в СРО, разобранные по закону, со ссылкой на каждую норму." />
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

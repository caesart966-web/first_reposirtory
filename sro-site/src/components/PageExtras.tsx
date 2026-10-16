import { ARTICLES_PATH, articlesFor } from '../content/articles'
import { serviceBySlug } from '../content/services'
import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { GoTo } from './ui/GoTo'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'

// Последний раздел внутренних страниц перед «Связаться»: сколько стоит
// и куда идти дальше.
//
// «Сколько стоит» — первый вопрос после «что это», а на страницах услуг
// ответа не было: он жил только в «Стоимости» на главной. Здесь то же
// правило, без цифр: цен заказчик не называл, и выдумывать их нельзя
// (правило сайта). Взносы в СРО — отдельно: их платит компания, и сумму
// по выбранной организации называю до оплаты — так сказано на странице
// «Подбор и проверка СРО».
// С 01.10.2026 — две строки вместо трёх абзацев: блок стоит на всех десяти
// внутренних страницах, и на телефоне занимал полэкрана одного и того же
// текста. «От чего зависит стоимость» осталось в «Форматах работы» на главной.
//
// «Услуги по теме» — чтобы страница не кончалась тупиком. Подписи у ссылок
// те же, что в меню (hint): человек заранее видит, что за стрелкой.
const PRICE = [
  'Консультация бесплатная на любом этапе. Стоимость работы называю после короткого разговора о задаче и согласовываю письменно до начала.',
  'Взносы в СРО компания платит сама; их сумму по выбранной организации называю до оплаты.',
]

// Строка-переход: крупное название и строка о сути, стрелка справа.
// Одна на «Услуги по теме» и «Статьи по теме» — оба списка выглядят одинаково.
function LinkList({ title, items }: { title: string; items: { key: string; href: string; name: string; hint: string }[] }) {
  return (
    <>
      <p className="text-sm text-neutral-600">{title}</p>
      <ul className="mt-4 border-t border-neutral-300">
        {items.map((item) => (
          <li key={item.key} className="border-b border-neutral-300">
            <a href={item.href} className="group flex items-center justify-between gap-6 py-5">
              <span className="min-w-0">
                <span className="block font-display text-[1.45rem] font-medium leading-tight text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-accent-700">
                  {nbsp(item.name)}
                </span>
                <span className="mt-1 block text-sm leading-relaxed text-neutral-600">{nbsp(item.hint)}</span>
              </span>
              {/* Стрелка без кружка: кружок — только у «Связаться» (ui/GoTo.tsx). */}
              <GoTo />
            </a>
          </li>
        ))}
      </ul>
    </>
  )
}

// muted — фон на ступень темнее. Страница его выбирает противоположным
// предыдущему разделу: два соседних раздела одного цвета читались бы одним.
//
// place — slug страницы вида СРО или услуги (16.10.2026): под «Услугами
// по теме» встают «Статьи по теме» — статьи, у которых эта страница в `on`
// (content/articles.ts). Человек, читающий про услугу, видит разбор своего
// вопроса, а поисковик — ссылку на статью со страницы той же темы.
// У самих статей place нет: там внизу свой раздел «Другие статьи».
export function PageExtras({
  related,
  id = 'stoimost',
  muted = false,
  place,
}: {
  related: string[]
  id?: string
  muted?: boolean
  place?: string
}) {
  const services = related.map((slug) => {
    const service = serviceBySlug(slug)
    if (!service) throw new Error(`Нет страницы услуги: ${slug}`)
    return { key: service.slug, href: page(service.path), name: service.short, hint: service.hint }
  })
  const articles = (place ? articlesFor(place) : []).map((article) => ({
    key: article.slug,
    href: page(`${ARTICLES_PATH}/${article.slug}`),
    name: article.title,
    hint: article.hint,
  }))
  return (
    <Section id={id} className={muted ? 'bg-neutral-100' : undefined}>
      <div className="grid gap-14 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-20">
        <Reveal>
          <h2 className="font-display text-[1.8rem] font-medium leading-[1.08] text-neutral-950 min-[360px]:text-[2.1rem] sm:text-[2.7rem]">
            Сколько стоит
          </h2>
          <p className="mt-5 text-lg leading-relaxed text-neutral-700">{nbsp(PRICE[0])}</p>
          <p className="mt-3 leading-relaxed text-neutral-600">{nbsp(PRICE[1])}</p>
        </Reveal>
        <Reveal delay={120}>
          <LinkList title="Услуги по теме" items={services} />
          {articles.length > 0 && (
            <div className="mt-12">
              <LinkList title="Статьи по теме" items={articles} />
            </div>
          )}
        </Reveal>
      </div>
    </Section>
  )
}

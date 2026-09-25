import { ArrowUpRight } from 'lucide-react'
import { serviceBySlug } from '../content/services'
import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'

// Последний раздел внутренних страниц перед «Связаться»: сколько стоит
// и куда идти дальше.
//
// «Сколько стоит» — первый вопрос после «что это», а на страницах услуг
// ответа не было: он жил только в «Стоимости» на главной. Здесь то же
// правило теми же словами, без цифр: цен заказчик не называл, и выдумывать
// их нельзя (правило сайта). Взносы в СРО — отдельно: их платит компания,
// и сумму по выбранной организации называю до оплаты — так сказано на
// странице «Подбор и проверка СРО».
//
// «Услуги по теме» — чтобы страница не кончалась тупиком. Подписи у ссылок
// те же, что в меню (hint): человек заранее видит, что за стрелкой.
const PRICE = [
  'Консультация бесплатная — на любом этапе.',
  'Стоимость работы зависит от вида СРО и готовности документов. Называю её после короткого разговора о задаче и согласовываю письменно до начала работы.',
  'Взносы в СРО компания уплачивает сама; их точную сумму по выбранной организации называю до оплаты.',
]

// muted — фон на ступень темнее. Страница его выбирает противоположным
// предыдущему разделу: два соседних раздела одного цвета читались бы одним.
export function PageExtras({
  related,
  id = 'stoimost',
  muted = false,
}: {
  related: string[]
  id?: string
  muted?: boolean
}) {
  const items = related.map((slug) => {
    const service = serviceBySlug(slug)
    if (!service) throw new Error(`Нет страницы услуги: ${slug}`)
    return service
  })
  return (
    <Section id={id} className={muted ? 'bg-neutral-100' : undefined}>
      <div className="grid gap-14 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-20">
        <Reveal>
          <h2 className="font-display text-[1.8rem] font-medium leading-[1.08] text-neutral-950 min-[360px]:text-[2.1rem] sm:text-[2.7rem]">
            Сколько стоит
          </h2>
          <p className="mt-5 text-lg leading-relaxed text-neutral-700">{nbsp(PRICE[0])}</p>
          {PRICE.slice(1).map((text) => (
            <p key={text} className="mt-3 leading-relaxed text-neutral-600">
              {nbsp(text)}
            </p>
          ))}
        </Reveal>
        <Reveal delay={120}>
          <p className="text-sm text-neutral-600">Услуги по теме</p>
          <ul className="mt-4 border-t border-neutral-300">
            {items.map((service) => (
              <li key={service.slug} className="border-b border-neutral-300">
                <a
                  href={page(service.path)}
                  className="group flex items-center justify-between gap-6 py-5"
                >
                  <span className="min-w-0">
                    <span className="block font-display text-[1.45rem] font-medium leading-tight text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-accent-700">
                      {nbsp(service.short)}
                    </span>
                    <span className="mt-1 block text-sm leading-relaxed text-neutral-600">
                      {nbsp(service.hint)}
                    </span>
                  </span>
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-neutral-300 text-neutral-950 transition-all duration-700 ease-silk group-hover:rotate-45 group-hover:border-neutral-950 group-hover:bg-neutral-950 group-hover:text-neutral-50">
                    <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </Section>
  )
}

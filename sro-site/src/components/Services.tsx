import { ArrowUpRight } from 'lucide-react'
import { serviceBySlug } from '../content/services'
import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Услуги разбиты на две группы: что делаем с самой СРО и что — со
// специалистами и уровнем ответственности.
//
// Карточек ровно семь — по одной на страницу услуги (/uslugi/…), и берутся
// они из тех же данных, что сами страницы и меню «Услуги» (content/services.ts).
// До 25.09.2026 карточек было восемь со своими текстами, и это путало:
// «Подбор СРО» и «Проверка СРО» вели на одну и ту же страницу, названия
// карточек не совпадали с заголовками страниц, а карточка «Расширение видов
// работ» обещала «изменение состава видов работ», хотя её же страница
// объясняет, что перечни видов работ отменены в 2017 году.
//
// Под названием — подсказка из меню (hint): что человек найдёт на странице.
// Так понятно, куда ведёт стрелка, ещё до нажатия.
const GROUPS: { title: string; slugs: string[] }[] = [
  { title: 'Вступление и сопровождение', slugs: ['vstuplenie', 'podbor', 'dokumenty', 'proverki'] },
  { title: 'Специалисты и уровень ответственности', slugs: ['nrs', 'nok', 'uroven'] },
]

// Страница по ключу; неизвестный ключ — ошибка сборки данных, а не
// молчаливая ссылка в никуда.
const serviceOf = (slug: string) => {
  const service = serviceBySlug(slug)
  if (!service) throw new Error(`Нет страницы услуги: ${slug}`)
  return service
}

// Классы перечислены целиком: Tailwind собирает только то, что видит в коде.
const COLS: Record<number, string> = { 3: 'lg:grid-cols-3', 4: 'lg:grid-cols-4' }

export function Services() {
  return (
    <Section id="services" className="bg-neutral-100">
      <SectionHeading
        eyebrow="Услуги"
        title="Услуги по вступлению в СРО"
        subtitle="Отдельные задачи или полное сопровождение: от подбора саморегулируемой организации до внесения сведений в реестр членов."
      />

      <div className="mt-16 space-y-14">
        {GROUPS.map((group) => (
          <div key={group.title}>
            <Reveal>
              <h3 className="text-sm text-neutral-600">{group.title}</h3>
            </Reveal>
            {/* Карточка — лист без рамки и тени. При наведении медленно темнеет
                до графита, стрелка поворачивается — приём из ролика заказчика.
                Описание видно всегда: спрятанное до наведения, оно оставляло
                пустые карточки, а на телефоне не читалось бы вовсе. */}
            <div className={`mt-5 grid gap-3 sm:grid-cols-2 ${COLS[group.slugs.length] ?? 'lg:grid-cols-4'}`}>
              {group.slugs.map(serviceOf).map((service, index) => (
                <Reveal key={service.slug} delay={(index % 4) * 90} className="h-full">
                  <a
                    href={page(service.path)}
                    className="group relative flex h-full flex-col justify-between gap-6 sm:min-h-[13rem] sm:gap-8 rounded-3xl bg-neutral-50 p-6 transition-colors duration-700 ease-silk hover:bg-neutral-950 focus-visible:bg-neutral-950 focus-visible:outline-none sm:p-7 lg:min-h-[15rem]"
                  >
                    {/* Кружок-стрелка — внизу, рядом с подписью (с 26.09.2026).
                        Над заголовком он читался непонятным значком и оставлял
                        пустоту; рядом с заголовком не помещался: в четыре
                        колонки «Сопровождение» выталкивало его за край.
                        На 1024–1279px кегль на ступень меньше: колонка там
                        уже всего. */}
                    <div>
                      <h4 className="font-display text-[1.6rem] font-medium leading-[1.1] text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-neutral-50 group-focus-visible:text-neutral-50 lg:text-[1.45rem] xl:text-[1.6rem]">
                        {nbsp(service.short)}
                      </h4>
                    </div>
                    <div className="flex items-end justify-between gap-4">
                      <p className="text-sm leading-relaxed text-neutral-600 transition-colors duration-700 group-hover:text-neutral-300 group-focus-visible:text-neutral-300">
                        {nbsp(service.hint)}
                      </p>
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-neutral-300 text-neutral-950 transition-all duration-700 ease-silk group-hover:rotate-45 group-hover:border-neutral-50 group-hover:bg-neutral-50 group-focus-visible:border-neutral-50 group-focus-visible:bg-neutral-50">
                        <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                      </span>
                    </div>
                  </a>
                </Reveal>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

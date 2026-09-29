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

// Раскладка (29.09.2026): обе группы — в одной сетке по четыре колонки,
// чтобы карточки второго ряда были той же ширины, что и первого (раньше
// три карточки второй группы растягивались шире четырёх первой, и ряды
// не совпадали по вертикали). Четвёртое место второго ряда — бесплатная
// консультация: для того, кто не знает, какая из семи услуг его.
// Подсказка стоит сразу под названием, стрелка — внизу: раньше подсказку
// прижимало к низу рядом со стрелкой, и между ней и названием зияла пустота.
const CARD =
  'group relative flex h-full flex-col rounded-3xl p-6 transition-colors duration-700 ease-silk focus-visible:outline-none sm:min-h-[13rem] sm:p-7 lg:min-h-[14.5rem]'

// Стрелка: на компьютере — внизу справа под текстом; на телефоне — в углу
// рядом с подсказкой, чтобы карточка не росла на лишнюю строку.
function Arrow({ dark = false }: { dark?: boolean }) {
  return (
    <span className="absolute bottom-6 right-6 sm:static sm:mt-auto sm:flex sm:justify-end sm:pt-6">
      <span
        className={`flex h-11 w-11 items-center justify-center rounded-full border transition-all duration-700 ease-silk group-hover:rotate-45 ${
          dark
            ? 'border-white/30 text-neutral-50 group-hover:border-neutral-50 group-hover:bg-neutral-50 group-hover:text-neutral-950'
            : 'border-neutral-300 text-neutral-950 group-hover:border-neutral-50 group-hover:bg-neutral-50 group-focus-visible:border-neutral-50 group-focus-visible:bg-neutral-50'
        }`}
      >
        <ArrowUpRight className="h-5 w-5" aria-hidden="true" />
      </span>
    </span>
  )
}

export function Services() {
  return (
    <Section id="services" className="bg-neutral-100">
      <SectionHeading
        title="Услуги по вступлению в СРО"
        subtitle="Можно поручить одну задачу или всё вступление целиком."
      />

      <div className="mt-16 space-y-14">
        {GROUPS.map((group, groupIndex) => (
          <div key={group.title}>
            <Reveal>
              <h3 className="text-sm text-neutral-600">{group.title}</h3>
            </Reveal>
            {/* Карточка — лист без рамки и тени. При наведении медленно темнеет
                до графита, стрелка поворачивается — приём из ролика заказчика.
                Описание видно всегда: спрятанное до наведения, оно оставляло
                пустые карточки, а на телефоне не читалось бы вовсе. */}
            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {group.slugs.map(serviceOf).map((service, index) => (
                <Reveal key={service.slug} delay={(index % 4) * 90} className="h-full">
                  <a
                    href={page(service.path)}
                    className={`${CARD} bg-neutral-50 hover:bg-neutral-950 focus-visible:bg-neutral-950`}
                  >
                    {/* На 1024–1279px кегль на ступень меньше: колонка там уже
                        всего, и «Сопровождение» не помещалось в строку. */}
                    <h4 className="font-display text-[1.6rem] font-medium leading-[1.1] text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-neutral-50 group-focus-visible:text-neutral-50 lg:text-[1.45rem] xl:text-[1.6rem]">
                      {nbsp(service.short)}
                    </h4>
                    <p className="mt-3 pr-14 text-sm leading-relaxed text-neutral-600 transition-colors sm:pr-0 duration-700 group-hover:text-neutral-300 group-focus-visible:text-neutral-300">
                      {nbsp(service.hint)}
                    </p>
                    <Arrow />
                  </a>
                </Reveal>
              ))}
              {groupIndex === GROUPS.length - 1 && (
                <Reveal delay={group.slugs.length * 90} className="h-full">
                  <a
                    href="#contacts"
                    className={`${CARD} bg-accent-950 hover:bg-neutral-950 focus-visible:ring-2 focus-visible:ring-accent-400`}
                  >
                    <h4 className="font-display text-[1.6rem] font-medium leading-[1.1] text-neutral-50 lg:text-[1.45rem] xl:text-[1.6rem]">
                      Бесплатная консультация
                    </h4>
                    <p className="mt-3 pr-14 text-sm leading-relaxed text-neutral-300 sm:pr-0">
                      {nbsp('Разберу вашу ситуацию и скажу, с какой услуги начать.')}
                    </p>
                    <Arrow dark />
                  </a>
                </Reveal>
              )}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

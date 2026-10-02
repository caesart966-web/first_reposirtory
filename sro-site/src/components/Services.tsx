import { serviceBySlug } from '../content/services'
import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { GoTo } from './ui/GoTo'
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
//
// На телефоне (до 640 px) с 01.10.2026 не карточки, а строки на линейках,
// как «Услуги по теме» внизу внутренних страниц: восемь карточек шли
// два экрана. Тёмная «Бесплатная консультация» остаётся карточкой — это
// приглашение, а не ещё одна услуга. Затемнение при наведении — только
// с 640 px: на телефоне наведение «залипает» после касания, и строка
// без фона получила бы белый текст на светлом листе.
const CARD =
  'group relative flex flex-col border-b border-neutral-300 py-5 pr-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400 sm:h-full sm:min-h-[13rem] sm:rounded-3xl sm:border-0 sm:bg-neutral-50 sm:p-7 sm:transition-colors sm:duration-700 sm:ease-silk sm:hover:bg-neutral-950 sm:focus-visible:bg-neutral-950 sm:focus-visible:ring-0 lg:min-h-[14.5rem]'
const CARD_DARK =
  'group relative mt-4 flex h-full flex-col rounded-3xl bg-accent-950 p-6 pr-14 transition-colors duration-700 ease-silk hover:bg-neutral-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400 sm:mt-0 sm:min-h-[13rem] sm:p-7 lg:min-h-[14.5rem]'

// Стрелка: на компьютере — внизу справа под текстом; на телефоне — справа
// от строки, по центру. С 01.10.2026 без кружка (правило кружков —
// ui/GoTo.tsx): карточка и так нажимается целиком и темнеет при наведении,
// а стрелка за ней светлеет.
function Arrow({ dark = false }: { dark?: boolean }) {
  return (
    <span
      className={`absolute top-1/2 -translate-y-1/2 sm:static sm:mt-auto sm:flex sm:translate-y-0 sm:justify-end sm:pt-6 ${
        dark ? 'right-6' : 'right-0'
      }`}
    >
      <GoTo
        tone={dark ? 'light' : 'ink'}
        className={dark ? '' : 'sm:group-hover:text-neutral-50 sm:group-focus-visible:text-neutral-50'}
      />
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

      <div className="mt-12 space-y-10 sm:mt-16 sm:space-y-14">
        {GROUPS.map((group, groupIndex) => (
          <div key={group.title}>
            <Reveal>
              <h3 className="text-sm text-neutral-600">{group.title}</h3>
            </Reveal>
            {/* Карточка — лист без рамки и тени. При наведении медленно темнеет
                до графита, стрелка поворачивается — приём из ролика заказчика.
                Описание видно всегда: спрятанное до наведения, оно оставляло
                пустые карточки, а на телефоне не читалось бы вовсе. */}
            <div className="mt-3 grid border-t border-neutral-300 sm:mt-5 sm:grid-cols-2 sm:gap-3 sm:border-t-0 lg:grid-cols-4">
              {group.slugs.map(serviceOf).map((service, index) => (
                <Reveal key={service.slug} delay={(index % 4) * 90} className="h-full">
                  <a href={page(service.path)} className={CARD}>
                    {/* На 1024–1279px кегль на ступень меньше: колонка там уже
                        всего, и «Сопровождение» не помещалось в строку. */}
                    <h4 className="font-display text-[1.4rem] font-medium leading-[1.1] text-neutral-950 sm:text-[1.6rem] sm:transition-colors sm:duration-700 sm:ease-silk sm:group-hover:text-neutral-50 sm:group-focus-visible:text-neutral-50 lg:text-[1.45rem] xl:text-[1.6rem]">
                      {nbsp(service.short)}
                    </h4>
                    <p className="mt-1.5 text-sm leading-relaxed text-neutral-600 sm:mt-3 sm:transition-colors sm:duration-700 sm:group-hover:text-neutral-300 sm:group-focus-visible:text-neutral-300">
                      {nbsp(service.hint)}
                    </p>
                    <Arrow />
                  </a>
                </Reveal>
              ))}
              {groupIndex === GROUPS.length - 1 && (
                <Reveal delay={group.slugs.length * 90} className="h-full">
                  <a href="#contacts" className={CARD_DARK}>
                    <h4 className="font-display text-[1.4rem] font-medium leading-[1.1] text-neutral-50 sm:text-[1.6rem] lg:text-[1.45rem] xl:text-[1.6rem]">
                      Бесплатная консультация
                    </h4>
                    <p className="mt-1.5 text-sm leading-relaxed text-neutral-300 sm:mt-3">
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

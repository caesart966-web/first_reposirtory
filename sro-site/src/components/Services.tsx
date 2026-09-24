import { ArrowUpRight } from 'lucide-react'
import { serviceBySlug } from '../content/services'
import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Восемь равнозначных карточек читались как каша, поэтому услуги разбиты
// на две понятные группы: что делаем с самой СРО и что — со специалистами.
//
// Каждая карточка ведёт на отдельную страницу услуги (/uslugi/…): заказчик
// попросил, чтобы посетитель, кликнув по карточке, попадал на страницу
// с полным описанием, а не прыгал по главной. Страниц семь, карточек восемь:
// «Подбор СРО» и «Проверка СРО» — одна тема и одна страница. Поэтому
// карточки и приподнимаются при наведении: по правилу из ui/card.ts подъём —
// обещание клика, и здесь оно честное.
type ServiceItem = { title: string; text: string; slug: string }
type ServiceGroup = { title: string; items: ServiceItem[] }

const GROUPS: ServiceGroup[] = [
  {
    title: 'Вступление и сопровождение',
    items: [
      {
        title: 'Вступление в СРО',
        text: 'Организую процесс от выбора СРО до внесения компании в реестр членов.',
        slug: 'vstuplenie',
      },
      {
        title: 'Подбор СРО',
        text: 'Сравню требования, размеры взносов и условия нескольких организаций и предложу подходящие варианты.',
        slug: 'podbor',
      },
      {
        title: 'Подготовка документов',
        text: 'Соберу полный пакет и выверю каждый документ перед подачей.',
        slug: 'dokumenty',
      },
      {
        title: 'Проверка СРО',
        text: 'Проверю статус организации по открытым реестрам до оплаты взносов.',
        slug: 'podbor',
      },
    ],
  },
  {
    title: 'Специалисты и реестры',
    items: [
      {
        title: 'НРС',
        text: 'Проверю соответствие сотрудников требованиям и подготовлю документы для включения в национальный реестр специалистов.',
        slug: 'nrs',
      },
      {
        title: 'НОК',
        text: 'Расскажу, как проходит независимая оценка квалификации, и помогу подготовиться к профессиональному экзамену.',
        slug: 'nok',
      },
      {
        title: 'Расширение видов работ',
        text: 'Оформлю изменение уровня ответственности или состава видов работ.',
        slug: 'uroven',
      },
      {
        title: 'Сопровождение проверок',
        text: 'Подготовлю к проверке СРО и помогу корректно ответить на запросы.',
        slug: 'proverki',
      },
    ],
  },
]

// Адрес страницы по ключу; неизвестный ключ — ошибка сборки данных, а не
// молчаливая ссылка в никуда.
const pathOf = (slug: string) => {
  const service = serviceBySlug(slug)
  if (!service) throw new Error(`Нет страницы услуги: ${slug}`)
  return page(service.path)
}

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
                восемь пустых карточек, а на телефоне не читалось бы вовсе. */}
            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {group.items.map((service, index) => (
                <Reveal key={service.title} delay={(index % 4) * 90} className="h-full">
                  <a
                    href={pathOf(service.slug)}
                    className="group relative flex h-full flex-col justify-between gap-6 sm:min-h-[13rem] sm:gap-8 rounded-3xl bg-neutral-50 p-6 transition-colors duration-700 ease-silk hover:bg-neutral-950 focus-visible:bg-neutral-950 focus-visible:outline-none sm:p-7 lg:min-h-[15rem]"
                  >
                    {/* Кружок-стрелка стоит отдельной строкой над заголовком,
                        а не рядом с ним: в четыре колонки рядом с кружком
                        «Сопровождение» не помещалось и выталкивало его за
                        край карточки. На 1024–1279px кегль на ступень меньше:
                        колонка там уже всего. */}
                    <div>
                      <span className="flex h-9 w-9 items-center justify-center rounded-full border border-neutral-300 text-neutral-950 transition-all duration-700 ease-silk group-hover:rotate-45 group-hover:border-neutral-50 group-hover:bg-neutral-50 group-focus-visible:border-neutral-50 group-focus-visible:bg-neutral-50">
                        <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                      </span>
                      <h4 className="mt-6 font-display text-[1.6rem] font-medium leading-[1.1] text-neutral-950 transition-colors duration-700 ease-silk group-hover:text-neutral-50 group-focus-visible:text-neutral-50 lg:text-[1.45rem] xl:text-[1.6rem]">
                        {nbsp(service.title)}
                      </h4>
                    </div>
                    <p className="text-sm leading-relaxed text-neutral-600 transition-colors duration-700 group-hover:text-neutral-300 group-focus-visible:text-neutral-300">
                      {service.text}
                    </p>
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

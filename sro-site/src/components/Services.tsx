import {
  ArrowRight,
  Building2,
  FileText,
  GraduationCap,
  Handshake,
  ListPlus,
  Search,
  ShieldCheck,
  UserCheck,
  type LucideIcon,
} from 'lucide-react'
import { anchor } from '../lib/site'
import { cardHover } from './ui/card'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Восемь равнозначных карточек читались как каша, поэтому услуги разбиты
// на две понятные группы: что делаем с самой СРО и что — со специалистами.
//
// Каждая карточка — ссылка на раздел, где об этой услуге рассказано
// подробно: страницы видов, документы, специалисты НРС, ответ в FAQ.
// Заказчик попросил, чтобы с карточки можно было попасть к нужной
// информации, а не только прочитать три строки. Поэтому карточки и
// приподнимаются при наведении: по правилу из ui/card.ts подъём — это
// обещание клика, и здесь оно честное. Подпись ссылки называет, куда
// ведёт, — «Подробнее» без адресата ничего не обещает.
type ServiceGroup = {
  title: string
  items: { icon: LucideIcon; title: string; text: string; href: string; link: string }[]
}

const GROUPS: ServiceGroup[] = [
  {
    title: 'Вступление и сопровождение',
    items: [
      {
        icon: Building2,
        title: 'Вступление в СРО',
        text: 'Организую процесс от выбора СРО до внесения компании в реестр членов.',
        href: '#types',
        link: 'Виды СРО и порядок вступления',
      },
      {
        icon: Search,
        title: 'Подбор СРО',
        text: 'Сравню требования, размеры взносов и условия нескольких организаций и предложу подходящие варианты.',
        href: '#process',
        link: 'Как проходит работа',
      },
      {
        icon: FileText,
        title: 'Подготовка документов',
        text: 'Соберу полный пакет и выверю каждый документ перед подачей.',
        href: '#documents',
        link: 'Что войдёт в пакет',
      },
      {
        icon: ShieldCheck,
        title: 'Проверка СРО',
        text: 'Проверю статус организации по открытым реестрам до оплаты взносов.',
        href: '#faq-check',
        link: 'Как проходит проверка',
      },
    ],
  },
  {
    title: 'Специалисты и реестры',
    items: [
      {
        icon: UserCheck,
        title: 'НРС',
        text: 'Проверю соответствие сотрудников требованиям и подготовлю документы для включения в национальный реестр специалистов.',
        href: '#nrs',
        link: 'Требования и варианты решения',
      },
      {
        icon: GraduationCap,
        title: 'НОК',
        text: 'Расскажу, как проходит независимая оценка квалификации, и помогу подготовиться к профессиональному экзамену.',
        href: '#nrs-nok',
        link: 'Что нужно для включения в реестр',
      },
      {
        icon: ListPlus,
        title: 'Расширение видов работ',
        text: 'Оформлю изменение уровня ответственности или состава видов работ.',
        href: '#types',
        link: 'Уровни ответственности и взносы',
      },
      {
        icon: Handshake,
        title: 'Сопровождение проверок',
        text: 'Подготовлю к проверке СРО и помогу корректно ответить на запросы.',
        href: '#pricing',
        link: 'Формат сопровождения',
      },
    ],
  },
]

export function Services() {
  return (
    <Section id="services" className="bg-neutral-50/55">
      <SectionHeading
        eyebrow="Услуги"
        title="Услуги по вступлению в СРО"
        subtitle="Отдельные задачи или полное сопровождение: от подбора саморегулируемой организации до внесения сведений в реестр членов."
      />

      <div className="mt-10 space-y-10">
        {GROUPS.map((group) => (
          <div key={group.title}>
            <Reveal>
              <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-600">
                {group.title}
              </h3>
            </Reveal>
            {/* Фотографий в сетке услуг нет: обе группы — про действия, а не
                про области, и любой кадр здесь иллюстрировал бы соседнюю тему.
                Области показаны выше, в «Видах СРО», каждая своим снимком. */}
            <div className="mt-5 grid gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-4">
              {group.items.map((service, index) => (
                <Reveal key={service.title} delay={(index % 4) * 70} className="h-full">
                  {/* До sm иконка стоит в строке с заголовком, а не над ним:
                      столбик «иконка / заголовок / текст» растягивал восемь
                      услуг на четыре экрана прокрутки. С 640px карточек в
                      строке уже две и высота не в дефиците — там прежний
                      столбик, он читается спокойнее. */}
                  <a
                    href={anchor(service.href)}
                    className={`group/card flex h-full flex-col rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6 ${cardHover}`}
                  >
                    <div className="flex items-center gap-3.5 sm:block">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-50 text-accent-600 sm:h-11 sm:w-11">
                        <service.icon className="h-5 w-5" aria-hidden="true" />
                      </div>
                      <h4 className="font-semibold text-neutral-950 sm:mt-5">{service.title}</h4>
                    </div>
                    <p className="mt-2.5 text-sm leading-relaxed text-neutral-600 sm:mt-2">{service.text}</p>
                    {/* Подпись прижата к низу карточки, чтобы стрелки в ряду
                        стояли на одной линии при разной длине текста. */}
                    <span className="mt-auto inline-flex items-center gap-1.5 pt-4 text-sm font-semibold text-accent-700">
                      {service.link}
                      <ArrowRight
                        className="h-4 w-4 shrink-0 transition-transform duration-200 group-hover/card:translate-x-1"
                        aria-hidden="true"
                      />
                    </span>
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

import {
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
import { cardHoverStatic } from './ui/card'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Восемь равнозначных карточек читались как каша, поэтому услуги разбиты
// на две понятные группы: что делаем с самой СРО и что — со специалистами.
type ServiceGroup = {
  title: string
  items: { icon: LucideIcon; title: string; text: string }[]
}

const GROUPS: ServiceGroup[] = [
  {
    title: 'Вступление и сопровождение',
    items: [
      {
        icon: Building2,
        title: 'Вступление в СРО',
        text: 'Организую процесс от выбора СРО до внесения компании в реестр членов.',
      },
      {
        icon: Search,
        title: 'Подбор СРО',
        text: 'Сравню требования, взносы и условия — предложу варианты под вашу задачу.',
      },
      {
        icon: FileText,
        title: 'Подготовка документов',
        text: 'Соберу полный пакет и выверю каждый документ перед подачей.',
      },
      {
        icon: ShieldCheck,
        title: 'Проверка СРО',
        text: 'Проверю статус организации по открытым реестрам до оплаты взносов.',
      },
    ],
  },
  {
    title: 'Специалисты и реестры',
    // Кадр изысканий отсюда уехал в секцию «Виды СРО»: там он один из трёх
    // и работает по назначению — показывает область, — а здесь стоял рядом
    // с карточками про НРС и НОК, к которым отношения не имеет.
    items: [
      {
        icon: UserCheck,
        title: 'НРС',
        text: 'Помогу с включением специалистов в национальный реестр: требования и документы.',
      },
      {
        icon: GraduationCap,
        title: 'НОК',
        text: 'Объясню, как проходит независимая оценка квалификации, и помогу подготовиться.',
      },
      {
        icon: ListPlus,
        title: 'Расширение видов работ',
        text: 'Оформлю изменение уровня ответственности или состава видов работ.',
      },
      {
        icon: Handshake,
        title: 'Сопровождение проверок',
        text: 'Подготовлю к проверке СРО и помогу корректно ответить на запросы.',
      },
    ],
  },
]

export function Services() {
  return (
    <Section id="services" className="bg-neutral-50/55">
      <SectionHeading
        eyebrow="Услуги"
        title="С чем помогу"
        subtitle="Разовые задачи и полное сопровождение — в зависимости от вашей ситуации."
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
                  <article
                    className={`h-full rounded-2xl border border-neutral-200 bg-white p-5 shadow-card sm:p-6 ${cardHoverStatic}`}
                  >
                    <div className="flex items-center gap-3.5 sm:block">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-50 text-accent-600 sm:h-11 sm:w-11">
                        <service.icon className="h-5 w-5" aria-hidden="true" />
                      </div>
                      <h4 className="font-semibold text-neutral-950 sm:mt-5">{service.title}</h4>
                    </div>
                    <p className="mt-2.5 text-sm leading-relaxed text-neutral-600 sm:mt-2">{service.text}</p>
                  </article>
                </Reveal>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

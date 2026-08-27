import {
  Award,
  Briefcase,
  Building2,
  FilePen,
  FileText,
  Gavel,
  GraduationCap,
  Handshake,
  ListPlus,
  Search,
  ShieldCheck,
  UserCheck,
  type LucideIcon,
} from 'lucide-react'
import { IMAGES, type PageImage } from '../content/images'
import { Figure } from './ui/Figure'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Восемь равнозначных карточек читались как каша, поэтому услуги разбиты
// на две понятные группы: что делаем с самой СРО и что — со специалистами.
// Тип явный: без него TypeScript выводит из массива объединение, у одного
// члена которого поля figure нет, и сузить его проверкой не получается.
type ServiceGroup = {
  title: string
  figure?: PageImage
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
        text: 'Соберу и проверю полный пакет, чтобы свести к минимуму риск замечаний и возвратов.',
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
    // Изыскания не показывает ни один конкурент — у всех только стройка,
    // а это отдельная СРО и отдельный клиент.
    figure: IMAGES.survey,
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

// Смежные юридические задачи с визитки: вторичная услуга, поэтому компактным
// списком под основной сеткой и нейтральными иконками, а не акцентными.
const LEGAL = [
  {
    icon: Briefcase,
    title: 'Регистрация и ликвидация',
    text: 'Юридических лиц и предпринимателей — от подачи до внесения записи.',
  },
  {
    icon: FilePen,
    title: 'Изменения в учредительных документах',
    text: 'Подготовлю пакет и сопровожу внесение изменений в ЕГРЮЛ.',
  },
  {
    icon: Gavel,
    title: 'Представление интересов в судах',
    text: 'Досудебная работа и защита позиции компании в судебных спорах.',
  },
  {
    icon: Award,
    title: 'Повышение квалификации и аттестации',
    text: 'Помогу организовать обучение и аттестацию специалистов для СРО и НРС.',
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
            <div className="mt-5 grid gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-4">
              {group.items.map((service, index) => (
                <Reveal key={service.title} delay={(index % 4) * 70} className="h-full">
                  <article className="h-full rounded-2xl border border-neutral-200 bg-white p-6 shadow-card transition-colors duration-200 hover:border-accent-300">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-50 text-accent-600">
                      <service.icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <h4 className="mt-5 font-semibold text-neutral-950">{service.title}</h4>
                    <p className="mt-2 text-sm leading-relaxed text-neutral-600">{service.text}</p>
                  </article>
                </Reveal>
              ))}
            </div>
            {group.figure && (
              <Reveal className="mt-6">
                <Figure
                  {...group.figure}
                  className="max-w-sm"
                  caption="Инженерные изыскания — отдельный вид СРО со своими требованиями к специалистам."
                />
              </Reveal>
            )}
          </div>
        ))}
      </div>

      <Reveal className="mt-12 border-t border-neutral-200 pt-8">
        <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-600">
          Смежные юридические задачи
        </h3>
        <div className="mt-5 grid gap-x-10 gap-y-4 sm:grid-cols-2">
          {LEGAL.map((service) => (
            <div key={service.title} className="flex items-start gap-3">
              <service.icon className="mt-0.5 h-5 w-5 shrink-0 text-neutral-400" aria-hidden="true" />
              <p className="text-sm text-neutral-700">
                <span className="font-medium text-neutral-950">{service.title}</span>{' '}
                <span className="text-neutral-600">— {service.text}</span>
              </p>
            </div>
          ))}
        </div>
        {/* Юридическая часть: та же графика, что и в подложке — весы, а не
            фото ноутбука с молотком. Заменяет прежнюю декоративную SVG:
            два рисунка в одном блоке спорили друг с другом. */}
        <Figure {...IMAGES.legal} className="mt-8 max-w-xs" />
      </Reveal>
    </Section>
  )
}

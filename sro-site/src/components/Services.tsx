import {
  Building2,
  FileText,
  GraduationCap,
  Handshake,
  ListPlus,
  Search,
  ShieldCheck,
  UserCheck,
} from 'lucide-react'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

const SERVICES = [
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
    icon: ShieldCheck,
    title: 'Проверка СРО',
    text: 'Проверю статус организации по открытым реестрам до оплаты взносов.',
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
]

export function Services() {
  return (
    <Section id="services" className="bg-neutral-50/70">
      <SectionHeading
        eyebrow="Услуги"
        title="С чем помогу"
        subtitle="Разовые задачи и полное сопровождение — в зависимости от вашей ситуации."
      />
      <div className="mt-10 grid gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-4">
        {SERVICES.map((service, index) => (
          <Reveal key={service.title} delay={(index % 4) * 70} className="h-full">
            <article className="group h-full rounded-2xl border border-neutral-200 bg-white p-6 shadow-card transition-all duration-200 hover:-translate-y-1 hover:border-accent-200 hover:shadow-card-hover">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-50 text-accent-600 transition-colors duration-200 group-hover:bg-accent-600 group-hover:text-white">
                <service.icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <h3 className="mt-5 font-semibold text-neutral-950">{service.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-neutral-600">{service.text}</p>
            </article>
          </Reveal>
        ))}
      </div>
    </Section>
  )
}

import { Check } from 'lucide-react'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

const PLANS = [
  {
    name: 'Консультация',
    price: 'от [ЦЕНА]',
    featured: false,
    items: [
      'Разбор вашей ситуации',
      'Ответы на вопросы по СРО, НРС и НОК',
      'Понятный план дальнейших шагов',
    ],
  },
  {
    name: 'Подготовка документов',
    price: 'от [ЦЕНА]',
    featured: false,
    items: [
      'Проверка имеющихся документов',
      'Подготовка недостающих',
      'Комплект под требования выбранной СРО',
    ],
  },
  {
    name: 'Вступление в СРО под ключ',
    price: 'от [ЦЕНА]',
    featured: true,
    badge: 'Максимум задач на моей стороне',
    items: [
      'Подбор и проверка СРО',
      'Полный пакет документов',
      'Сопровождение до внесения в реестр',
    ],
  },
]

export function Pricing() {
  return (
    <Section id="pricing" className="bg-neutral-50/70">
      <SectionHeading
        eyebrow="Стоимость"
        title="Форматы работы"
        subtitle="Точную стоимость назову после короткого разбора задачи — письменно и до начала работы."
      />
      <div className="mt-10 grid gap-5 lg:grid-cols-3">
        {PLANS.map((plan, index) => (
          <Reveal key={plan.name} delay={index * 80} className="h-full">
            <article
              className={`relative flex h-full flex-col rounded-2xl border bg-white p-7 shadow-card transition-all duration-200 hover:-translate-y-1 hover:shadow-card-hover ${
                plan.featured ? 'border-accent-300 ring-1 ring-accent-200' : 'border-neutral-200'
              }`}
            >
              {plan.featured && plan.badge && (
                <span className="absolute -top-3 left-6 rounded-full bg-accent-600 px-3 py-1 text-xs font-semibold text-white">
                  {plan.badge}
                </span>
              )}
              <h3 className="font-semibold text-neutral-950">{plan.name}</h3>
              <p className="mt-3 text-3xl font-bold tracking-tight text-neutral-950">
                {plan.price}
              </p>
              <ul className="mt-5 space-y-2.5">
                {plan.items.map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm text-neutral-600">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </article>
          </Reveal>
        ))}
      </div>
      <Reveal className="mt-9 text-center">
        <ButtonLink href="#quiz" size="lg">
          Получить расчёт стоимости
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

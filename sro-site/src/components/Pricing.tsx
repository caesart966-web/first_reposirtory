import { Check } from 'lucide-react'
import { ButtonLink } from './ui/Button'
import { cardHoverStatic } from './ui/card'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Строка цены есть у всех трёх форматов, а не только у бесплатного: карточка
// без неё выглядела бы так, будто цену скрывают, и ряд разъезжался бы по высоте.
// Цифр здесь нет и быть не может — их называют после разбора задачи.
const PLANS = [
  {
    name: 'Консультация',
    price: 'Бесплатно',
    priceNote: 'на любом этапе, не только первый разговор',
    free: true,
    featured: false,
    items: [
      'Разбор вашей ситуации',
      'Ответы на вопросы по СРО, НРС и НОК',
      'Понятный план дальнейших шагов',
    ],
  },
  {
    name: 'Подготовка документов',
    price: 'По задаче',
    priceNote: 'зависит от объёма и готовности бумаг',
    free: false,
    featured: false,
    items: [
      'Проверка имеющихся документов',
      'Подготовка недостающих',
      'Комплект под требования выбранной СРО',
    ],
  },
  {
    name: 'Вступление в СРО под ключ',
    price: 'По задаче',
    priceNote: 'зависит от вида СРО и состава работ',
    free: false,
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
    <Section id="pricing">
      <SectionHeading
        eyebrow="Стоимость"
        title="Форматы работы"
        subtitle="Консультация бесплатная — платите только за работу. Её стоимость зависит от вида СРО и готовности документов; назову цифру письменно, до начала."
      />
      <div className="mt-10 grid gap-5 lg:grid-cols-3">
        {PLANS.map((plan, index) => (
          <Reveal key={plan.name} delay={index * 80} className="h-full">
            <article
              className={`relative flex h-full flex-col rounded-2xl border bg-white p-7 shadow-card ${cardHoverStatic} ${
                plan.featured ? 'border-accent-300 ring-1 ring-accent-200' : 'border-neutral-200'
              }`}
            >
              {plan.featured && plan.badge && (
                <span className="absolute -top-3 left-6 rounded-full bg-accent-600 px-3 py-1 text-xs font-semibold text-white">
                  {plan.badge}
                </span>
              )}
              <h3 className="text-lg font-semibold text-neutral-950">{plan.name}</h3>
              <p
                className={`mt-3 text-2xl font-bold tracking-tight ${
                  plan.free ? 'text-accent-600' : 'text-neutral-950'
                }`}
              >
                {plan.price}
              </p>
              <p className="mt-1 text-sm text-neutral-500">{plan.priceNote}</p>
              <ul className="mt-5 space-y-2.5 border-t border-neutral-200 pt-5">
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
          Узнать стоимость для моей компании
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

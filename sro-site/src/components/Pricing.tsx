import { ButtonLink } from './ui/Button'
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
    priceNote: 'зависит от объёма и готовности документов',
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
    badge: 'Полное сопровождение',
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
        subtitle="Консультации бесплатны на любом этапе. Стоимость работы зависит от вида СРО и готовности документов и согласовывается письменно до начала."
      />
      {/* Три колонки листами, без рамок и теней. Главный формат — тёмный:
          выделен цветом листа, а не плашкой «хит» над ним. */}
      <div className="mt-16 grid gap-3 lg:grid-cols-3">
        {PLANS.map((plan, index) => (
          <Reveal key={plan.name} delay={index * 100} className="h-full">
            <article
              className={`flex h-full flex-col rounded-3xl p-7 sm:p-9 ${
                plan.featured ? 'bg-neutral-950 text-neutral-50' : 'bg-neutral-100 text-neutral-950'
              }`}
            >
              <p className={`text-sm ${plan.featured ? 'text-accent-200' : 'text-neutral-600'}`}>
                {plan.featured && plan.badge ? plan.badge : 'Формат'}
              </p>
              <h3 className="mt-3 font-display text-[1.9rem] font-medium leading-tight">{plan.name}</h3>
              <p className="mt-10 font-display text-[2.6rem] font-medium leading-none">{plan.price}</p>
              <p className={`mt-3 text-sm ${plan.featured ? 'text-neutral-300' : 'text-neutral-600'}`}>
                {plan.priceNote}
              </p>
              <ul
                className={`mt-8 space-y-3 border-t pt-6 text-sm ${
                  plan.featured ? 'border-white/15 text-neutral-200' : 'border-neutral-300 text-neutral-700'
                }`}
              >
                {plan.items.map((item) => (
                  <li key={item} className="flex gap-3">
                    <span
                      className={`mt-2 h-1 w-1 shrink-0 rounded-full ${plan.featured ? 'bg-accent-300' : 'bg-accent-500'}`}
                      aria-hidden="true"
                    />
                    {item}
                  </li>
                ))}
              </ul>
            </article>
          </Reveal>
        ))}
      </div>
      <Reveal className="mt-12">
        <ButtonLink href="#contacts" size="lg" arrow>
          Узнать стоимость для моей компании
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

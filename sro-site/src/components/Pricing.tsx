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
      'План действий по шагам',
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
        title="Форматы работы"
        subtitle="Стоимость работы зависит от вида СРО и готовности документов и согласовывается письменно до начала."
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
              {/* Подписи «Формат» над каждой карточкой больше нет: одинаковая
                  рубрика над тремя листами ничего не сообщала. Главный формат
                  выделен цветом листа. */}
              {/* Высота названия — на две строки у всех трёх: иначе
                  «Консультация» в одну строку поднимала свою цену выше
                  соседних, и ряд цен шёл лесенкой. */}
              <h3 className="font-display text-[1.9rem] font-medium leading-tight lg:min-h-[2.5em]">{plan.name}</h3>
              <p className="mt-8 font-display text-[2.6rem] font-medium leading-none lg:mt-6">{plan.price}</p>
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
      {/* На телефоне — «Узнать стоимость»: полная надпись не помещалась
          в строку, и кнопка ломалась на две. */}
      <Reveal className="mt-12">
        <ButtonLink href="#contacts" size="lg" arrow>
          {/* Одним span: иначе хвост надписи становился отдельным элементом
              кнопки и отодвигался от начала на её зазор. */}
          <span>
            Узнать стоимость<span className="hidden sm:inline">&nbsp;для моей компании</span>
          </span>
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

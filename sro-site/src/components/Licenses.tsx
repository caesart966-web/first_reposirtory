import { Award, Factory, FireExtinguisher, HardHat, Landmark, Wrench, Zap } from 'lucide-react'
import { EXTRA_GROUPS, EXTRA_ID, type ExtraIcon } from '../content/extra'
import { nbsp } from '../lib/typo'
import { Law } from './PageParts'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Лицензии, обучение сотрудников, ISO 9001 (02.10.2026, просьба заказчика).
// Данные — content/extra.ts.
//
// Раскладка взята из образца, который заказчик присылал 24.09.2026 (шаблон
// юридической фирмы, блок «Practice Areas»): слева название направления
// и строка о том, что я делаю, справа — пункты сеткой, у каждого значок,
// название и две строки. Синие плитки, отзывы и счётчики образца не взяты:
// синего на сайте нет, а отзывов и цифр у нас нет. Значки — те же линейные
// латунные квадраты, что у видов СРО на первом экране; рядом с каждым
// пунктом — норма, как везде на сайте.
//
// Место — после «Форматов работы», перед «О компании»: всё про СРО
// сказано до него, и раздел не разрывает путь «услуги → как работаю →
// документы → специалисты → стоимость». Фон кремовый: соседи белый
// и тёмный.
const ICONS: Record<ExtraIcon, typeof Award> = {
  fire: FireExtinguisher,
  heritage: Landmark,
  labor: HardHat,
  electric: Zap,
  industrial: Factory,
  trade: Wrench,
  quality: Award,
}

export function Licenses() {
  return (
    <Section id={EXTRA_ID} className="bg-neutral-100">
      <SectionHeading
        title="Лицензии, обучение и сертификация"
        titleClassName="max-[379px]:text-[2.2rem]"
        subtitle="Для строительных, проектных и изыскательских компаний — вместе со вступлением в СРО или отдельно."
      />

      <div className="mt-12 border-t border-neutral-300 sm:mt-16">
        {EXTRA_GROUPS.map((group) => (
          <div
            key={group.title}
            className="grid gap-6 border-b border-neutral-300 py-9 sm:py-12 lg:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)] lg:gap-16"
          >
            <Reveal>
              <h3 className="font-display text-[1.75rem] font-medium leading-tight text-neutral-950 sm:text-[2rem]">
                {group.title}
              </h3>
              <p className="mt-3 max-w-md text-base leading-relaxed text-neutral-600">{nbsp(group.lead)}</p>
            </Reveal>
            <ul className="grid gap-x-10 gap-y-8 sm:grid-cols-2">
              {group.items.map((item, index) => {
                const Icon = ICONS[item.icon]
                return (
                  // Единственный пункт группы (ISO 9001) — на обе колонки:
                  // в одной справа оставалась пустая половина ряда.
                  <li key={item.title} className={group.items.length === 1 ? 'sm:col-span-2 sm:max-w-2xl' : ''}>
                    <Reveal delay={(index % 2) * 90} className="flex gap-4">
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-50 text-accent-700 ring-1 ring-inset ring-accent-200/70">
                        <Icon className="h-5 w-5" strokeWidth={1.6} aria-hidden="true" />
                      </span>
                      <div className="min-w-0">
                        <h4 className="text-lg font-semibold leading-snug text-neutral-950">{item.title}</h4>
                        <p className="mt-1.5 text-[0.9375rem] leading-relaxed text-neutral-700">{nbsp(item.text)}</p>
                        <Law>{item.law}</Law>
                      </div>
                    </Reveal>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>

      <Reveal className="mt-12 flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-xl text-lg text-neutral-700">
          {nbsp('Расскажите, что нужно, — назову срок и стоимость.')}
        </p>
        <ButtonLink href="#contacts" size="lg" arrow className="shrink-0">
          Обсудить задачу
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

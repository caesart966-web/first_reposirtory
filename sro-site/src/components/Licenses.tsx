import { Award, Factory, FireExtinguisher, GraduationCap, HardHat, Landmark, ScrollText, Wrench, Zap } from 'lucide-react'
import { EXTRA_GROUPS, EXTRA_ID, type ExtraIcon } from '../content/extra'
import { nbsp } from '../lib/typo'
import { Law } from './PageParts'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Лицензии, обучение сотрудников, ISO 9001 (02.10.2026, просьба заказчика).
// Данные — content/extra.ts.
//
// Оформление — «три листа» (вариант Б, выбор заказчика из трёх макетов
// 02.10.2026; отклонены «строки по группам» и «плитки»). Каждая группа —
// свой лист: значок группы, название, строка о том, что я делаю, и пункты
// на линейках — значок, название, две строки, норма. Идея листов-направлений
// — из образца заказчика 24.09.2026 (блок «Practice Areas»); синие плитки,
// отзывы и счётчики образца не взяты.
//
// На компьютере обучение (четыре пункта) — справа во всю высоту, слева
// лицензии и сертификация: высоты колонок сходятся. В разметке группы идут
// по порядку данных, раскладку задаёт сетка: на телефоне листы стоят
// в том же порядке — лицензии, обучение, сертификация.
//
// Над разделом стоят «Форматы работы» тоже листами. Чтобы два раздела
// не читались одним, цвета обратные: там кремовые листы на белом, здесь
// белые на кремовом, и у каждого листа латунный значок группы.
//
// Место — после «Форматов работы», перед «О компании»: всё про СРО сказано
// до него, и раздел не разрывает путь «услуги → как работаю → документы →
// специалисты → стоимость».
const GROUP_ICONS = [ScrollText, GraduationCap, Award]

const ICONS: Record<ExtraIcon, typeof Award> = {
  fire: FireExtinguisher,
  heritage: Landmark,
  labor: HardHat,
  electric: Zap,
  industrial: Factory,
  trade: Wrench,
  quality: Award,
}

// Место листа в сетке с 1024 px: обучение — справа на две строки.
const PLACE = ['lg:col-start-1 lg:row-start-1', 'lg:col-start-2 lg:row-span-2 lg:row-start-1', 'lg:col-start-1 lg:row-start-2']

export function Licenses() {
  return (
    <Section id={EXTRA_ID} className="bg-neutral-100">
      <SectionHeading
        title="Лицензии, обучение и сертификация"
        titleClassName="max-[379px]:text-[2.2rem]"
        subtitle="Для строительных, проектных и изыскательских компаний — вместе со вступлением в СРО или отдельно."
      />

      <div className="mt-12 grid gap-3 sm:mt-16 lg:grid-cols-2 lg:grid-rows-[auto_auto]">
        {EXTRA_GROUPS.map((group, index) => {
          const GroupIcon = GROUP_ICONS[index] ?? Award
          return (
            <Reveal key={group.title} delay={index * 90} className={`h-full ${PLACE[index] ?? ''}`}>
              <article className="flex h-full flex-col rounded-3xl bg-neutral-50 p-6 sm:p-9">
                <div className="flex items-center gap-4">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-accent-600 text-neutral-50 sm:h-12 sm:w-12">
                    <GroupIcon className="h-[1.375rem] w-[1.375rem] sm:h-6 sm:w-6" strokeWidth={1.6} aria-hidden="true" />
                  </span>
                  <h3 className="font-display text-[1.65rem] font-medium leading-tight text-neutral-950 sm:text-[1.9rem]">
                    {group.title}
                  </h3>
                </div>
                <p className="mt-4 text-[0.9375rem] leading-relaxed text-neutral-600">{nbsp(group.lead)}</p>
                <ul className="mt-5 border-t border-neutral-300 sm:mt-6">
                  {group.items.map((item) => {
                    const Icon = ICONS[item.icon]
                    return (
                      <li key={item.title} className="flex gap-3.5 border-b border-neutral-200 py-4 last:border-b-0 last:pb-0 sm:py-5">
                        <Icon className="mt-0.5 h-5 w-5 shrink-0 text-accent-700" strokeWidth={1.6} aria-hidden="true" />
                        <div className="min-w-0">
                          <h4 className="text-lg font-semibold leading-snug text-neutral-950">{item.title}</h4>
                          <p className="mt-1 text-[0.9375rem] leading-relaxed text-neutral-700">{nbsp(item.text)}</p>
                          <Law>{item.law}</Law>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              </article>
            </Reveal>
          )
        })}
      </div>

      <Reveal className="mt-12 flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-xl text-lg text-neutral-700">{nbsp('Расскажите, что нужно, — назову срок и стоимость.')}</p>
        <ButtonLink href="#contacts" size="lg" arrow className="shrink-0">
          Обсудить задачу
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

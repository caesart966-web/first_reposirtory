import { Award, ChevronDown, GraduationCap, ScrollText } from 'lucide-react'
import { useState } from 'react'
import { EXTRA_GROUPS, EXTRA_ID } from '../content/extra'
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
// на линейках — название, две строки, норма. Мелких значков у пунктов нет
// (решение заказчика 02.10.2026): в 20 px огнетушитель, завод и ключ
// не различались и читались точками перед строкой, а значок группы уже
// делит раздел на листы. Идея листов-направлений
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
// Место — перед «О компании»: всё про СРО сказано до него, и раздел
// не разрывает путь «услуги → как работаю → стоимость → специалисты →
// документы». С 22.10.2026 над ним «Документы» (белый фон), а не «Форматы
// работы»; белые листы на кремовом остались — раздел и так отделён фоном.
//
// До 1024 px (22.10.2026, разбор главной) лист свёрнут: значок, название
// и перечень пунктов одной строкой («Лицензия МЧС · Лицензия Минкультуры»);
// нажатие раскрывает описание и пункты с нормами — плавно, по высоте,
// как группы ссылок в подвале. Развёрнутые листы занимали на телефоне
// 2,8 экрана — больше любого раздела главной, хотя это не основная
// услуга. Название — кнопка только там, где лист сворачивается;
// с 1024 px листы открыты всегда, и aria-expanded был бы неправдой.
// Текст пунктов всегда в разметке — скрыт только стилем.
const GROUP_ICONS = [ScrollText, GraduationCap, Award]

// Место листа в сетке с 1024 px: обучение — справа на две строки.
const PLACE = ['lg:col-start-1 lg:row-start-1', 'lg:col-start-2 lg:row-span-2 lg:row-start-1', 'lg:col-start-1 lg:row-start-2']

export function Licenses() {
  return (
    <Section id={EXTRA_ID} className="bg-neutral-100">
      <SectionHeading
        title="Лицензии, обучение и сертификация"
        titleClassName="max-[379px]:text-[2.2rem]"
        subtitle={'Для строительных, проектных и изыскательских компаний — вместе со вступлением в СРО или\u00A0отдельно.'}
      />

      <div className="mt-10 grid gap-3 sm:mt-16 lg:grid-cols-2 lg:grid-rows-[auto_auto]">
        {EXTRA_GROUPS.map((group, index) => (
          <Reveal key={group.title} delay={index * 90} className={`h-full ${PLACE[index] ?? ''}`}>
            <Sheet group={group} index={index} />
          </Reveal>
        ))}
      </div>

      <Reveal className="mt-12 flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-xl text-lg text-neutral-700">{nbsp('Расскажите, что нужно, — назову срок и стоимость.')}</p>
        <ButtonLink href="#contacts" data-topic="licenses" size="lg" arrow className="shrink-0">
          Обсудить задачу
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

function Sheet({ group, index }: { group: (typeof EXTRA_GROUPS)[number]; index: number }) {
  const [open, setOpen] = useState(false)
  const GroupIcon = GROUP_ICONS[index] ?? Award
  const bodyId = `licenzii-${index}`
  const icon = (
    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-accent-600 text-neutral-50 max-[379px]:h-10 max-[379px]:w-10 sm:h-12 sm:w-12">
      <GroupIcon className="h-[1.375rem] w-[1.375rem] sm:h-6 sm:w-6" strokeWidth={1.6} aria-hidden="true" />
    </span>
  )
  return (
    <article className="flex h-full flex-col rounded-3xl bg-neutral-50 p-5 sm:p-9">
      {/* Уже 380 px значок, отступы и кегль на ступень меньше: «Сертификация»
          одним словом рядом со стрелкой раскрытия не помещалась в 320 px. */}
      <h3 className="font-display text-[1.65rem] font-medium leading-tight text-neutral-950 max-[379px]:text-[1.45rem] sm:text-[1.9rem] lg:max-xl:text-[1.8rem]">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={bodyId}
          onClick={() => setOpen((value) => !value)}
          className="-m-2 flex w-[calc(100%+1rem)] items-center gap-4 rounded-2xl p-2 text-left max-[379px]:gap-3 [-webkit-tap-highlight-color:transparent] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 lg:hidden"
        >
          {icon}
          <span className="min-w-0 flex-1">{group.title}</span>
          <ChevronDown
            className={`h-5 w-5 shrink-0 text-neutral-600 transition-transform duration-500 ease-silk ${open ? 'rotate-180' : ''}`}
            aria-hidden="true"
          />
        </button>
        <span className="hidden items-center gap-4 lg:flex">
          {icon}
          {group.title}
        </span>
      </h3>
      {/* Перечень пунктов — пока лист свёрнут: видно, что внутри, не раскрывая.
          Сворачивается тем же движением, каким раскрывается лист. Название
          пункта не рвётся («Рабочие / профессии»): перенос только у точки. */}
      <div
        className={`grid transition-[grid-template-rows,opacity] duration-500 ease-silk lg:hidden ${
          open ? 'grid-rows-[0fr] opacity-0' : 'grid-rows-[1fr] opacity-100'
        }`}
        aria-hidden="true"
      >
        <div className="overflow-hidden">
          <p className="pt-3 text-[0.9375rem] leading-snug text-neutral-700" onClick={() => setOpen(true)}>
            {group.items.map((item) => item.title.replace(/ /g, '\u00a0')).join(' · ')}
          </p>
        </div>
      </div>
      <div
        id={bodyId}
        className={`grid transition-[grid-template-rows,opacity,visibility] duration-500 ease-silk lg:block ${
          open ? 'visible grid-rows-[1fr] opacity-100' : 'invisible grid-rows-[0fr] opacity-0 lg:visible lg:opacity-100'
        }`}
      >
        <div className="overflow-hidden lg:overflow-visible">
          <p className="mt-4 text-[0.9375rem] leading-relaxed text-neutral-600">{nbsp(group.lead)}</p>
          <ul className="mt-5 border-t border-neutral-300 sm:mt-6">
            {group.items.map((item) => (
              <li key={item.title} className="border-b border-neutral-200 py-4 last:border-b-0 last:pb-0 sm:py-5">
                <h4 className="text-lg font-semibold leading-snug text-neutral-950">{item.title}</h4>
                <p className="mt-1 text-[0.9375rem] leading-relaxed text-neutral-700">{nbsp(item.text)}</p>
                <Law>{item.law}</Law>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </article>
  )
}

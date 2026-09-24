import { FACTS, REQUISITES, isPlaceholder } from '../content/facts'
import { ScalesMark } from './illustrations'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Максимум три и строками, а не карточками: карточки уже заняты услугами.
const ADVANTAGES = [
  'Прямая связь со специалистом, без колл-центра и передачи задачи между отделами',
  'Три вида СРО: строительство, проектирование, инженерные изыскания',
  'Сопровождение после вступления: проверки СРО, изменение видов работ, вопросы НРС',
]

// Пока цифр практики нет, во вводном абзаце их не упоминаем вовсе —
// плейсхолдеры в прозе выглядят ещё хуже, чем в полосе фактов.
const FACTS_READY = !isPlaceholder(FACTS.yearsOfPractice) && !isPlaceholder(FACTS.companies)

// Город из адреса реквизитов: полный адрес в визитке не нужен, он в подвале.
const CITY = 'Ростов-на-Дону'

// Полосы цифр здесь больше нет (06.09.2026): заказчик посмотрел на живом
// сайте и решил, что она не вписывается. Цифры и так есть в тексте рядом:
// три вида СРО — в списке преимуществ, регионы — в блоке географии,
// бесплатная консультация — в «Стоимости».
export function AboutExpert() {
  return (
    <Section id="about" className="bg-neutral-100">
      <div className="grid gap-14 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] lg:gap-20">
        <div>
          <SectionHeading eyebrow="О нас" title="Как построена работа" />
          <Reveal delay={120}>
            <p className="mt-8 font-display text-[1.55rem] font-medium leading-snug text-neutral-950 sm:text-[1.9rem]">
              {FACTS_READY ? (
                <>
                  {REQUISITES.legalName} занимается вступлением в СРО {FACTS.yearsOfPractice} лет;
                  за это время сопровождение прошли {FACTS.companies} компаний из {FACTS.regions}{' '}
                  регионов.
                </>
              ) : (
                <>
                  {REQUISITES.legalName} занимается вступлением в СРО строителей,
                  проектировщиков и изыскателей, а также вопросами специалистов НРС и
                  независимой оценки квалификации.
                </>
              )}
            </p>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-neutral-600">
              Каждую задачу от начала до конца ведёт один специалист: он отвечает на вопросы,
              готовит документы и взаимодействует с саморегулируемой организацией. Вы всегда
              знаете, кто занимается вашим вопросом и на каком он этапе.
            </p>
          </Reveal>
        </div>
        {/* Карточка компании — тёмный лист со знаком весов. Фотографии нет:
            сайт представляет компанию, а не лицо. Реквизиты — в подвале. */}
        <Reveal delay={160} className="lg:pt-10">
          <div className="relative overflow-hidden rounded-3xl bg-neutral-950 p-8 text-neutral-50 sm:p-10">
            <ScalesMark
              className="pointer-events-none absolute -right-8 -top-6 h-40 w-auto text-white/[0.06]"
              aria-hidden="true"
            />
            <div className="relative">
              <ScalesMark className="h-8 w-auto text-accent-300" aria-hidden="true" />
              <p className="mt-6 font-display text-[1.7rem] font-medium leading-tight">
                {REQUISITES.legalName}
              </p>
              <p className="mt-1 text-sm text-neutral-400">Вступление в СРО · {CITY}</p>
              <ul className="mt-8 space-y-4 border-t border-white/15 pt-6">
                {ADVANTAGES.map((advantage) => (
                  <li key={advantage} className="flex gap-3 text-sm leading-relaxed text-neutral-300">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent-300" aria-hidden="true" />
                    {advantage}
                  </li>
                ))}
                <li className="flex gap-3 text-sm leading-relaxed text-neutral-300">
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent-300" aria-hidden="true" />
                  Дистанционно, личный визит не требуется; работаю по договору
                </li>
              </ul>
              <ButtonLink href="#contacts" variant="inverse" size="md" arrow className="mt-8">
                Обсудить задачу
              </ButtonLink>
            </div>
          </div>
        </Reveal>
      </div>
    </Section>
  )
}

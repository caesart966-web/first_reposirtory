import { FACTS, REQUISITES, isPlaceholder } from '../content/facts'
import { fadeIn } from '../lib/fade'
import { asset } from '../lib/site'
import { nbsp } from '../lib/typo'
import { ScalesMark } from './illustrations'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { SectionHeading } from './ui/Section'

// Строками, а не карточками: карточки уже заняты услугами.
const ADVANTAGES = [
  'Прямая связь со специалистом, без колл-центра',
  'Три вида СРО: строительство, проектирование, инженерные изыскания',
  'Сопровождение после вступления: проверки СРО, изменение уровня ответственности, вопросы НРС',
  'Лицензии МЧС и Минкультуры, обучение сотрудников, сертификация ISO 9001',
  'Дистанционно, личный визит не требуется; работаю по договору',
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
//
// С 26.09.2026 раздел тёмный, и Фемида стоит фоном справа во всю высоту,
// растворяясь к тексту (на телефоне — сверху, растворяясь к заголовку). Раньше
// она стояла в «Как проходит работа», но там она ничего не объясняла: символ
// закона уместен там, где сайт говорит, на чём держится работа. Заголовок
// «Как построена работа» заменён: он почти дословно повторял «Как проходит
// работа» тремя разделами выше. Новый взят из текста самого раздела и ждёт
// подтверждения заказчика: раньше он просил короткий заголовок вместо фразы
// про одного специалиста (см. README, «„О нас“»).
// Карточки компании больше нет — её строки стали списком под текстом,
// подпись со знаком — внизу, как подпись под письмом.
export function AboutExpert() {
  return (
    <section
      id="about"
      className="relative isolate overflow-hidden bg-accent-950 pb-24 pt-[21rem] text-neutral-50 sm:pb-32 sm:pt-[28rem] lg:py-32"
    >
      <picture>
        <source type="image/avif" srcSet={asset('./img/themis-photo.avif')} />
        <img
          src={asset('./img/themis-photo.webp')}
          alt=""
          aria-hidden="true"
          width={1024}
          height={1024}
          loading="lazy"
          decoding="async"
          ref={fadeIn}
          className="about-photo scroll-settle pointer-events-none absolute inset-x-0 top-0 -z-10 h-[26rem] w-full select-none object-cover object-[50%_12%] sm:h-[34rem] lg:inset-x-auto lg:right-0 lg:h-full lg:w-[46%] lg:object-[55%_20%] min-[1800px]:right-[max(0px,calc(50%-56.25rem))] min-[1800px]:w-[51.875rem]"
        />
      </picture>
      <div className="mx-auto w-full max-w-6xl min-[1800px]:max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="lg:max-w-[56%]">
          <SectionHeading dark title="О компании" />
          <Reveal delay={120}>
            {/* На телефоне — обычным шрифтом (01.10.2026): антиквой в 1,45rem
                абзац шёл семью строками и спорил с заголовком раздела.
                С 640 px — крупно антиквой, как было: там он в три строки. */}
            <p className="mt-8 text-lg leading-relaxed text-neutral-50 sm:font-display sm:text-[1.75rem] sm:font-medium sm:leading-snug">
              {FACTS_READY ? (
                <>
                  {REQUISITES.legalName} занимается вступлением в СРО {FACTS.yearsOfPractice} лет;
                  за это время сопровождение прошли {FACTS.companies} компаний из {FACTS.regions}{' '}
                  регионов.
                </>
              ) : (
                nbsp(
                  `${REQUISITES.legalName} занимается вступлением в СРО строителей, проектировщиков и изыскателей, а также вопросами специалистов НРС и независимой оценки квалификации.`,
                )
              )}
            </p>
            <p className="mt-6 text-lg leading-relaxed text-neutral-300">
              {nbsp(
                'Каждую задачу ведёт один специалист — от первого звонка до выписки из реестра. Вы знаете, кому звонить и на каком этапе дело.',
              )}
            </p>
          </Reveal>
          <Reveal delay={200}>
            <ul className="mt-12 border-t border-white/15">
              {ADVANTAGES.map((advantage) => (
                <li key={advantage} className="flex gap-4 border-b border-white/15 py-4 text-neutral-200">
                  <span className="mt-[0.7rem] h-px w-5 shrink-0 bg-accent-300" aria-hidden="true" />
                  <span className="leading-relaxed">{nbsp(advantage)}</span>
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal delay={260}>
            <div className="mt-10 flex flex-wrap items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <ScalesMark className="h-10 w-auto shrink-0 text-accent-300" aria-hidden="true" />
                <div>
                  <p className="font-display text-xl font-medium leading-tight">{REQUISITES.legalName}</p>
                  <p className="mt-1 text-sm text-neutral-400">Вступление в СРО · {CITY}</p>
                </div>
              </div>
              <ButtonLink href="#contacts" variant="inverse" size="md" arrow>
                Обсудить задачу
              </ButtonLink>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}

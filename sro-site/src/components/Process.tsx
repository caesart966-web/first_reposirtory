import { asset } from '../lib/site'
import { Reveal } from './ui/Reveal'
import { SectionHeading } from './ui/Section'

// Четыре шага работы — единственный тёмный раздел посреди страницы,
// и в нём Фемида.
//
// До 24.09.2026 здесь стояла гравюра белым штрихом на графите; заказчик
// попросил её убрать — рядом с его примерами она смотрелась бедно.
// 25.09.2026 на её место встала фотография статуи (выбор заказчика из трёх,
// учёт — в public/img/CREDITS.md). На компьютере она справа, шаги слева
// в две колонки; на телефоне и планшете — над заголовком раздела, и заголовок
// ложится на её растворённый низ. Маски — в index.css (.process-photo): на
// разных ширинах они разные, а классами Tailwind две маски не пересечь.
// Контраст надписей поверх неё меряет scripts/test-hero-contrast.mjs.
//
// «Через форму на сайте» из первого шага убрано вместе с формой.
const STEPS = [
  {
    number: '01',
    title: 'Заявка',
    text: 'Вы рассказываете о задаче — по телефону или в мессенджере.',
  },
  {
    number: '02',
    title: 'Проверка',
    text: 'Изучаю ситуацию и документы, задаю уточняющие вопросы.',
  },
  {
    number: '03',
    title: 'Подготовка',
    text: 'Готовлю необходимый пакет под требования выбранной СРО.',
  },
  {
    number: '04',
    title: 'Сопровождение',
    text: 'Контролирую процесс до результата и держу вас в курсе.',
  },
]

export function Process() {
  return (
    <section
      id="process"
      className="relative isolate overflow-hidden bg-accent-950 pb-24 pt-72 text-neutral-50 sm:pb-32 sm:pt-[26rem] lg:pt-32"
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
          className="process-photo scroll-settle pointer-events-none absolute inset-x-0 top-0 -z-10 h-[26rem] w-full select-none object-cover object-[50%_12%] sm:h-[34rem] lg:inset-x-auto lg:right-0 lg:h-full lg:w-[40%] lg:object-[60%_20%] xl:w-[46%]"
        />
      </picture>
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <SectionHeading dark eyebrow="Процесс" title="Как проходит работа" />
        {/* С 640px — сетка 2×2; на компьютере она занимает левые 58%,
            правее стоит статуя. */}
        <ol className="mt-16 grid border-t border-white/15 sm:grid-cols-2 lg:max-w-[58%]">
          {STEPS.map((step, index) => (
            <li
              key={step.number}
              className="border-b border-white/15 py-8 sm:odd:border-r sm:odd:pr-8 sm:even:pl-8 sm:[&:nth-child(n+3)]:border-b-0"
            >
              <Reveal delay={index * 120}>
                <p className="text-sm tabular-nums text-neutral-400">{step.number}</p>
                <h3 className="mt-6 font-display text-[1.9rem] font-medium leading-tight lg:mt-8">
                  {step.title}
                </h3>
                <p className="mt-3 leading-relaxed text-neutral-300">{step.text}</p>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

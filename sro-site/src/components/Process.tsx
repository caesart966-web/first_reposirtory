import { useEffect, useRef, useState } from 'react'
import { nbsp } from '../lib/typo'
import { Blueprint } from './Blueprint'
import { Reveal } from './ui/Reveal'
import { SectionHeading } from './ui/Section'

// Четыре шага работы — тёмный раздел посреди страницы, пауза между
// светлыми блоками.
//
// С 26.09.2026 без фотографии. Здесь стояла Фемида (до того — гравюра), но
// раздел рассказывает про шаги, а символ правосудия ни один шаг не объясняет:
// она переехала в «О нас», где сайт говорит, на чём держится работа.
// Номера здесь по делу: это последовательность.
//
// С 19.10.2026 — чертёж, который достраивается по шагам (заказчик прислал
// шаблон Ora со scrolltide.co: часы разбираются и собираются, пока страницу
// листают). Здесь тот же приём «главами», но своим рисунком: шаги идут
// столбиком, рядом стоит чертёж дома латунными линиями, и с каждым шагом
// на нём прибавляется стадия (Blueprint.tsx). 20.10.2026 («чуть красивее
// и профессиональнее»): чертёж стал листом с осями, отметками и штампом,
// а у шагов слева — шкала: линия заполняется по мере прокрутки, точка
// шага загорается, когда до него дошли.
// Не 240 кадров, а один SVG в несколько килобайт: на телефоне ни ожидания,
// ни лишнего трафика. Шаг, который сейчас читают, — тот, чей верх прошёл
// 55 % высоты окна; остальные чуть приглушены (не ниже 0,6: текст
// остаётся читаемым, 5:1 и выше).
//
// Без скрипта (готовый HTML для поисковика) и при «уменьшить движение»
// чертёж стоит готовым и все шаги видны одинаково.
//
// «Через форму на сайте» из первого шага убрано вместе с формой.
const STEPS = [
  {
    number: '01',
    title: 'Заявка',
    text: 'Позвоните или напишите: какие работы и по какому договору планируете.',
  },
  {
    number: '02',
    title: 'Разбор',
    text: 'Смотрю договор и документы и говорю, нужна ли СРО и какая.',
  },
  {
    number: '03',
    title: 'Документы',
    // До 01.10.2026 — «Собираю комплект под требования выбранной СРО»:
    // слово в слово первая фраза раздела «Документы» сразу ниже. Здесь —
    // кто что делает на шаге, как в шагах вступления (StepsGrid).
    text: 'Готовлю комплект, вы подписываете и подаёте его в СРО.',
  },
  {
    number: '04',
    title: 'Выписка',
    text: 'Веду переписку с СРО до решения о приёме и выписки из реестра.',
  },
]

export function Process() {
  // null — скрипт ещё не считал прокрутку (готовый HTML) или движение
  // уменьшено: дом достроен, все шаги видны одинаково. -1 — раздел ещё
  // не дошёл до середины экрана: на чертеже только земля.
  const [active, setActive] = useState<number | null>(null)
  const [animate, setAnimate] = useState(false)
  const listRef = useRef<HTMLOListElement>(null)
  const railRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const list = listRef.current
    if (!list || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const items = [...list.querySelectorAll(':scope > li')] as HTMLElement[]
    let frame = 0
    const measure = () => {
      frame = 0
      const line = window.innerHeight * 0.55
      const tops = items.map((el) => el.getBoundingClientRect().top)
      let index = -1
      tops.forEach((top, i) => {
        if (top <= line) index = i
      })
      setActive(index)
      // Шкала — непрерывно, от верха первого шага до верха последнего;
      // меняется только transform, без перерасчёта раскладки.
      const span = tops[tops.length - 1] - tops[0]
      const progress = Math.min(1, Math.max(0, (line - tops[0]) / (span || 1)))
      if (railRef.current) railRef.current.style.transform = `scaleY(${progress})`
    }
    measure()
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(measure)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      cancelAnimationFrame(frame)
    }
  }, [])

  // Переходы включаются только после того, как первая расстановка по месту
  // прокрутки уже на экране (два кадра после неё): иначе готовый дом
  // «стирался» бы на глазах, а при «Назад» на главную под обложкой шло бы
  // движение, которого там быть не должно (test-site.mjs, «Назад» на главную).
  const measured = active !== null
  useEffect(() => {
    if (!measured) return
    let second = 0
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => setAnimate(true))
    })
    return () => {
      cancelAnimationFrame(first)
      cancelAnimationFrame(second)
    }
  }, [measured])

  return (
    <section id="process" className="relative isolate bg-accent-950 py-20 text-neutral-50 sm:py-32">
      <div className="mx-auto w-full max-w-6xl min-[1800px]:max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading dark title="Как проходит работа" />
        {/* До 1024 px чертёж липнет под шапкой сверху, шаги проезжают под ним
            (у него свой графитовый фон и растушёвка снизу); с 1024 px —
            справа, по середине экрана, шаги слева. */}
        <div className="mt-10 sm:mt-14 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-20">
          <div className="sticky top-16 z-10 -mx-4 bg-accent-950 px-4 pb-2 pt-3 after:pointer-events-none after:absolute after:inset-x-0 after:top-full after:h-10 after:bg-gradient-to-b after:from-accent-950 after:to-transparent sm:-mx-6 sm:px-6 lg:order-2 lg:top-[max(5rem,calc(50vh-16rem))] lg:mx-0 lg:self-start lg:bg-transparent lg:p-0 lg:after:hidden">
            <div className="mx-auto h-[min(34vh,17rem)] max-w-full sm:h-[min(36vh,20rem)] lg:h-[32rem]">
              <Blueprint stage={active === null ? STEPS.length : active + 1} animate={animate} />
            </div>
          </div>

          <ol ref={listRef} className="relative mt-6 border-t border-white/15 lg:order-1 lg:mt-0">
            {/* Шкала шагов. Без скрипта и при «уменьшить движение» заполнена
                целиком, как и чертёж. */}
            <div aria-hidden="true" className="pointer-events-none absolute inset-y-0 left-0 w-px bg-white/15">
              <div ref={railRef} className="h-full w-full origin-top bg-accent-400" />
            </div>
            {STEPS.map((step, index) => {
              const dim = active !== null && active >= 0 && index !== active
              const reached = active === null || index <= active
              return (
                <li
                  key={step.number}
                  className="relative min-h-[34vh] border-b border-white/15 py-7 pl-6 last:min-h-0 sm:py-9 sm:pl-9 lg:min-h-[40vh] lg:py-10 lg:pl-10 lg:last:min-h-0"
                >
                  {/* Точка шага на шкале: горит, когда до шага дошли. */}
                  <span
                    aria-hidden="true"
                    className={`absolute -left-[4px] top-[2.4rem] h-[9px] w-[9px] rounded-full border sm:top-[3.25rem] lg:top-[3.5rem] ${
                      reached ? 'border-accent-400 bg-accent-400' : 'border-white/30 bg-accent-950'
                    } ${animate ? 'transition-colors duration-500' : ''}`}
                  />
                  <Reveal delay={index * 120}>
                    <div
                      className={`grid grid-cols-[3.25rem_minmax(0,1fr)] sm:grid-cols-[5rem_minmax(0,1fr)] ${
                        animate ? 'transition-opacity duration-700 ease-silk' : ''
                      }`}
                      style={{ opacity: dim ? 0.6 : 1 }}
                    >
                      <p className="font-display text-[2rem] font-medium leading-none tabular-nums text-accent-300 sm:text-[2.6rem]">
                        {step.number}
                      </p>
                      <div>
                        <h3 className="font-display text-[1.6rem] font-medium leading-none sm:text-[1.9rem] sm:leading-tight">
                          {step.title}
                        </h3>
                        <p className="mt-2.5 max-w-md leading-relaxed text-neutral-300 sm:mt-3">{nbsp(step.text)}</p>
                      </div>
                    </div>
                  </Reveal>
                </li>
              )
            })}
          </ol>
        </div>
      </div>
    </section>
  )
}

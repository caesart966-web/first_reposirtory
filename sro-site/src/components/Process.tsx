import { nbsp } from '../lib/typo'
import { Reveal } from './ui/Reveal'
import { SectionHeading } from './ui/Section'

// Четыре шага работы — тёмный раздел посреди страницы, пауза между
// светлыми блоками.
//
// С 26.09.2026 без фотографии. Здесь стояла Фемида (до того — гравюра), но
// раздел рассказывает про шаги, а символ правосудия ни один шаг не объясняет:
// она переехала в «О нас», где сайт говорит, на чём держится работа. Рисунок
// раздела теперь — сами шаги: четыре в ряд на компьютере, номера крупно
// латунью. Номера здесь по делу: это последовательность.
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
    text: 'Собираю комплект под требования выбранной СРО.',
  },
  {
    number: '04',
    title: 'Выписка',
    text: 'Веду переписку с СРО до решения о приёме и выписки из реестра.',
  },
]

export function Process() {
  return (
    <section id="process" className="relative isolate bg-accent-950 py-20 text-neutral-50 sm:py-32">
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <SectionHeading dark title="Как проходит работа" />
        {/* Телефон — столбик, номер слева от текста (30.09.2026: номер
            отдельной строкой над заголовком растягивал четыре коротких шага
            почти на два экрана); с 640px — сетка 2×2, с 1024px — четыре шага
            в ряд. Номера набраны крупно латунью: без фотографии они и есть
            рисунок раздела. */}
        <ol className="mt-12 grid border-t border-white/15 sm:mt-16 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <li
              key={step.number}
              className="border-b border-white/15 py-6 sm:py-8 sm:odd:border-r sm:odd:pr-8 sm:even:pl-8 sm:[&:nth-child(n+3)]:border-b-0 lg:border-b-0 lg:border-r lg:px-8 lg:py-10 lg:first:pl-0 lg:last:border-r-0 lg:last:pr-0"
            >
              <Reveal delay={index * 120} className="grid grid-cols-[3.5rem_minmax(0,1fr)] sm:block">
                <p className="font-display text-[2rem] font-medium leading-none tabular-nums text-accent-300 sm:text-[2.6rem]">
                  {step.number}
                </p>
                <div>
                  <h3 className="font-display text-[1.6rem] font-medium leading-none sm:mt-8 sm:text-[1.9rem] sm:leading-tight lg:text-[1.6rem] xl:text-[1.9rem]">
                    {step.title}
                  </h3>
                  <p className="mt-2.5 leading-relaxed text-neutral-300 sm:mt-3">{nbsp(step.text)}</p>
                </div>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

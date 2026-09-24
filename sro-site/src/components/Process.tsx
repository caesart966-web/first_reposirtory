import { Reveal } from './ui/Reveal'
import { SectionHeading } from './ui/Section'

// Четыре шага работы — единственный тёмный раздел посреди страницы.
//
// До 24.09.2026 здесь стояла гравюра Фемиды белым штрихом на графите.
// Заказчик попросил её убрать: белый рисунок на чёрном смотрелся бедно
// рядом с его примерами, где Фемида — бронзовая статуя на фотографии.
// Место под такую фотографию — этот раздел; пока её нет, раздел стоит
// без картинки.
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
    <section id="process" className="bg-accent-950 py-24 text-neutral-50 sm:py-32">
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <SectionHeading dark eyebrow="Процесс" title="Как проходит работа" />
        <ol className="mt-16 grid border-t border-white/15 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <li
              key={step.number}
              className="border-b border-white/15 py-8 sm:pr-8 lg:border-b-0 lg:border-r lg:py-10 lg:pl-8 lg:first:pl-0 lg:last:border-r-0"
            >
              <Reveal delay={index * 120}>
                <p className="text-sm tabular-nums text-neutral-400">{step.number}</p>
                <h3 className="mt-10 font-display text-[1.9rem] font-medium leading-tight lg:mt-16">
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

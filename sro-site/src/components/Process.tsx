import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

const STEPS = [
  {
    number: '01',
    title: 'Заявка',
    text: 'Вы рассказываете о задаче — по телефону, в мессенджере или через форму на сайте.',
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
    <Section id="process" size="compact" className="bg-neutral-50/70">
      <SectionHeading eyebrow="Процесс" title="Как проходит работа" />
      <div className="relative mt-12">
        <div
          className="absolute left-0 right-0 top-7 hidden border-t-2 border-dashed border-neutral-200 lg:block"
          aria-hidden="true"
        />
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <Reveal key={step.number} delay={index * 90}>
              <div className="relative">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-accent-200 bg-white text-lg font-bold tabular-nums text-accent-600 shadow-card">
                  {step.number}
                </div>
                <h3 className="mt-5 text-lg font-semibold text-neutral-950">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-neutral-600">{step.text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </Section>
  )
}

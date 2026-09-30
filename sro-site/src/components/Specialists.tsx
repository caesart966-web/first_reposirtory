import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Специалисты НРС — то, обо что чаще всего спотыкаются на входе в СРО.
//
// В FAQ ответ на это есть, но короткий. Здесь варианты названы прямо, все
// три, в деловом тоне: требование закона, потом что делать. Отдельный блок,
// а не строчка в услугах: в «Услугах» НРС и НОК стоят карточками «помогу
// с тем-то», а вопрос у посетителя другой — «у меня их нет, мне можно?».
//
// Тон намеренно ровный, без острот и афоризмов: заказчик попросил, чтобы
// текст читался как написанный специалистом по СРО, а не сочинённый.

const WAYS = [
  {
    title: 'Проверить действующих сотрудников',
    text: 'Бывает, что сотрудник с подходящим образованием и стажем уже работает в компании, но в реестр не внесён. Проверю его дипломы, стаж и должностные обязанности.',
  },
  {
    title: 'Включить своего специалиста в реестр',
    text: 'Для включения в НРС нужны профильное высшее образование, стаж по специальности и действующее свидетельство о независимой оценке квалификации — она обязательна с сентября 2022 года. Подготовлю документы и подам заявление.',
  },
  {
    title: 'Принять в штат специалиста из реестра',
    text: 'Специалист из реестра оформляется по основному месту работы — так требует закон. До оформления проверю его сведения в реестре.',
  },
]

export function Specialists() {
  return (
    <Section id="nrs" className="bg-neutral-100">
      <SectionHeading
        title="Специалисты НРС"
        subtitle="Без двух специалистов в национальном реестре в СРО не принимают. Если своих пока нет, закон оставляет три пути."
      />
      {/* Сначала норма, потом варианты. Иначе получается разговор о способах
          обойти требование, а требование настоящее и никуда не денется.
          Норма — крупной цитатой с латунной чертой: это текст закона, и
          выглядеть он должен иначе, чем мои советы под ним. */}
      <Reveal className="mt-16">
        {/* На телефоне цитата на ступень мельче: в 1,55rem она шла восемью
            строками и занимала весь экран. */}
        <blockquote className="border-l-2 border-accent-500 pl-5 sm:pl-10">
          <p className="text-balance font-display text-[1.3rem] font-medium leading-snug text-neutral-950 min-[380px]:text-[1.4rem] sm:text-[2rem]">
            В штате члена СРО по основному месту работы должно быть не менее двух специалистов
            по организации работ, сведения о которых внесены в национальный реестр
            специалистов (НРС).
          </p>
          <p className="mt-5 max-w-3xl leading-relaxed text-neutral-600">
            Специализация зависит от вида СРО: организация строительства, подготовки проектной
            документации или инженерных изысканий. Работа по совместительству не учитывается.
          </p>
          <p className="mt-4 text-sm text-neutral-600">ст. 55.5-1, ст. 55.6 ГрК РФ</p>
        </blockquote>
      </Reveal>

      <ol className="mt-16 grid gap-10 lg:grid-cols-3 lg:gap-8">
        {WAYS.map((way, index) => (
          <li key={way.title} className="border-t border-neutral-300 pt-6">
            <Reveal delay={index * 90}>
              <p className="text-sm tabular-nums text-neutral-600">Вариант {index + 1}</p>
              <h3 className="mt-4 font-display text-[1.65rem] font-medium leading-tight text-neutral-950">
                {way.title}
              </h3>
              <p className="mt-3 leading-relaxed text-neutral-600">{way.text}</p>
            </Reveal>
          </li>
        ))}
      </ol>

      {/* Оговорка на месте: сайт держится на том, что здесь не обещают
          невозможного. «Аренда» специалиста — первое, что предлагают
          посредники, и об этом стоит сказать самим. */}
      <Reveal delay={80} className="mt-16">
        <div className="rounded-3xl bg-neutral-950 p-7 text-neutral-50 sm:p-10">
          {/* Два предупреждения — каждое со своим заголовком. Общая шапка
              «Что важно учитывать» над ними ничего не говорила. */}
          <div className="grid gap-8 text-neutral-300 lg:grid-cols-2 lg:gap-10">
            <div>
              <h3 className="font-display text-[1.5rem] font-medium text-neutral-50">«Аренда» специалистов</h3>
              <p className="mt-3 leading-relaxed">
                Фиктивное трудоустройство задачу не решает: СРО проверяет соответствие
                требованиям не только при приёме, но и после.
              </p>
            </div>
            <div>
              <h3 className="font-display text-[1.5rem] font-medium text-neutral-50">Срок свидетельства НОК</h3>
              <p className="mt-3 leading-relaxed">
                Свидетельство действует ограниченный срок. Когда он истечёт, специалиста исключат
                из реестра, и компания перестанет соответствовать требованию о двух специалистах.
                При сопровождении слежу за этими сроками.
              </p>
            </div>
          </div>
        </div>
      </Reveal>

      <Reveal delay={120} className="mt-12 flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-xl text-lg text-neutral-700">
          Пришлите документы сотрудника — скажу, подходит ли он для реестра.
        </p>
        <ButtonLink href="#contacts" size="lg" arrow className="shrink-0">
          Проверить сотрудника
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

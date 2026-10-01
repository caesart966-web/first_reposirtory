import { page } from '../lib/site'
import { nbsp } from '../lib/typo'
import { Law, PageLink } from './PageParts'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Специалисты НРС — то, обо что чаще всего спотыкаются на входе в СРО.
//
// Отдельный раздел, а не строчка в услугах: в «Услугах» НРС и НОК стоят
// карточками «помогу с тем-то», а вопрос у посетителя другой — «у меня их
// нет, мне можно?». Поэтому здесь требование и три законных пути.
//
// С 01.10.2026 раздел короткий: требование, норма, три пути названиями
// и строка-переход на страницу «Специалисты НРС». Прежде здесь стояли
// цитата закона, пояснение к каждому пути и тёмная плашка про «аренду»
// специалистов и срок НОК — слово в слово то же, что на странице услуги,
// и главная от этого шла лишний экран. «Аренда» и срок НОК остались там.
//
// Тон намеренно ровный, без острот и афоризмов: заказчик попросил, чтобы
// текст читался как написанный специалистом по СРО, а не сочинённый.

const WAYS = [
  'Проверить действующих сотрудников',
  'Включить своего специалиста в реестр',
  'Принять в штат специалиста из реестра',
]

const NRS_PAGE = 'uslugi/specialisty-nrs'

export function Specialists() {
  return (
    <Section id="nrs" className="bg-neutral-100">
      <SectionHeading
        title="Специалисты НРС"
        subtitle="Без двух специалистов в национальном реестре в СРО не принимают: в штате, по основному месту работы. Если своих пока нет, закон оставляет три пути."
      />
      {/* Норма — под подзаголовком, в его колонке (сетка та же, что
          у SectionHeading): она подтверждает требование, а не заголовок. */}
      <Reveal className="lg:grid lg:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)] lg:gap-16">
        <div className="mt-2 lg:col-start-2">
          <Law>ст. 55.5-1, ст. 55.6 ГрК РФ</Law>
        </div>
      </Reveal>

      {/* Три пути — названиями, без номеров: это не шаги, порядка у них нет.
          На телефоне пути идут строками, и строка-переход встаёт следующей,
          без своей верхней линейки: иначе между двумя линейками оставалась
          пустая полоса, похожая на пропущенную строку. */}
      <ul className="mt-12 grid border-t border-neutral-300 lg:grid-cols-3 lg:gap-8 lg:border-t-0">
        {WAYS.map((way, index) => (
          <li key={way} className="border-b border-neutral-300 py-5 lg:border-b-0 lg:border-t lg:pb-0 lg:pt-6">
            <Reveal delay={index * 90}>
              <h3 className="font-display text-[1.4rem] font-medium leading-tight text-neutral-950 sm:text-[1.65rem]">
                {nbsp(way)}
              </h3>
            </Reveal>
          </li>
        ))}
      </ul>

      <Reveal>
        <PageLink
          href={page(NRS_PAGE)}
          text="Что нужно для реестра, «аренда» специалистов и срок НОК"
          to="Специалисты НРС"
          className="border-t-0 lg:mt-12 lg:border-t"
        />
      </Reveal>

      <Reveal delay={120} className="mt-12 flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-xl text-lg text-neutral-700">
          {nbsp('Пришлите документы сотрудника — скажу, подходит ли он для реестра.')}
        </p>
        <ButtonLink href="#contacts" size="lg" arrow className="shrink-0">
          Проверить сотрудника
        </ButtonLink>
      </Reveal>
    </Section>
  )
}

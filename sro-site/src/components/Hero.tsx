import { ChevronRight, Phone } from 'lucide-react'
import { LINKS } from '../content/contacts'
import { BlueprintGrid } from './illustrations'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'

// Первый экран без карточки квиза.
//
// Она стояла здесь и показывала первый вопрос — ровно тот же, с которого
// начинается сам квиз внизу страницы. Посетитель, доскроллив, видел один и тот
// же вопрос второй раз. Точку входа это не усиливало: сразу под героем идут
// «Виды СРО» — те же три карточки с фотографиями, которые тоже заводят квиз,
// только узнаваемо, а не списком вариантов.
//
// Поэтому герой стал тем, чем должен быть: заголовок, суть, два действия.
// Колонки убраны, блок по центру — так он занимает меньше высоты, и карточки
// видов попадают на первый экран, а не уезжают под сгиб.
export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
        {/* Белая вуаль поверх фоновой гравюры: на первом экране уже работают
            сетка чертежа и два размытых пятна, третий фоновый мотив под ними
            даёт грязь. Ниже первого экрана Фемида проступает в полную силу. */}
        <div className="absolute inset-0 bg-white/75" />
        <div className="absolute -top-32 right-[-10%] h-[420px] w-[420px] rounded-full bg-accent-100/60 blur-3xl" />
        <div className="absolute bottom-[-30%] left-[-10%] h-[360px] w-[360px] rounded-full bg-accent-50 blur-3xl" />
        <BlueprintGrid className="absolute inset-0 h-full w-full text-accent-400/25" />
      </div>

      <div className="mx-auto w-full max-w-6xl px-4 pb-10 pt-10 sm:px-6 sm:pb-14 sm:pt-14 lg:px-8">
        <Reveal className="mx-auto max-w-3xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-600">
            СРО · НРС · НОК · Документы · Сопровождение
          </p>
          <h1 className="mt-5 text-4xl font-bold leading-[1.08] tracking-tight text-neutral-950 sm:text-5xl lg:text-[3.4rem]">
            Помогу вступить в <span className="text-accent-600">СРО</span> без лишней переписки
            и&nbsp;ошибок в&nbsp;документах
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-neutral-600">
            Подберу СРО, проверю документы, подготовлю необходимые материалы и лично сопровожу
            процесс.
          </p>
          {/* Кнопка подбора видна и на телефоне: раньше её прятали, потому что
              карточка с тем же вопросом стояла сразу под ней. Карточки больше
              нет, и прятать нечего. */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <ButtonLink href="#types" size="lg">
              Подобрать СРО за 1 минуту
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </ButtonLink>
            <ButtonLink href={LINKS.tel} variant="secondary" size="lg">
              <Phone className="h-4 w-4" aria-hidden="true" />
              Позвонить
            </ButtonLink>
          </div>
          {/* «Стоимость обсуждаем до начала работы» отсюда убрано: ровно это
              написано в подзаголовке «Стоимости», а место в строке занял
              главный довод — консультация ничего не стоит. */}
          <p className="mt-6 text-sm text-neutral-600">
            Консультация бесплатная · Работаю по договору · Конфиденциально
          </p>
        </Reveal>
      </div>
    </section>
  )
}

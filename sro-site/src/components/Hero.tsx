import { ChevronRight, Phone } from 'lucide-react'
import { LINKS } from '../content/contacts'
import { IMAGES } from '../content/images'
import { BlueprintGrid } from './illustrations'
import { ButtonLink } from './ui/Button'
import { Figure } from './ui/Figure'
import { anchor } from '../lib/site'
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
//
// Затем заказчик попросил первый экран «красивее и профессиональнее», но без
// портрета — публиковать лицо он не будет. Экран стал двухколонным: текст
// слева, справа его же фотография рабочего стола в фирменном дуотоне. Кадр
// уже стоит фоном под квизом; здесь он в полную силу, там — приглушён под
// плёнкой. Страница им открывается и закрывается, в середине его нет.
//
// Заголовок в колонке уже, чем был по центру, поэтому на lg его кегль ниже
// (2.9rem против 3.4rem): иначе он ломался на пять строк.
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

      <div className="mx-auto w-full max-w-6xl px-4 pb-12 pt-10 sm:px-6 sm:pb-16 sm:pt-14 lg:px-8">
        <div className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14">
          <Reveal className="text-center lg:text-left">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-600">
              СРО · НРС · НОК · Документы · Сопровождение
            </p>
            <h1 className="mt-5 text-4xl font-bold leading-[1.08] tracking-tight text-neutral-950 sm:text-5xl lg:text-[2.9rem]">
              Помогу вступить в <span className="text-accent-600">СРО</span> без лишней переписки
              и&nbsp;ошибок в&nbsp;документах
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-neutral-600 lg:mx-0">
              Подберу СРО, проверю документы, подготовлю необходимые материалы и лично сопровожу
              процесс.
            </p>
            {/* Кнопка подбора видна и на телефоне: раньше её прятали, потому что
                карточка с тем же вопросом стояла сразу под ней. Карточки больше
                нет, и прятать нечего. */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
              <ButtonLink href={anchor('#types')} size="lg">
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

          {/* Подложка со сдвигом вниз-вправо даёт кадру глубину фирменным
              цветом — вместо тени, которая на светлом фоне читалась бы грязью.
              Кадр грузится сразу (priority): это самый большой элемент первого
              экрана, и ленивый он ронял бы оценку скорости. */}
          <Reveal delay={120} className="relative mx-auto w-full max-w-xl lg:max-w-none">
            <div
              className="absolute inset-0 translate-x-4 translate-y-4 rounded-2xl bg-accent-100/80"
              aria-hidden="true"
            />
            <Figure {...IMAGES.hero} priority className="relative" />
          </Reveal>
        </div>
      </div>
    </section>
  )
}

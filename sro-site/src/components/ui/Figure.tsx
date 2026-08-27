import type { ReactNode } from 'react'

// Один компонент на все фотослоты страницы: иначе у четырёх картинок из четырёх
// мест разъедутся скругления, рамки и отступы.
//
// width/height обязательны и передаются реальными: без них браузер не знает
// пропорцию до загрузки, вёрстка прыгает, и Lighthouse снимает баллы за CLS.
// В спецификации ТЗ этих полей в списке пропсов нет, но требование «обязательные
// width/height» есть — держим их явными, чтобы значение нельзя было забыть.
//
// AVIF подключается через <source>: если srcAvif не передан, остаётся один
// <img>, и это рабочее состояние, а не ошибка.
//
// fetchPriority здесь нет намеренно: React 18 такого пропса не знает, роняет
// его и пишет предупреждение в консоль. Приоритет задаётся через loading.
type FigureProps = {
  src: string // './img/design.webp'
  srcAvif?: string // './img/design.avif'
  alt: string // осмысленный, не «картинка»
  width: number
  height: number
  caption?: ReactNode
  ratio?: string // 'aspect-[4/3]' | 'aspect-[20/7]'
  // cover обрезает кадр под рамку — так и надо фотографии. Вырезанному объекту
  // на прозрачном фоне (весы, печать) обрезка отрубает края, поэтому ему contain.
  fit?: 'cover' | 'contain'
  // frame=false — для вырезанных объектов: рамка с фоном превращала прозрачный
  // объект в «серую плашку», которая читалась как незагрузившаяся картинка.
  // Без рамки объект стоит прямо на фоне секции, как гравюра Фемиды.
  frame?: boolean
  priority?: boolean // true только для первого экрана
  className?: string
}

export function Figure({
  src,
  srcAvif,
  alt,
  width,
  height,
  caption,
  ratio = 'aspect-[4/3]',
  fit = 'cover',
  frame = true,
  priority = false,
  className = '',
}: FigureProps) {
  return (
    <figure className={className}>
      <div
        className={
          frame
            ? `overflow-hidden rounded-2xl border border-neutral-200/80 bg-neutral-100 ${ratio}`
            : ratio
        }
      >
        <picture>
          {srcAvif && <source type="image/avif" srcSet={srcAvif} />}
          <img
            src={src}
            alt={alt}
            width={width}
            height={height}
            loading={priority ? 'eager' : 'lazy'}
            decoding="async"
            className={`h-full w-full ${fit === 'contain' ? 'object-contain' : 'object-cover'}`}
          />
        </picture>
      </div>
      {caption && <figcaption className="mt-3 text-sm text-neutral-600">{caption}</figcaption>}
    </figure>
  )
}

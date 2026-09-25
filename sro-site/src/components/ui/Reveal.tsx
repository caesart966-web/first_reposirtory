import {
  Fragment,
  createElement,
  useEffect,
  useRef,
  type CSSProperties,
  type ElementType,
  type ReactNode,
} from 'react'
import { nbsp } from '../../lib/typo'

// Появление при прокрутке: блок выплывает, заголовок поднимается по словам.
// Сами переходы — в index.css (.reveal, .reveal-words), здесь только момент
// запуска. Шторка для фотографий (RevealImage) снята 25.09.2026 вместе
// с последней фотографией в рамке: кадры разделов теперь стоят фоном
// и въезжают по прокрутке (.scroll-settle).
//
// Запуск — когда верх блока заходит в нижние 90% экрана, а не когда видно
// 15% его площади, как было. Прежнее правило на высоких блоках не
// срабатывало никогда: карточка политики на телефоне выше экрана в несколько
// раз, и 15% её площади в окно не помещаются — текст оставался прозрачным.
function useReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.classList.add('is-visible')
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            el.classList.add('is-visible')
            observer.disconnect()
          }
        }
      },
      { threshold: 0, rootMargin: '0px 0px -10% 0px' },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return ref
}

export function Reveal({
  children,
  delay = 0,
  className = '',
}: {
  children: ReactNode
  delay?: number
  className?: string
}) {
  const ref = useReveal<HTMLDivElement>()
  const style: CSSProperties | undefined = delay ? { transitionDelay: `${delay}ms` } : undefined
  return (
    <div ref={ref} className={`reveal ${className}`} style={style}>
      {children}
    </div>
  )
}

/**
 * Заголовок, который поднимается по словам из-под маски.
 *
 * Принимает только строку: слова режутся по пробелам, и каждое получает свою
 * ступеньку задержки. Неразрывный пробел ( ) слова не делит — «в СРО»,
 * «под ключ» так и едут парой, как и стоят в строке.
 *
 * Скринридер читает фразу целиком из aria-label, а не по кусочкам.
 */
export function RevealText({
  as = 'h2',
  text,
  className = '',
}: {
  as?: ElementType
  text: string
  className?: string
}) {
  const ref = useReveal<HTMLElement>()
  // Короткие предлоги склеены со следующим словом (nbsp) и попадают с ним
  // в один блок: иначе «в» висело в конце строки («по вступлению в / СРО»).
  const words = nbsp(text).split(' ')
  return createElement(
    as,
    { ref, className: `reveal-words ${className}`, 'aria-label': text },
    // Пробел между словами стоит СНАРУЖИ обрезающего блока: внутри
    // inline-block конечный пробел схлопывается, и слова слипаются.
    words.map((word, i) => (
      <Fragment key={i}>
        <span className="w" aria-hidden="true">
          <span style={{ '--i': i } as CSSProperties}>{word}</span>
        </span>
        {i < words.length - 1 ? ' ' : null}
      </Fragment>
    )),
  )
}

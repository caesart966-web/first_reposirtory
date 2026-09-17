import { X } from 'lucide-react'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { LEGAL_PAGE, legalDoc, type LegalBlock, type LegalDocId } from '../content/legal'
import { page } from '../lib/site'

export type { LegalDocId }

const LegalContext = createContext<(doc: LegalDocId) => void>(() => {})

export function useLegalDocs() {
  return useContext(LegalContext)
}

/** Адрес документа на постоянной странице: /politika-konfidencialnosti/#politika. */
export const legalHref = (doc: LegalDocId) =>
  `${page(LEGAL_PAGE)}#${doc === 'privacy' ? 'politika' : 'soglasie'}`

function Block({ block }: { block: LegalBlock }) {
  if (typeof block === 'string') return <p>{block}</p>
  return (
    <ul className="space-y-2 pl-5">
      {block.list.map((item) => (
        // Маркер — точка того же цвета, что акценты страницы: список должен
        // читаться перечнем, а не сплошным текстом с отступом.
        <li key={item} className="relative before:absolute before:-left-4 before:top-[0.6em] before:h-1.5 before:w-1.5 before:rounded-full before:bg-accent-300">
          {item}
        </li>
      ))}
    </ul>
  )
}

/**
 * Текст документа. Один и тот же вывод и в окне из формы заявки, и на
 * постоянной странице — второй копии текста на сайте нет.
 */
export function LegalDocBody({ doc }: { doc: LegalDocId }) {
  const { lead, sections } = legalDoc(doc)
  return (
    <div className="space-y-7 text-sm leading-relaxed text-neutral-700">
      <p className="text-neutral-500">{lead}</p>
      {sections.map((section) => (
        <section key={section.title} className="space-y-3">
          <h3 className="text-sm font-bold text-neutral-950">{section.title}</h3>
          {section.blocks.map((block, i) => (
            <Block key={i} block={block} />
          ))}
        </section>
      ))}
    </div>
  )
}

export function LegalProvider({ children }: { children: ReactNode }) {
  const [doc, setDoc] = useState<LegalDocId | null>(null)
  const closeButtonRef = useRef<HTMLButtonElement | null>(null)
  const lastFocused = useRef<HTMLElement | null>(null)

  const open = useCallback((next: LegalDocId) => {
    lastFocused.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    setDoc(next)
  }, [])

  const close = useCallback(() => {
    setDoc(null)
    lastFocused.current?.focus()
  }, [])

  useEffect(() => {
    if (!doc) return
    closeButtonRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [doc, close])

  return (
    <LegalContext.Provider value={open}>
      {children}
      {doc && (
        <div
          className="fixed inset-0 z-[60] flex items-end justify-center bg-neutral-950/40 sm:items-center sm:p-6"
          onClick={close}
          role="presentation"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="legal-doc-title"
            onClick={(event) => event.stopPropagation()}
            className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-t-3xl bg-white p-6 shadow-card-hover sm:rounded-3xl sm:p-8"
          >
            <div className="flex items-start justify-between gap-4">
              <h2 id="legal-doc-title" className="text-xl font-bold text-neutral-950">
                {legalDoc(doc).title}
              </h2>
              <button
                ref={closeButtonRef}
                type="button"
                onClick={close}
                aria-label="Закрыть"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-neutral-200 text-neutral-600 transition hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
            <div className="mt-5">
              <LegalDocBody doc={doc} />
            </div>
            {/* Постоянный адрес документа: из окна его не скопировать и не
                отправить, а именно это просят, когда документ нужен на руки. */}
            <a
              href={legalHref(doc)}
              className="mt-7 inline-block text-sm font-medium text-accent-700 underline-offset-4 transition hover:text-accent-800 hover:underline"
            >
              Открыть отдельной страницей
            </a>
          </div>
        </div>
      )}
    </LegalContext.Provider>
  )
}

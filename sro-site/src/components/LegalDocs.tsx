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
import { CONTACTS } from '../content/contacts'

export type LegalDocId = 'privacy' | 'consent'

const LegalContext = createContext<(doc: LegalDocId) => void>(() => {})

export function useLegalDocs() {
  return useContext(LegalContext)
}

const TITLES: Record<LegalDocId, string> = {
  privacy: 'Политика конфиденциальности',
  consent: 'Согласие на обработку персональных данных',
}

// Шаблонные тексты: перед публикацией сайта их нужно заменить
// финальными редакциями документов.
function DocBody({ doc }: { doc: LegalDocId }) {
  if (doc === 'privacy') {
    return (
      <div className="space-y-4 text-sm leading-relaxed text-neutral-700">
        <p>
          Настоящая политика описывает, как {CONTACTS.fullName} (далее — Оператор) обрабатывает
          персональные данные посетителей сайта.
        </p>
        <p>
          <span className="font-semibold">Какие данные обрабатываются:</span> имя, номер
          телефона, адрес электронной почты, а также сведения, которые вы указываете в форме
          заявки.
        </p>
        <p>
          <span className="font-semibold">Цель обработки:</span> связь с вами по вашей заявке
          и консультирование по услугам.
        </p>
        <p>
          Данные не передаются третьим лицам, за исключением случаев, предусмотренных
          законодательством Российской Федерации.
        </p>
        <p>
          Вы можете отозвать согласие на обработку и запросить удаление данных, написав на{' '}
          {CONTACTS.email}.
        </p>
        <p>
          <span className="font-semibold">Срок обработки:</span> до достижения цели обработки
          или до отзыва согласия — в зависимости от того, что наступит раньше.
        </p>
        <p>
          <span className="font-semibold">Ваши права:</span> получить сведения об обработке
          своих данных, потребовать их уточнения, блокирования или удаления, отозвать согласие,
          обжаловать действия Оператора в Роскомнадзоре или в суде.
        </p>
        <p>
          Обработка персональных данных ведётся в соответствии с Федеральным законом от
          27.07.2006 № 152-ФЗ «О персональных данных».
        </p>
      </div>
    )
  }
  return (
    <div className="space-y-4 text-sm leading-relaxed text-neutral-700">
      <p>
        Отправляя форму на сайте, вы даёте согласие {CONTACTS.fullName} на обработку указанных вами
        персональных данных: имени, номера телефона и адреса электронной почты.
      </p>
      <p>
        Цель обработки — связь с вами по вашей заявке и консультирование по услугам. Согласие
        действует до его отзыва.
      </p>
      <p>Отозвать согласие можно в любой момент, написав на {CONTACTS.email}.</p>
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
                {TITLES[doc]}
              </h2>
              <button
                ref={closeButtonRef}
                type="button"
                onClick={close}
                aria-label="Закрыть"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-neutral-200 text-neutral-600 transition hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
            <p className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Это шаблон документа: в нём ещё нет реквизитов оператора персональных данных
              (правовой статус, ИНН, ОГРНИП, адрес). Перед публикацией сайта на своём домене
              его нужно заменить финальной редакцией.
            </p>
            <div className="mt-5">
              <DocBody doc={doc} />
            </div>
          </div>
        </div>
      )}
    </LegalContext.Provider>
  )
}

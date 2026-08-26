import { CONFIGURED, CONTACTS, LINKS, externalLinkProps } from '../content/contacts'
import { useLegalDocs } from './LegalDocs'

export function Footer() {
  const openLegal = useLegalDocs()
  return (
    <footer className="border-t border-neutral-200 bg-neutral-50/70">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-10 md:flex-row md:justify-between">
          <div>
            <p className="font-bold text-neutral-950">{CONTACTS.fullName}</p>
            <p className="mt-1 text-sm text-neutral-500">{CONTACTS.role}</p>
            <p className="mt-4 text-sm text-neutral-500">
              Вступление в СРО во всех регионах России
            </p>
          </div>
          <div className="grid gap-8 sm:grid-cols-2 md:gap-16">
            <div>
              <p className="text-sm font-semibold text-neutral-900">Контакты</p>
              <ul className="mt-3 space-y-2 text-sm text-neutral-600">
                <li>
                  <a href={LINKS.tel} className="transition hover:text-accent-700">
                    Телефон: {CONTACTS.phone}
                  </a>
                </li>
                <li>
                  <a href={LINKS.mail} className="transition hover:text-accent-700">
                    E-mail: {CONTACTS.email}
                  </a>
                </li>
                <li>
                  <a
                    href={LINKS.whatsapp}
                    {...externalLinkProps(CONFIGURED.whatsapp)}
                    className="transition hover:text-accent-700"
                  >
                    WhatsApp
                  </a>
                </li>
                <li>
                  <a
                    href={LINKS.telegram}
                    {...externalLinkProps(CONFIGURED.telegram)}
                    className="transition hover:text-accent-700"
                  >
                    Telegram
                  </a>
                </li>
                <li>
                  <a
                    href={LINKS.max}
                    {...externalLinkProps(CONFIGURED.max)}
                    className="transition hover:text-accent-700"
                  >
                    MAX
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-900">Документы</p>
              <ul className="mt-3 space-y-2 text-sm text-neutral-600">
                {/* Открывают шаблонные тексты; замените их финальными редакциями */}
                <li>
                  <button
                    type="button"
                    onClick={() => openLegal('privacy')}
                    className="text-left transition hover:text-accent-700"
                  >
                    Политика конфиденциальности
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={() => openLegal('consent')}
                    className="text-left transition hover:text-accent-700"
                  >
                    Согласие на обработку персональных данных
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div className="mt-10 border-t border-neutral-200 pt-6 text-sm text-neutral-500">
          © {new Date().getFullYear()} {CONTACTS.fullName} · {CONTACTS.role}
        </div>
      </div>
    </footer>
  )
}

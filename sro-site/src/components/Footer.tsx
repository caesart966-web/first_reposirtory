import { Mail, Phone } from 'lucide-react'
import { CONFIGURED, CONTACTS, LINKS } from '../content/contacts'
import { SECTIONS } from '../content/nav'
import { ScalesMark } from './illustrations'
import { useLegalDocs } from './LegalDocs'

export function Footer() {
  const openLegal = useLegalDocs()

  return (
    <footer className="border-t border-neutral-200 bg-neutral-50/55">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1.9fr)] lg:gap-16">
          <div>
            {/* Тот же знак, что в шапке: подвал — вторая точка, где страница
                называет себя, и называть себя дважды по-разному незачем. */}
            <div className="flex items-center gap-2.5">
              <ScalesMark className="h-[22px] w-auto shrink-0 text-accent-600" />
              <span className="flex flex-col leading-tight">
                <span className="font-bold text-neutral-950">{CONTACTS.fullName}</span>
                {/* neutral-600, а не neutral-500 как в шапке: там подпись лежит
                    на белом, а здесь под ней ещё и фоновая гравюра Фемиды. Над
                    самой тёмной её точкой контраст neutral-500 падает до
                    4.39:1 при норме 4.5 — замерено на странице, а не по
                    заливке секции (по одной заливке вышло бы 4.62:1, и ошибку
                    было бы не видно). */}
                <span className="text-xs text-neutral-600">{CONTACTS.role}</span>
              </span>
            </div>
            <p className="mt-4 text-sm text-neutral-600">
              Вступление в СРО во всех регионах России: строительство, проектирование, инженерные
              изыскания.
            </p>
            <p className="mt-3 text-sm font-medium text-accent-700">Консультация бесплатная</p>
          </div>

          <div className="grid gap-8 sm:grid-cols-3 sm:gap-10">
            <div>
              <p className="text-sm font-semibold text-neutral-900">Разделы</p>
              <ul className="mt-3 space-y-2 text-sm text-neutral-600">
                {SECTIONS.map((section) => (
                  <li key={section.href}>
                    <a href={section.href} className="transition hover:text-accent-700">
                      {section.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            {/* Колонка целиком условная: заголовок над пустотой — та же ошибка,
                что и в «Контактах», и лечится так же. */}
            {(CONFIGURED.phone || CONFIGURED.email) && (
            <div>
              <p className="text-sm font-semibold text-neutral-900">Связь</p>
              <ul className="mt-3 space-y-2 text-sm text-neutral-600">
                {CONFIGURED.phone && (
                  <li>
                    <a
                      href={LINKS.tel}
                      className="inline-flex items-center gap-2 transition hover:text-accent-700"
                    >
                      <Phone className="h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                      {CONTACTS.phone}
                    </a>
                  </li>
                )}
                {CONFIGURED.email && (
                  <li>
                    <a
                      href={LINKS.mail}
                      className="inline-flex items-start gap-2 transition hover:text-accent-700"
                    >
                      <Mail
                        className="mt-0.5 h-4 w-4 shrink-0 text-accent-600"
                        aria-hidden="true"
                      />
                      <span className="min-w-0 break-all">{CONTACTS.email}</span>
                    </a>
                  </li>
                )}
              </ul>
              {/* Иконок мессенджеров здесь больше нет: они повторяли плитки
                  из секции «Контакты» один в один. Телефон и почта в подвале —
                  норма, за остальным ведёт ссылка. */}
              <a
                href="#contacts"
                className="mt-3 inline-block text-sm text-neutral-600 transition hover:text-accent-700"
              >
                Все способы связи →
              </a>
            </div>
            )}

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

        <div className="mt-10 flex flex-col gap-2 border-t border-neutral-200 pt-6 text-sm text-neutral-600 sm:flex-row sm:items-center sm:justify-between">
          <p>
            © {new Date().getFullYear()} {CONTACTS.fullName} · {CONTACTS.role}
          </p>
          {/* Цен на странице нет, сроков тоже — оговорка про оферту это
              фиксирует, а не прикрывает. */}
          <p>Информация на сайте не является публичной офертой.</p>
        </div>
      </div>
    </footer>
  )
}

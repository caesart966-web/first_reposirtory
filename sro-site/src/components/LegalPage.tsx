import { ArrowLeft } from 'lucide-react'
import { LEGAL_REVISED } from '../content/legal'
import { REQUISITES } from '../content/facts'
import { home } from '../lib/site'
import { useHashScroll } from '../lib/useHashScroll'
import { Footer } from './Footer'
import { Header } from './Header'
import { LegalDocBody, LegalProvider } from './LegalDocs'
import { MobileBar } from './MobileBar'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'

// Страница с документами о персональных данных: постоянный адрес, который
// можно скопировать, отправить и указать в уведомлении в Роскомнадзор.
//
// Тексты те же, что в окне из формы заявки, — источник один, content/legal.ts.
// Окно осталось намеренно: посетитель читает документ, не бросая наполовину
// заполненную форму. А ссылки в подвале ведут сюда: документ, открывающийся
// только всплывающим окном, нельзя ни переслать, ни сослаться на него.
//
// Два документа на одной странице, а не на двух: их читают вместе, и оба
// короткие для отдельного адреса. Каждый под своим якорем — /#politika
// и /#soglasie.
const DOCS = [
  { id: 'privacy', anchor: 'politika', title: 'Политика конфиденциальности' },
  { id: 'consent', anchor: 'soglasie', title: 'Согласие на обработку персональных данных' },
] as const

export function LegalPage() {
  useHashScroll()

  return (
    <LegalProvider>
      <div id="top" className="relative">
        <Header />
        <main>
          <Section size="compact" className="bg-accent-50/60">
            <Reveal>
              <a
                href={home()}
                className="inline-flex items-center gap-1.5 text-sm font-medium text-accent-700 transition hover:text-accent-800"
              >
                <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden="true" />
                На главную
              </a>
              <h1 className="mt-6 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
                Обработка персональных данных
              </h1>
              <p className="mt-5 max-w-3xl text-lg text-neutral-600">
                Здесь опубликованы два документа: политика конфиденциальности и текст согласия,
                которое вы даёте, отправляя форму заявки на сайте. Оператор персональных данных —{' '}
                {REQUISITES.legalName}, ИНН {REQUISITES.inn}, ОГРН {REQUISITES.ogrn}.
              </p>
              {/* Оглавление: документ длинный, и к нужному месту надо попадать
                  сразу, а не прокруткой. */}
              <ul className="mt-7 flex flex-wrap gap-3">
                {DOCS.map((doc) => (
                  <li key={doc.anchor}>
                    <a
                      href={`#${doc.anchor}`}
                      className="inline-flex rounded-xl border border-accent-200 bg-white px-4 py-2 text-sm font-medium text-accent-800 transition hover:border-accent-300 hover:bg-accent-50"
                    >
                      {doc.title}
                    </a>
                  </li>
                ))}
              </ul>
              <p className="mt-6 text-sm text-neutral-500">Редакция от {LEGAL_REVISED}.</p>
            </Reveal>
          </Section>

          <Section>
            {/* Уже основной сетки: строка в 110 знаков читается тяжело, а
                документ и так длинный. Ограничение по ширине — единственная
                вольность вёрстки, которую здесь стоит себе позволить. */}
            <div className="mx-auto max-w-4xl space-y-10">
              {DOCS.map((doc) => (
                // scroll-mt — поправка на фиксированную шапку: без неё якорь
                // ставит заголовок ровно под неё, и раздел начинается за краем.
                <section key={doc.id} id={doc.anchor} className="scroll-mt-24">
                  {/* Без Reveal — и это не упущение. Появление по прокрутке
                      срабатывает, когда в окне оказывается 15% блока, а
                      карточка документа выше экрана в несколько раз: на
                      телефоне пятнадцати процентов не наберётся никогда, и
                      текст остался бы прозрачным навсегда. Проверка legal.mjs
                      смотрит именно на видимость, а не на наличие текста в
                      разметке: невидимый текст в innerText есть. */}
                  <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-card sm:p-9">
                    <h2 className="text-2xl font-bold tracking-tight text-neutral-950">
                      {doc.title}
                    </h2>
                    <div className="mt-6">
                      <LegalDocBody doc={doc.id} />
                    </div>
                  </div>
                </section>
              ))}
            </div>
          </Section>

          <Section size="compact" className="pb-16">
            <Reveal className="flex flex-wrap gap-3">
              <ButtonLink href={home()} size="lg">
                На главную
              </ButtonLink>
            </Reveal>
          </Section>
        </main>
        <Footer />
        <div
          className="md:hidden"
          style={{ height: 'calc(4rem + env(safe-area-inset-bottom))' }}
          aria-hidden="true"
        />
        <MobileBar />
      </div>
    </LegalProvider>
  )
}

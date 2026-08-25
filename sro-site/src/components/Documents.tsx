import { CheckCircle2 } from 'lucide-react'
import { DraftingTools } from './illustrations'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'
import { Section } from './ui/Section'

const DOCUMENTS = [
  { title: 'Заявление', text: 'по форме выбранной СРО' },
  { title: 'Регистрационные документы', text: 'ОГРН / ОГРНИП, ИНН, устав' },
  { title: 'Документы организации', text: 'сведения о компании и руководителе' },
  { title: 'Документы специалистов', text: 'дипломы, подтверждение стажа' },
  { title: 'Документы НРС', text: 'подтверждение включения специалистов в реестр' },
  { title: 'Сведения о квалификации', text: 'удостоверения о повышении квалификации, НОК' },
  { title: 'Дополнительные документы', text: 'по требованиям конкретной СРО' },
]

export function Documents() {
  return (
    <Section id="documents">
      <div className="grid items-center gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-14">
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent-600">
            Документы
          </p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
            Подготовлю пакет документов для вступления в СРО
          </h2>
          <p className="mt-5 text-lg text-neutral-600">
            Соберу комплект под требования конкретной СРО и проверю каждый документ до подачи —
            чтобы снизить риск замечаний и возвратов.
          </p>
          <ButtonLink href="#quiz" size="lg" className="mt-7">
            Проверить мои документы
          </ButtonLink>
          <DraftingTools className="mt-10 hidden h-auto w-full max-w-sm text-accent-500/40 lg:block" />
        </Reveal>
        <Reveal delay={100}>
          <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-card sm:p-8">
            <p className="text-sm font-semibold uppercase tracking-wider text-neutral-500">
              Что войдёт в пакет
            </p>
            <ul className="mt-5 space-y-3.5">
              {DOCUMENTS.map((doc) => (
                <li key={doc.title} className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-accent-600" aria-hidden="true" />
                  <p className="text-neutral-800">
                    <span className="font-medium">{doc.title}</span>
                    <span className="text-neutral-500"> — {doc.text}</span>
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
      </div>
    </Section>
  )
}

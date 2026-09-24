import { IMAGES } from '../content/images'
import { ButtonLink } from './ui/Button'
import { Figure } from './ui/Figure'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

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
      <div className="grid gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-20">
        <div>
          <SectionHeading eyebrow="Документы" title="Подготовлю пакет документов для вступления в СРО" />
          <Reveal delay={120}>
            <p className="mt-7 text-lg leading-relaxed text-neutral-600">
              Соберу комплект под требования конкретной СРО и проверю каждый документ до
              подачи — чтобы снизить риск замечаний и возвратов.
            </p>
            <ButtonLink href="#contacts" size="lg" arrow className="mt-9">
              Проверить мои документы
            </ButtonLink>
          </Reveal>
          <Figure {...IMAGES.documents} className="mt-12 max-w-md" />
        </div>
        {/* Перечень — строками с тонкими линейками, как опись в деле, а не
            галочками в карточке: галочки означают «сделано», а это список
            того, что войдёт в пакет. */}
        <div className="lg:pt-24">
          <Reveal>
            <p className="text-sm text-neutral-600">Что войдёт в пакет</p>
          </Reveal>
          <ol className="mt-5 border-t border-neutral-300">
            {DOCUMENTS.map((doc, index) => (
              <li key={doc.title} className="border-b border-neutral-300">
                <Reveal delay={index * 60} className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-2 py-5">
                  <span className="pt-0.5 text-sm tabular-nums text-neutral-500">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <p className="text-neutral-950">
                    <span className="font-medium">{doc.title}</span>
                    <span className="text-neutral-600"> — {doc.text}</span>
                  </p>
                </Reveal>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </Section>
  )
}

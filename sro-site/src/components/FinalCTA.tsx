import { Phone } from 'lucide-react'
import { LINKS } from '../content/contacts'
import { CitySkyline } from './illustrations'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'

export function FinalCTA() {
  return (
    <section className="relative overflow-hidden bg-accent-950">
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute -top-24 left-1/2 h-[380px] w-[640px] -translate-x-1/2 rounded-full bg-accent-600/25 blur-3xl" />
      </div>
      {/* Панорама стройки — только у нижней кромки, под контентом */}
      <CitySkyline className="pointer-events-none absolute inset-x-0 bottom-0 h-20 w-full text-white/[0.09] sm:h-28" />
      <div className="relative mx-auto w-full max-w-6xl px-4 pb-32 pt-16 text-center sm:px-6 sm:pb-44 sm:pt-20 lg:px-8">
        <Reveal>
          <h2 className="mx-auto max-w-3xl text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Расскажите, какая задача стоит перед вашей компанией
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-accent-100/80">
            Помогу понять, что необходимо сделать именно в вашей ситуации.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <ButtonLink href="#quiz" variant="inverse" size="lg">
              Получить консультацию
            </ButtonLink>
            <ButtonLink href={LINKS.tel} variant="outlineInverse" size="lg">
              <Phone className="h-4 w-4" aria-hidden="true" />
              Позвонить
            </ButtonLink>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

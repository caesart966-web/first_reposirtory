import { MessageCircle, Phone, Send } from 'lucide-react'
import { CONFIGURED, LINKS, externalLinkProps } from '../content/contacts'
import { CitySkyline } from './illustrations'
import { ButtonLink } from './ui/Button'
import { Reveal } from './ui/Reveal'

export function FinalCTA() {
  return (
    <section className="relative overflow-hidden bg-accent-950 py-16 sm:py-20">
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute -top-24 left-1/2 h-[380px] w-[640px] -translate-x-1/2 rounded-full bg-accent-600/25 blur-3xl" />
        {/* Панорама стройки по нижней кромке секции */}
        <CitySkyline className="absolute inset-x-0 bottom-0 h-32 w-full text-white/[0.16] sm:h-40" />
      </div>
      <div className="relative mx-auto w-full max-w-6xl px-4 text-center sm:px-6 lg:px-8">
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
            <ButtonLink
              href={LINKS.whatsapp}
              variant="outlineInverse"
              size="lg"
              {...externalLinkProps(CONFIGURED.whatsapp)}
            >
              <MessageCircle className="h-4 w-4" aria-hidden="true" />
              WhatsApp
            </ButtonLink>
            <ButtonLink
              href={LINKS.max}
              variant="outlineInverse"
              size="lg"
              {...externalLinkProps(CONFIGURED.max)}
            >
              <Send className="h-4 w-4" aria-hidden="true" />
              MAX
            </ButtonLink>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

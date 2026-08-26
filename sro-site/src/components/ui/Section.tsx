import type { ReactNode } from 'react'
import { Reveal } from './Reveal'

export function Section({
  id,
  className = '',
  children,
}: {
  id?: string
  className?: string
  children: ReactNode
}) {
  return (
    <section id={id} className={`py-14 sm:py-20 ${className}`}>
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">{children}</div>
    </section>
  )
}

export function SectionHeading({
  eyebrow,
  title,
  subtitle,
  dark = false,
}: {
  eyebrow?: string
  title: string
  subtitle?: string
  dark?: boolean
}) {
  return (
    <Reveal className="mx-auto max-w-3xl text-center">
      {eyebrow && (
        <p
          className={`text-xs font-semibold uppercase tracking-[0.2em] ${
            dark ? 'text-accent-300' : 'text-accent-600'
          }`}
        >
          {eyebrow}
        </p>
      )}
      <h2
        className={`mt-3 text-3xl font-bold tracking-tight sm:text-4xl ${
          dark ? 'text-white' : 'text-neutral-950'
        }`}
      >
        {title}
      </h2>
      {subtitle && (
        <p className={`mt-4 text-lg ${dark ? 'text-neutral-300' : 'text-neutral-600'}`}>
          {subtitle}
        </p>
      )}
    </Reveal>
  )
}

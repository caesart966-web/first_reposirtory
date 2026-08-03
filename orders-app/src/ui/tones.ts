import type { Tone } from '../db/types'

/**
 * Мягкие плашки-«пилюли»: подложка того же оттенка с низкой насыщенностью,
 * текст — насыщенный цвет тона. Никаких кислотных бейджей.
 */
export const pillTone: Record<Tone, string> = {
  neutral: 'bg-ink/5 text-muted dark:bg-ink/10',
  muted: 'bg-muted/10 text-muted dark:bg-muted/15',
  accent: 'bg-accent/10 text-accent dark:bg-accent/15',
  warn: 'bg-warn/10 text-warn dark:bg-warn/15',
  violet: 'bg-violet/10 text-violet dark:bg-violet/15',
  money: 'bg-money/10 text-money dark:bg-money/15',
  danger: 'bg-danger/10 text-danger dark:bg-danger/15',
}

/** Только цвет текста — для чисел и иконок. */
export const textTone: Record<Tone, string> = {
  neutral: 'text-ink',
  muted: 'text-muted',
  accent: 'text-accent',
  warn: 'text-warn',
  violet: 'text-violet',
  money: 'text-money',
  danger: 'text-danger',
}

/** Цвет заливки — для полоски слева у просроченных карточек и точек-индикаторов. */
export const bgTone: Record<Tone, string> = {
  neutral: 'bg-line',
  muted: 'bg-muted',
  accent: 'bg-accent',
  warn: 'bg-warn',
  violet: 'bg-violet',
  money: 'bg-money',
  danger: 'bg-danger',
}

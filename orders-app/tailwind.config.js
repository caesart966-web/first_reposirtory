/** @type {import('tailwindcss').Config} */
// Дизайн-система приложения.
// Цвета живут в CSS-переменных (см. src/index.css) — светлая и тёмная темы
// описаны отдельно, тёмная не является инверсией светлой.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: 'rgb(var(--c-bg) / <alpha-value>)',
        surface: 'rgb(var(--c-surface) / <alpha-value>)',
        'surface-2': 'rgb(var(--c-surface-2) / <alpha-value>)',
        line: 'rgb(var(--c-line) / <alpha-value>)',
        ink: 'rgb(var(--c-ink) / <alpha-value>)',
        muted: 'rgb(var(--c-muted) / <alpha-value>)',
        accent: 'rgb(var(--c-accent) / <alpha-value>)',
        money: 'rgb(var(--c-money) / <alpha-value>)',
        warn: 'rgb(var(--c-warn) / <alpha-value>)',
        danger: 'rgb(var(--c-danger) / <alpha-value>)',
        violet: 'rgb(var(--c-violet) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'Manrope', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      fontSize: {
        // Ниже 13px не опускаемся нигде.
        caption: ['0.8125rem', { lineHeight: '1.15rem', letterSpacing: '0.01em' }], // 13
        body: ['0.9375rem', { lineHeight: '1.4rem' }], // 15
        'body-lg': ['1rem', { lineHeight: '1.5rem' }], // 16
        title: ['1.375rem', { lineHeight: '1.75rem', letterSpacing: '-0.02em' }], // 22
        'title-lg': ['1.5rem', { lineHeight: '1.9rem', letterSpacing: '-0.02em' }], // 24
        metric: ['2rem', { lineHeight: '2.25rem', letterSpacing: '-0.03em' }], // 32
        'metric-lg': ['2.5rem', { lineHeight: '2.75rem', letterSpacing: '-0.03em' }], // 40
      },
      borderRadius: {
        card: '16px',
        btn: '12px',
        chip: '8px',
      },
      boxShadow: {
        soft: '0 1px 3px rgba(16,24,40,0.06)',
        lift: '0 4px 16px rgba(16,24,40,0.08)',
        sheet: '0 -8px 40px rgba(16,24,40,0.14)',
      },
      spacing: {
        // Шкала 4/8/12/16/24/32 покрыта базовым Tailwind (1/2/3/4/6/8),
        // добавляем безопасную зону под системные жесты Android/iOS.
        safe: 'env(safe-area-inset-bottom, 0px)',
      },
      keyframes: {
        'sheet-in': {
          from: { transform: 'translateY(100%)' },
          to: { transform: 'translateY(0)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'sheet-in': 'sheet-in 220ms cubic-bezier(0.22, 1, 0.36, 1)',
      },
      transitionTimingFunction: {
        out: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
    },
  },
  plugins: [],
}

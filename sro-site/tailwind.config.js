/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Единственный акцентный цвет сайта — спокойный кобальтовый синий.
        accent: {
          50: '#F2F5FF',
          100: '#E6ECFF',
          200: '#C9D6FE',
          300: '#A3B8FC',
          400: '#7490F7',
          500: '#4A66EF',
          600: '#2F4BDE',
          700: '#2439B8',
          800: '#202F93',
          900: '#1E2A75',
          950: '#141A45'
        }
      },
      fontFamily: {
        sans: [
          '"Inter Variable"',
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          '"Segoe UI"',
          'Roboto',
          'sans-serif'
        ]
      },
      boxShadow: {
        card: '0 1px 2px rgb(20 26 69 / 0.04), 0 8px 24px -12px rgb(20 26 69 / 0.12)',
        'card-hover': '0 2px 4px rgb(20 26 69 / 0.05), 0 16px 40px -16px rgb(20 26 69 / 0.18)'
      }
    }
  },
  plugins: []
}

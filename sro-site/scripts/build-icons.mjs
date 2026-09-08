// Иконка для «на экран Домой» в iOS (apple-touch-icon).
//
// Safari не умеет SVG-фавиконку для ярлыка на рабочем столе: без PNG он
// показывает уменьшенный скриншот страницы, и вместо знака компании на экране
// оказывается нечитаемый кусок текста. Android и десктопные браузеры берут
// favicon.svg и в этом файле не нуждаются.
//
// Рисуется из того же public/favicon.svg — второго источника правды нет.
// Прозрачности нет намеренно: iOS подкладывает под ярлык чёрный фон.
//
// Запуск: PLAYWRIGHT=/путь/к/playwright-core/index.js node scripts/build-icons.mjs
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const svg = readFileSync(resolve(root, 'public/favicon.svg'), 'utf8')
const SIZE = 180

const pw = await import(process.env.PLAYWRIGHT || 'playwright-core')
const { chromium } = pw.default ?? pw
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' })
const page = await browser.newPage({ viewport: { width: SIZE, height: SIZE }, deviceScaleFactor: 1 })
await page.setContent(
  `<!doctype html><meta charset="utf-8"><style>
     html,body{margin:0;padding:0;background:#2F4BDE}
     svg{display:block;width:${SIZE}px;height:${SIZE}px}
   </style>${svg}`,
  { waitUntil: 'load' },
)
await page.screenshot({ path: resolve(root, 'public/apple-touch-icon.png'), type: 'png' })
await browser.close()
console.log(`apple-touch-icon.png готов: ${SIZE}×${SIZE}`)

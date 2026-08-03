// Генератор иконок приложения: рисуем SVG и превращаем его в PNG 192 и 512.
// Запуск: npm run icons  (перезапускать нужно только если менял рисунок)
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import sharp from 'sharp'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const publicDir = resolve(root, 'public')
const iconsDir = resolve(publicDir, 'icons')
mkdirSync(iconsDir, { recursive: true })

/**
 * Рисунок иконки: тёмно-синяя плашка, на ней «список заказов» —
 * три белые строки разной длины и зелёная галочка (деньги пришли).
 * scale — доля холста, которую занимает рисунок (для maskable оставляем поля).
 */
function icon({ size = 512, scale = 1, radius = 0.22, background = true } = {}) {
  const s = size
  const c = s / 2
  const box = s * 0.62 * scale // размер рисунка внутри

  const barH = box * 0.115
  const gap = box * 0.15
  const x = c - box / 2
  const yStart = c - box * 0.34
  const widths = [1, 0.72, 0.46]

  const bars = widths
    .map(
      (w, i) =>
        `<rect x="${x}" y="${yStart + i * (barH + gap)}" width="${box * w}" height="${barH}" rx="${barH / 2}" fill="#FFFFFF" fill-opacity="${i === 0 ? 1 : 0.75}"/>`,
    )
    .join('')

  // Зелёная галочка в правом нижнем углу рисунка
  const r = box * 0.27
  const cx = c + box * 0.34
  const cy = c + box * 0.34
  const check = `
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="#12A578"/>
    <path d="M ${cx - r * 0.42} ${cy + r * 0.02} L ${cx - r * 0.1} ${cy + r * 0.34} L ${cx + r * 0.45} ${cy - r * 0.34}"
      fill="none" stroke="#FFFFFF" stroke-width="${r * 0.28}" stroke-linecap="round" stroke-linejoin="round"/>`

  const bg = background
    ? `<defs>
         <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
           <stop offset="0%" stop-color="#5B7DE8"/>
           <stop offset="100%" stop-color="#3F5FCC"/>
         </linearGradient>
       </defs>
       <rect width="${s}" height="${s}" rx="${s * radius}" fill="url(#g)"/>`
    : ''

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}" viewBox="0 0 ${s} ${s}">${bg}${bars}${check}</svg>`
}

const tasks = [
  { file: resolve(iconsDir, 'icon-192.png'), svg: icon({ size: 512 }), size: 192 },
  { file: resolve(iconsDir, 'icon-512.png'), svg: icon({ size: 512 }), size: 512 },
  // maskable: фон во весь холст, рисунок ужат — Android обрежет края по своей маске
  {
    file: resolve(iconsDir, 'maskable-512.png'),
    svg: icon({ size: 512, scale: 0.78, radius: 0 }),
    size: 512,
  },
]

for (const t of tasks) {
  const png = await sharp(Buffer.from(t.svg)).resize(t.size, t.size).png().toBuffer()
  writeFileSync(t.file, png)
  console.log('готово:', t.file)
}

// Иконка вкладки браузера
writeFileSync(resolve(publicDir, 'favicon.svg'), icon({ size: 64, radius: 0.22 }))
console.log('готово:', resolve(publicDir, 'favicon.svg'))

// Картинки для карточек компании на картах (16.10.2026): Яндекс Бизнес,
// 2ГИС, Google. Заказчик: «перейдём к продвижению карточек».
//
// Собираются из тех же фирменных элементов, что og.png (build-og.mjs):
// знак весов, тёплый графит accent-950, латунь, Brygada 1918 и Onest.
// Нарисованный один раз логотип разошёлся бы с сайтом при первой правке знака.
// Имя на логотипе — прописными, как в шапке сайта и в реестре; в поле
// «Название» карточки — «Бизнес-Групп»: кавычки там запрещены правилами
// Яндекс Бизнеса, а форма ООО идёт в реквизиты.
//
// Чего на картинках нет нарочно: телефона, адреса сайта и фотографий.
// Модерация карт отклоняет картинки с контактами и стоковые снимки
// (опыт norma-site с Яндекс Бизнесом, 28.09.2026), а права на фотографии
// сайта не подтверждены (public/img/CREDITS.md).
//
//   PLAYWRIGHT=/opt/node22/lib/node_modules/playwright/index.mjs node scripts/build-cards.mjs [папка]
//
// Папка по умолчанию — release/cards (в git не идёт). Файлы:
//   logo-znak.png          1024×1024 — знак по центру, с полями под круглую обрезку
//   logo-s-nazvaniem.png   1024×1024 — знак, имя и «Вступление в СРО»
//   oblozhka-16x9.png      1920×1080 — обложка (Google, 2ГИС, запасная для Яндекса)
//   oblozhka-4x1.png       1440×360  — обложка Яндекс Бизнеса (рекомендованный размер)
//   uslugi/usluga-*.png    1200×1200 — восемь услуг для фото «Услуги» (и -korotko)
const pw = await import(process.env.PLAYWRIGHT || 'playwright-core')
const { chromium } = pw.default ?? pw
import { mkdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const OUT = resolve(process.argv[2] || resolve(root, 'release/cards'))
mkdirSync(OUT, { recursive: true })

const face = (family, pkg, file) =>
  `@font-face{font-family:${family};font-style:normal;font-weight:100 900;src:url(data:font/woff2;base64,` +
  readFileSync(resolve(root, `node_modules/@fontsource-variable/${pkg}/files/${file}`)).toString('base64') +
  `) format('woff2-variations')}`

// Знак — те же координаты, что в ScalesMark и build-og.mjs.
const scales = (width) => `<svg viewBox="-1 2 50 37.4" fill="#C09A68" stroke="#C09A68"
  stroke-linecap="round" stroke-linejoin="round" style="width:${width}px;height:auto;display:block">
  <path d="M3.2 12.6 24 3.6l20.8 9Z" fill="none" stroke-width="2"/>
  <path d="M24 12.6v20" fill="none" stroke-width="2.2"/>
  <path d="M5.2 13.4.6 25.2m4.6-11.8 4.6 11.8m33-11.8-4.6 11.8m4.6-11.8 4.6 11.8" fill="none" stroke-width="1.2"/>
  <path d="M-.4 25.2h11.2q-5.6 7.2-11.2 0Zm37.6 0h11.2q-5.6 7.2-11.2 0Z" stroke="none"/>
  <path d="M20.4 32.4h7.2l2.2 4.2H18.2Z" stroke="none"/>
  <path d="M16.2 37.9h15.6" fill="none" stroke-width="1.5"/></svg>`

const head = `<meta charset="utf-8"><style>
  ${face('Onest', 'onest', 'onest-cyrillic-wght-normal.woff2')}
  ${face('Onest', 'onest', 'onest-latin-wght-normal.woff2')}
  ${face('Brygada', 'brygada-1918', 'brygada-1918-cyrillic-wght-normal.woff2')}
  ${face('Brygada', 'brygada-1918', 'brygada-1918-latin-wght-normal.woff2')}
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#1C1815;overflow:hidden;position:relative;
    font-family:Onest,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
  .light{position:absolute;border-radius:50%;background:radial-gradient(circle,#9D744333 0%,#9D744300 70%)}
  .name{font-family:Brygada,Georgia,serif;font-weight:500;line-height:1;color:#FBF9F5;
    letter-spacing:-.01em;font-variant-numeric:lining-nums}
  .sub{color:#D6CDC1}
  /* Имя — как в шапке сайта и в реестре: прописными, Onest. */
  .brand{font-weight:600;letter-spacing:.05em;color:#FBF9F5;line-height:1}
  .rule{display:block;height:1px;background:#C09A68}
</style>`

const PAGES = [
  {
    file: 'logo-znak.png', w: 1024, h: 1024,
    // Карты показывают логотип кружком: знак занимает середину, края пустые.
    body: `<div class="light" style="right:-260px;top:-300px;width:900px;height:900px"></div>
      <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center">${scales(560)}</div>`,
  },
  {
    file: 'logo-s-nazvaniem.png', w: 1024, h: 1024,
    body: `<div class="light" style="right:-260px;top:-300px;width:900px;height:900px"></div>
      <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center">
        ${scales(380)}
        <div class="brand" style="margin-top:72px;font-size:78px">БИЗНЕС-ГРУПП</div>
        <span class="rule" style="width:72px;margin-top:40px"></span>
        <div class="sub" style="margin-top:34px;font-size:48px">Вступление в&nbsp;СРО</div>
      </div>`,
  },
  {
    file: 'oblozhka-16x9.png', w: 1920, h: 1080,
    // Главное — в средней полосе: площадки обрезают обложку по-разному.
    body: `<div class="light" style="right:-200px;top:-360px;width:1200px;height:1200px"></div>
      <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:110px">
        ${scales(330)}
        <div>
          <div class="sub" style="display:flex;align-items:center;gap:22px;font-size:36px">
            <span class="rule" style="width:60px"></span>ООО «БИЗНЕС-ГРУПП»</div>
          <div class="name" style="margin-top:30px;font-size:118px">Вступление в&nbsp;СРО<br>под&nbsp;ключ</div>
          <div class="sub" style="margin-top:40px;font-size:38px;line-height:1.4">Строители, проектировщики, изыскатели</div>
        </div>
      </div>`,
  },
  {
    file: 'oblozhka-4x1.png', w: 1440, h: 360,
    body: `<div class="light" style="right:-120px;top:-420px;width:900px;height:900px"></div>
      <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:56px">
        ${scales(150)}
        <div>
          <div class="name" style="font-size:68px">Вступление в&nbsp;СРО под&nbsp;ключ</div>
          <div class="sub" style="margin-top:18px;font-size:27px">Строители, проектировщики, изыскатели</div>
        </div>
      </div>`,
  },
]

// Картинки услуг для блока «Услуги» в фотографиях Яндекс Бизнеса (26.10.2026,
// просьба заказчика: «красиво и профессионально оформить услуги»).
// Светлый лист сайта: крем, графит, латунь. Название — как `short` или `title`
// в services.ts (сборка падает, если услугу переименовали, а здесь нет). Строка
// под ним — простыми словами, что получит клиент (заказчик: «Уровень
// ответственности — совсем непонятен»), только из текстов страниц услуг.
// Без знака, телефона и адреса сайта: знак поверх картинки модерация считает
// водяным, контакты — рекламой (опыт norma-site). У каждой картинки короткий
// вариант `-korotko` — значок и название — для повторной загрузки, если
// полную отклонят: тот же файл второй раз отклоняют снова.
const { createElement } = await import('react')
const { renderToStaticMarkup } = await import('react-dom/server')
const icons = await import('lucide-react')
const icon = (name) =>
  renderToStaticMarkup(createElement(icons[name], { size: 60, strokeWidth: 1.5, color: '#86602F' }))

const SERVICES = [
  ['vstuplenie', 'Building2', 'Вступление в СРО', 'Проверим, нужно ли вам членство, и сопроводим до внесения в реестр членов СРО'],
  ['podbor', 'Search', 'Подбор и проверка СРО', 'Сравним условия и взносы нескольких СРО и проверим выбранную по госреестру до оплаты'],
  ['dokumenty', 'FileText', 'Подготовка документов', 'Соберём документы под требования выбранной СРО и проверим каждый до подачи'],
  ['nrs', 'UserCheck', 'Специалисты НРС', 'Для вступления в штате нужны два специалиста из национального реестра. Проверим ваших сотрудников или поможем найти'],
  ['nok', 'GraduationCap', 'Независимая оценка квалификации (НОК)', 'Экзамен для специалиста: без свидетельства его не внесут в национальный реестр. Поможем подготовиться и записаться'],
  ['uroven', 'ListChecks', 'Изменение уровня ответственности', 'От уровня в СРО зависит, на какую сумму можно заключать договоры. Подберём нужный уровень и рассчитаем доплату взноса'],
  ['proverki', 'Handshake', 'Сопровождение проверок', 'СРО регулярно проверяет своих членов. Подготовим к проверке и составим ответы на её запросы'],
  ['licenzii', 'BadgeCheck', 'Лицензии, обучение и сертификация', 'Поможем получить лицензии МЧС и Минкультуры и сертификат ISO 9001, организуем обучение сотрудников'],
]
const servicesSrc = readFileSync(resolve(root, 'src/content/services.ts'), 'utf8')
const licensesSrc = readFileSync(resolve(root, 'src/components/Licenses.tsx'), 'utf8')
for (const [, , title] of SERVICES) {
  const named = [`short: '${title}'`, `title: '${title}'`].some((k) => servicesSrc.includes(k))
  if (!named && !licensesSrc.includes(`title="${title}"`))
    throw new Error(`«${title}»: такой услуги на сайте нет — сверить с services.ts`)
}
// Неразрывные пробелы после коротких слов: «в СРО», «и ИП» не разрываются.
const nb = (s) => s.replace(/(^|\s)(в|и|до|по|для|под|не|на|с|к|о|а|то|от|из|ISO) /g, '$1$2&nbsp;')
const sheet = (inner) => `<div style="position:absolute;inset:0;background:#FBF9F5">
    <div class="light" style="left:-300px;top:-380px;width:1100px;height:1100px;background:radial-gradient(circle,#E3CDA955 0%,#E3CDA900 70%)"></div>
    <div style="position:absolute;inset:44px;border:1px solid #E3CDA9"></div>
    <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 150px">${inner}</div>
  </div>`
const ring = (name) => `<div style="width:128px;height:128px;border-radius:50%;border:1.5px solid #C09A68;
    display:flex;align-items:center;justify-content:center;background:#F7F1E8">${icon(name)}</div>`
// Длинное название (НОК, уровень) в 100 px шло в четыре строки — тесно.
const title = (t) =>
  `<div class="name" style="color:#1C1815;font-size:${t.length > 24 ? 84 : 100}px;line-height:1.06;margin-top:64px">${nb(t)}</div>`
for (const [slug, iconName, t, sub] of SERVICES) {
  PAGES.push({
    file: `uslugi/usluga-${slug}.png`, w: 1200, h: 1200,
    body: sheet(`${ring(iconName)}${title(t)}
      <span class="rule" style="width:72px;margin-top:56px"></span>
      <div style="margin-top:44px;font-size:42px;line-height:1.4;color:#5C534A;max-width:880px">${nb(sub)}.</div>`),
  })
  PAGES.push({ file: `uslugi/usluga-${slug}-korotko.png`, w: 1200, h: 1200, body: sheet(`${ring(iconName)}${title(t)}`) })
}
mkdirSync(resolve(OUT, 'uslugi'), { recursive: true })

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium' })
for (const p of PAGES) {
  const page = await browser.newPage({ viewport: { width: p.w, height: p.h }, deviceScaleFactor: 1 })
  await page.setContent(`<!doctype html><html lang="ru"><head>${head}<style>body{width:${p.w}px;height:${p.h}px}</style></head><body>${p.body}</body></html>`, { waitUntil: 'load' })
  await page.evaluate(() => document.fonts.ready).catch(() => {})
  await page.waitForTimeout(400)
  // Шрифт обязан быть фирменным: запасной Georgia на логотипе — брак.
  // Браузер грузит начертание, только когда им что-то набрано, поэтому
  // у знака без надписей проверять нечего.
  const fonts = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family))
  if (p.body.includes('class="name"') && !fonts.some((f) => f.includes('Brygada'))) throw new Error(`${p.file}: Brygada не загрузилась`)
  // Ничего не вылезает за край кадра.
  const over = await page.evaluate(() =>
    [...document.querySelectorAll('body *')].some((el) => {
      const r = el.getBoundingClientRect()
      return !el.classList.contains('light') && (r.left < 0 || r.top < 0 || r.right > innerWidth || r.bottom > innerHeight)
    }),
  )
  if (over) throw new Error(`${p.file}: содержимое вылезает за край`)
  await page.screenshot({ path: resolve(OUT, p.file), type: 'png' })
  await page.close()
  console.log(`${p.file}: ${p.w}×${p.h}`)
}
await browser.close()
console.log('карточки:', OUT)

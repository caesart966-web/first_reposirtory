/*
 * Длинные названия не вылезают из своих рамок - на шести ширинах.
 *
 * Страницы собирает tools/render-long-names.php из самых неудобных
 * названий выгрузки 1С. Здесь каждая открывается в настоящем браузере
 * на 320, 360, 390, 768, 1024 и 1280 px, и для каждого куска текста
 * проверяется, что он не выходит ни за свой элемент, ни за карточку,
 * строку корзины, ячейку или плитку, в которой стоит, ни за экран.
 * Полосы с горизонтальной прокруткой (таблица сравнения) пропускаются:
 * там выходить за экран - нормально, так они и устроены.
 *
 * Первая же прогонка нашла два места: название с куском
 * «HTR0001,140x80x38мм,-32+350С,точность» вылезало из карточки
 * в каталоге (на 320 px - на 46 px, и страница становилась шире
 * экрана) и из строки корзины - почти на всех ширинах.
 *
 * Запуск: node tools/test-long-names.mjs <папка со страницами>
 */
import { existsSync } from 'node:fs';
import { chromium } from 'playwright';

const dir = process.argv[2];
if (!dir || !existsSync(`${dir}/category.html`)) {
  console.error('Сначала: php tools/render-long-names.php <папка>');
  process.exit(2);
}
const PAGES = ['category', 'department', 'product', 'cart', 'compare'];
const WIDTHS = [320, 360, 390, 768, 1024, 1280];

const exe = [process.env.CHROMIUM_PATH, '/opt/pw-browsers/chromium'].find(c => c && existsSync(c));
const browser = await chromium.launch(exe ? { executablePath: exe } : {});

function findOverflow() {
  const issues = [];
  const vw = document.documentElement.clientWidth;
  const extra = document.documentElement.scrollWidth - vw;
  if (extra > 1) issues.push(`страница шире экрана на ${extra} px`);
  const walker = document.createTreeWalker(document.querySelector('main'), NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const text = walker.currentNode;
    if (!text.textContent.trim()) continue;
    const el = text.parentElement;
    if (seen.has(el)) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || el.closest('.visually-hidden')) continue;
    let inScroller = false;
    for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) {
      const ox = getComputedStyle(a).overflowX;
      if (ox === 'auto' || ox === 'scroll') { inScroller = true; break; }
    }
    if (inScroller) continue;
    const range = document.createRange();
    range.selectNodeContents(text);
    const tr = range.getBoundingClientRect();
    const er = el.getBoundingClientRect();
    const box = el.closest('.product-card, .cart-row, td, th, .breadcrumbs, .product-info, .category-card, .page-head') || el;
    const limit = Math.min(er.right, box.getBoundingClientRect().right, vw);
    if (tr.right > limit + 1.5) {
      seen.add(el);
      issues.push(`«${text.textContent.trim().slice(0, 45)}» (${el.tagName.toLowerCase()}.${String(el.className).split(' ')[0]}) `
        + `вылезает на ${Math.round(tr.right - limit)} px`);
    }
  }
  return issues;
}

let bad = 0;
for (const name of PAGES) {
  for (const width of WIDTHS) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await page.goto(`file://${dir}/${name}.html`);
    await page.addStyleTag({ content: '.reveal{opacity:1!important;transform:none!important}' });
    await page.waitForTimeout(100);
    const issues = await page.evaluate(findOverflow);
    for (const issue of issues) console.log(`${name}, ${width} px: ${issue}`);
    bad += issues.length;
    await page.close();
  }
}
await browser.close();
console.log(`Длинные названия: ${PAGES.length} страниц × ${WIDTHS.length} ширин`
  + (bad ? `, вылезает: ${bad}` : ' — ничего не вылезает'));
process.exit(bad ? 1 : 0);

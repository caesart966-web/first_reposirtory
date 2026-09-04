/**
 * Проверки макета «Строй-Герой» в настоящем браузере.
 *
 * Ловит то, что глазами не увидишь, пока не откроешь нужную страницу
 * на нужной ширине в нужной теме:
 *   • ошибки в консоли;
 *   • горизонтальную прокрутку (страница «едет» вбок на телефоне);
 *   • контраст текста ниже нормы WCAG — в светлой и тёмной теме;
 *   • мелкие цели нажатия (меньше 24 px по короткой стороне);
 *   • картинки без alt и ссылки без доступного имени;
 *   • плашку cookie, закрывающую низ страницы.
 *
 * Запуск: node test.mjs   (нужен playwright и Chromium)
 */

import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.dirname(fileURLToPath(import.meta.url));
const PAGES = ['index', 'catalog', 'product', 'cart', 'calculator', 'delivery', 'contacts', '404'];
const WIDTHS = [360, 390, 768, 1024, 1280, 1440, 1920];
const THEMES = ['light', 'dark'];

/* Chromium из образа: свой playwright его не скачивает. */
const EXECUTABLE = process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

const fails = [];
const fail = (msg) => fails.push(msg);

/* Считаем контраст прямо в странице: только там известен реальный цвет
   фона под текстом — он может прийти от любого предка. */
const CONTRAST_PROBE = `(() => {
  const lum = (c) => {
    const [r, g, b] = c.map((v) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const parse = (s) => (s.match(/[\\d.]+/g) || []).slice(0, 4).map(Number);
  const bgOf = (el) => {
    for (let n = el; n; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c.length >= 3 && (c[3] === undefined || c[3] > 0.5)) return c;
    }
    return [255, 255, 255];
  };
  const ratio = (a, b) => {
    const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  };
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    const text = [...el.childNodes]
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent.trim())
      .join('');
    if (!text) continue;
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none' || +st.opacity < 0.9) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const size = parseFloat(st.fontSize);
    const bold = +st.fontWeight >= 700;
    /* Крупный текст по WCAG: от 24 px, или от 18.66 px полужирный */
    const large = size >= 24 || (size >= 18.66 && bold);
    const need = large ? 3 : 4.5;
    const got = ratio(parse(st.color), bgOf(el));
    if (got < need) {
      out.push({
        text: text.slice(0, 45),
        got: +got.toFixed(2),
        need,
        size: Math.round(size),
        sel: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/)[0] : ''),
      });
    }
  }
  return out;
})()`;

const browser = await chromium.launch({ executablePath: EXECUTABLE });

/* ==========================================================================
   Ошибки в консоли, горизонтальная прокрутка, alt, доступные имена
   ========================================================================== */

for (const name of PAGES) {
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await ctx.newPage();
    const errors = [];
    page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
    page.on('pageerror', (e) => errors.push(String(e)));

    await page.goto('file://' + path.join(DIR, `${name}.html`), { waitUntil: 'load' });
    await page.waitForTimeout(250);

    for (const e of errors) fail(`${name} @${width}: ошибка в консоли — ${e.slice(0, 120)}`);

    const overflow = await page.evaluate(() => {
      const doc = document.documentElement;
      if (doc.scrollWidth <= doc.clientWidth) return null;
      /* Виноватого ищем поимённо, иначе «страница едет» ничего не говорит */
      const guilty = [...document.querySelectorAll('body *')]
        .filter((el) => el.getBoundingClientRect().right > doc.clientWidth + 1)
        .slice(0, 3)
        .map((el) => el.tagName.toLowerCase() + '.' + String(el.className).trim().split(/\s+/)[0]);
      return { scroll: doc.scrollWidth, client: doc.clientWidth, guilty };
    });
    if (overflow) {
      fail(`${name} @${width}: горизонтальная прокрутка ${overflow.scroll}>${overflow.client}, виновники: ${overflow.guilty.join(', ')}`);
    }

    if (width === 1280) {
      const a11y = await page.evaluate(() => {
        const noAlt = [...document.images].filter((i) => !i.hasAttribute('alt')).length;
        const nameless = [...document.querySelectorAll('a[href], button')]
          .filter((el) => {
            const r = el.getBoundingClientRect();
            if (!r.width || !r.height) return false;
            return !(el.textContent.trim() || el.getAttribute('aria-label') || el.getAttribute('title'));
          })
          .map((el) => el.tagName.toLowerCase() + '.' + String(el.className).trim().split(/\s+/)[0]);
        return { noAlt, nameless: [...new Set(nameless)] };
      });
      if (a11y.noAlt) fail(`${name}: картинок без alt — ${a11y.noAlt}`);
      if (a11y.nameless.length) fail(`${name}: кнопки/ссылки без названия — ${a11y.nameless.join(', ')}`);
    }

    await ctx.close();
  }
}

/* ==========================================================================
   Контраст в обеих темах
   ========================================================================== */

for (const name of PAGES) {
  for (const theme of THEMES) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    await page.addInitScript(`try { localStorage.setItem('sg-theme', '"${theme}"'); } catch (e) {}`);
    await page.goto('file://' + path.join(DIR, `${name}.html`), { waitUntil: 'load' });
    await page.waitForTimeout(250);

    const low = await page.evaluate(CONTRAST_PROBE);
    for (const item of low.slice(0, 6)) {
      fail(`${name} (${theme}): контраст ${item.got} вместо ${item.need} — ${item.sel} ${item.size}px «${item.text}»`);
    }

    /* Пунктир вокруг пустых мест должен быть виден. Проверка контраста
       текста этого не ловит: она смотрит на буквы, а «здесь ничего нет»
       читается по рамке. Один раз цвет пунктира был зашит под светлую
       тему, в тёмной давал контраст 1.03, и плейсхолдер выглядел
       обычным залитым чипом — тесты при этом были зелёные. */
    const ph = await page.evaluate(() => {
      const el = document.querySelector('.ph, .data-notice');
      if (!el) return null;
      const parse = (s) => (s.match(/[\d.]+/g) || []).map(Number);
      const lum = (c) => {
        const [r, g, b] = c.map((v) => {
          const s = v / 255;
          return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      const cs = getComputedStyle(el);
      const border = parse(cs.borderTopColor);
      const bg = parse(cs.backgroundColor);
      if (border.length < 3 || bg.length < 3) return null;
      const a = border[3] === undefined ? 1 : border[3];
      const mixed = [0, 1, 2].map((i) => border[i] * a + bg[i] * (1 - a));
      const [hi, lo] = [lum(mixed), lum(bg.slice(0, 3))].sort((x, y) => y - x);
      return { ratio: +((hi + 0.05) / (lo + 0.05)).toFixed(2), color: cs.borderTopColor };
    });
    if (ph && ph.ratio < 1.6) {
      fail(`${name} (${theme}): пунктир пустых мест сливается с фоном — контраст ${ph.ratio}, цвет ${ph.color}`);
    }

    await ctx.close();
  }
}

/* ==========================================================================
   Цели нажатия на телефоне и плашка cookie
   ========================================================================== */

for (const name of PAGES) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(DIR, `${name}.html`), { waitUntil: 'load' });
  await page.waitForTimeout(300);

  const small = await page.evaluate(() => {
    const seen = new Set();
    for (const el of document.querySelectorAll('a[href], button, input, select')) {
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      /* Строчная ссылка живёт по правилам текста: у неё высота строки,
         а не кнопки, и правило про 24 px к ней не применяется. */
      if (el.tagName === 'A' && getComputedStyle(el).display.startsWith('inline')) continue;
      /* Галочка внутри <label> нажимается по всей подписи — целью считается
         подпись, а не сам квадратик. */
      if (el.tagName === 'INPUT' && el.closest('label')) continue;
      if (Math.min(r.width, r.height) < 24) {
        seen.add(el.tagName.toLowerCase() + '.' + String(el.className).trim().split(/\s+/)[0] +
          ` ${Math.round(r.width)}x${Math.round(r.height)}`);
      }
    }
    return [...seen];
  });
  for (const s of small.slice(0, 4)) fail(`${name} @390: мелкая цель нажатия — ${s}`);

  /* Плашка cookie не должна прятать под собой низ страницы.
     Скроллим рывком: в стилях включён scroll-behavior: smooth, и плавная
     прокрутка на семь тысяч пикселей не успевает доехать до замера. */
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = 'auto';
    window.scrollTo(0, document.documentElement.scrollHeight);
  });
  await page.waitForTimeout(300);
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await page.waitForTimeout(200);
  const covered = await page.evaluate(() => {
    const bar = document.querySelector('[data-cookie]');
    if (!bar || bar.hidden) return null;
    const barTop = bar.getBoundingClientRect().top;
    const footer = document.querySelector('.site-footer');
    return footer.getBoundingClientRect().bottom > barTop + 1
      ? Math.round(footer.getBoundingClientRect().bottom - barTop)
      : null;
  });
  if (covered) fail(`${name} @390: плашка cookie закрывает ${covered}px низа страницы`);

  await ctx.close();
}

await browser.close();

/* ==========================================================================
   Итог
   ========================================================================== */

const checks = PAGES.length * WIDTHS.length + PAGES.length * THEMES.length + PAGES.length;
console.log(`Прогонов: ${checks} (${PAGES.length} страниц × ${WIDTHS.length} ширин, обе темы, телефон)`);

if (fails.length) {
  console.error(`\nНе прошло (${fails.length}):`);
  for (const f of fails) console.error('  • ' + f);
  process.exit(1);
}
console.log('Все проверки пройдены');

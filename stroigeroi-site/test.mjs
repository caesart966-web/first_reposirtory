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
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const DIR = path.dirname(fileURLToPath(import.meta.url));
const PAGES = ['index', 'catalog', 'product', 'cart', 'calculator', 'delivery', 'contacts',
  'checkout', 'order-done', 'favourites', 'compare', 'login', 'policy', 'terms', '404'];
const WIDTHS = [360, 390, 768, 1024, 1280, 1440, 1920];
const THEMES = ['light', 'dark'];

/* Где взять Chromium. По порядку: переменная CHROMIUM_PATH, затем браузер
   из образа (если проверки гоняют в контейнере, где playwright свой
   не скачивает), иначе — тот, что playwright поставил себе сам.
   Существование пути проверяем: на GitHub Actions пути из образа нет,
   и с жёстко зашитым значением проверки падали бы, не начавшись. */
function findChromium() {
  const candidates = [process.env.CHROMIUM_PATH, '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'];
  for (const c of candidates) {
    if (c && existsSync(c)) return c;
  }
  return undefined; // playwright возьмёт свой
}
const EXECUTABLE = findChromium();

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

/* Готовый набор проверок доступности. Он ловит больше, чем написанное
   вручную: ориентиры страницы, ссылки, отличимые одним цветом, подписи
   полей. Молча пропускать его нельзя — тогда CI зеленел бы, ничего
   не проверив, поэтому отсутствие файла это ошибка, а не повод пропустить. */
function loadAxe() {
  for (const c of [
    path.join(DIR, 'node_modules/axe-core/axe.min.js'),
    path.join(DIR, '..', 'node_modules/axe-core/axe.min.js'),
  ]) {
    if (existsSync(c)) return readFileSync(c, 'utf8');
  }
  console.error('Не найден axe-core. Поставьте его: npm install axe-core --no-save');
  process.exit(2);
}
const AXE_SOURCE = loadAxe();

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
    const phs = await page.evaluate(() => {
      const parse = (s) => (s.match(/[\d.]+/g) || []).map(Number);
      const lum = (c) => {
        const [r, g, b] = c.map((v) => {
          const s = v / 255;
          return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      /* Плейсхолдеры бывают двух видов: громкие в коробке и тихие
         с подчёркиванием. У вторых рамка только снизу, поэтому смотрим
         не на верхнюю сторону, а на первую, которая вообще нарисована. */
      const measure = (el) => {
        if (!el) return null;
        const cs = getComputedStyle(el);
        const side = ['Top', 'Bottom', 'Left', 'Right'].find(
          (s) => parseFloat(cs['border' + s + 'Width']) > 0 && cs['border' + s + 'Style'] !== 'none',
        );
        if (!side) return null;
        const border = parse(cs['border' + side + 'Color']);
        /* Фон под рамкой: у тихого плейсхолдера своего фона нет,
           поэтому поднимаемся до ближайшего непрозрачного предка. */
        let bg = [255, 255, 255];
        for (let n = el; n; n = n.parentElement) {
          const c = parse(getComputedStyle(n).backgroundColor);
          if (c.length >= 3 && (c[3] === undefined || c[3] > 0.5)) {
            bg = c.slice(0, 3);
            break;
          }
        }
        if (border.length < 3) return null;
        const a = border[3] === undefined ? 1 : border[3];
        const mixed = [0, 1, 2].map((i) => border[i] * a + bg[i] * (1 - a));
        const [hi, lo] = [lum(mixed), lum(bg)].sort((x, y) => y - x);
        return {
          ratio: +((hi + 0.05) / (lo + 0.05)).toFixed(2),
          color: cs['border' + side + 'Color'],
          side,
        };
      };
      return {
        громкий: measure(document.querySelector('.data-notice')),
        тихий: measure(document.querySelector('.product-card__meta .ph, .category-card__count, .cat-list__link .ph')),
      };
    });
    for (const [kind, ph] of Object.entries(phs)) {
      if (ph && ph.ratio < 1.6) {
        fail(`${name} (${theme}): ${kind} пунктир пустых мест сливается с фоном — контраст ${ph.ratio}, ${ph.side.toLowerCase()}, ${ph.color}`);
      }
    }

    /* Готовые проверки доступности на этой же странице и в этой же теме */
    await page.addScriptTag({ content: AXE_SOURCE });
    const axeReport = await page.evaluate(async () =>
      await window.axe.run(document, {
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'] },
      }));
    for (const v of axeReport.violations) {
      const sample = v.nodes[0] ? v.nodes[0].html.slice(0, 70) : '';
      fail(`${name} (${theme}): axe ${v.id} [${v.impact}] — ${v.help}${sample ? ' — ' + sample : ''}`);
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

/* ==========================================================================
   Сквозной проход покупки: кликами, от главной до «заказ принят»
   ========================================================================== */

/* Макет показывают заказчику ради сценария, поэтому сценарий должен
   проходиться кликами, а не подстановкой адресов в строку браузера.
   Один раз это уже подвело: страница «Заказ принят» существовала,
   но дойти до неё было нельзя — форма молча сбрасывалась. */
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  const here = () => page.url().split('/').pop().split('?')[0];

  const walk = async (label, action, expect) => {
    try {
      await action();
      await page.waitForTimeout(450);
    } catch (e) {
      fail(`сценарий, шаг «${label}»: не удалось — ${String(e).slice(0, 90)}`);
      return false;
    }
    if (here() !== expect) {
      fail(`сценарий, шаг «${label}»: ожидали ${expect}, оказались на ${here()}`);
      return false;
    }
    return true;
  };

  await page.goto('file://' + path.join(DIR, 'index.html'), { waitUntil: 'load' });
  await page.waitForTimeout(400);
  await page.evaluate(() => {
    const c = document.querySelector('[data-cookie]');
    if (c) { c.hidden = true; document.body.classList.remove('has-cookie'); }
  });

  const chain =
    (await walk('главная → каталог', () => page.click('.header-quick__link[href="catalog.html"]'), 'catalog.html')) &&
    (await walk('каталог → карточка', () => page.click('.product-card__title'), 'product.html')) &&
    (await walk('карточка → корзина', async () => {
      await page.click('[data-add="cart"]');
      await page.waitForTimeout(200);
      await page.click('a[href="cart.html"]');
    }, 'cart.html')) &&
    (await walk('корзина → оформление', () => page.click('a[href="checkout.html"]'), 'checkout.html')) &&
    (await walk('оформление → заказ принят', async () => {
      await page.fill('#co-name', 'Иван');
      await page.fill('#co-phone', '9638300999');
      await page.check('.consent input[type=checkbox]');
      await page.click('.checkout button[type=submit]');
    }, 'order-done.html'));

  if (chain) {
    /* Обратная сторона: незаполненная форма дальше пускать не должна */
    await page.goto('file://' + path.join(DIR, 'checkout.html'), { waitUntil: 'load' });
    await page.waitForTimeout(350);
    await page.click('.checkout button[type=submit]');
    await page.waitForTimeout(400);
    if (here() === 'order-done.html') {
      fail('сценарий: пустая форма оформления пропускает дальше — проверка полей не работает');
    }
  }

  for (const e of errors) fail(`сценарий: ошибка в консоли — ${e.slice(0, 110)}`);
  await ctx.close();
}

/* ==========================================================================
   Превью одним файлом: панель вкладок не должна съедать экран
   ========================================================================== */

/* Страниц стало четырнадцать, и панель переключения, переносясь по строкам,
   занимала на телефоне больше половины экрана: человек открывал присланную
   ссылку и видел не сайт, а список вкладок. Заметили это, только открыв
   на телефоне. Теперь высота панели под контролем, и добавление страниц
   её не раздувает. */
{
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(DIR, 'stroigeroi-preview.html'), { waitUntil: 'load' });
  await page.waitForTimeout(400);
  const bar = await page.evaluate(() => {
    const el = document.querySelector('.preview-bar');
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { height: Math.round(r.height), scrollable: el.scrollWidth > el.clientWidth };
  });
  if (!bar) {
    fail('превью: панель переключения страниц не найдена');
  } else {
    if (bar.height > 64) {
      fail(`превью @390: панель вкладок ${bar.height}px — она должна быть одной строкой, а не занимать экран`);
    }
    if (!bar.scrollable) {
      fail('превью @390: панель должна прокручиваться вбок — иначе часть страниц недоступна');
    }
  }
  await ctx.close();
}

/* ==========================================================================
   Поиск по разделам каталога
   ========================================================================== */

{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(DIR, 'index.html'), { waitUntil: 'load' });
  await page.waitForTimeout(300);
  await page.click('[data-search-input]');

  const ask = async (query) => {
    await page.fill('[data-search-input]', query);
    await page.waitForTimeout(150);
    /* Пробелы приводим к обычным: сборщик связывает предлоги неразрывным
       пробелом, и «Всё для сада» в разметке содержит U+00A0. Сравнивать
       с ним напрямую — значит проверять типографику вместо поиска. */
    return page.evaluate(() => {
      const flat = (s) => s.replace(/ /g, ' ').trim();
      return {
        items: [...document.querySelectorAll('.search-suggest__item')].map((a) => flat(a.textContent)),
        href: document.querySelector('.search-suggest__item')?.getAttribute('href') || '',
        empty: document.querySelector('.search-suggest__empty')?.innerHTML || '',
      };
    });
  };

  /* Ищем по началу слова: «сад» находит «Всё для сада» и не находит
     «Расходка», где «сад» стоит в середине другого слова. */
  const garden = await ask('сад');
  if (!garden.items.some((t) => /Всё для сада/.test(t))) {
    fail(`поиск: «сад» должен находить «Всё для сада», получено ${JSON.stringify(garden.items)}`);
  }
  if (garden.items.some((t) => /Расходка/.test(t))) {
    fail('поиск: «сад» не должен находить «Расходка» — совпадение не с начала слова');
  }
  /* Ссылка ведёт в каталог с запросом и сохраняет номер категории OpenCart */
  if (!/catalog\.html\?search=/.test(garden.href)) {
    fail(`поиск: подсказка должна вести в каталог с запросом, получено «${garden.href}»`);
  }

  /* «ё» и регистр не должны мешать */
  const fastener = await ask('КРЕПЕЖ');
  if (!fastener.items.some((t) => /Крепёж/.test(t))) {
    fail(`поиск: «КРЕПЕЖ» должен находить «Крепёж и фурнитура», получено ${JSON.stringify(fastener.items)}`);
  }

  /* Чего нет — про то честный ответ с телефоном, а не пустота */
  const nothing = await ask('<b>гвозди</b>');
  if (!nothing.empty) fail('поиск: на запрос без совпадений нужен ответ, а не пустой список');
  if (!/tel:/.test(nothing.empty)) fail('поиск: в ответе «ничего не нашлось» должен быть телефон');
  /* Запрос уходит в innerHTML — теги обязаны быть экранированы */
  if (/<b>/.test(nothing.empty)) fail('поиск: запрос подставляется в разметку без экранирования');

  await ctx.close();
}

/* ==========================================================================
   Карточка товара подстраивается под свою ширину
   ========================================================================== */

/* Случай, который медиазапросами не выразить: на 1680 px каталог идёт
   в четыре колонки, и карточка там УЖЕ, чем на 1280 в три колонки.
   Ширина экрана про это ничего не говорит. */
{
  const seen = [];
  for (const width of [1280, 1680]) {
    const ctx = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await ctx.newPage();
    await page.goto('file://' + path.join(DIR, 'catalog.html'), { waitUntil: 'load' });
    await page.waitForTimeout(300);
    seen.push(
      await page.evaluate(() => {
        const card = document.querySelector('.product-card');
        const bottom = card.querySelector('.product-card__bottom');
        return {
          card: Math.round(card.getBoundingClientRect().width),
          dir: getComputedStyle(bottom).flexDirection,
        };
      }),
    );
    await ctx.close();
  }
  const [wide, narrow] = seen;
  if (!(narrow.card < wide.card)) {
    fail(`карточка: на 1680 px она должна быть уже, чем на 1280 (четыре колонки против трёх), получено ${narrow.card} и ${wide.card}`);
  }
  if (wide.dir !== 'row') fail(`карточка ${wide.card}px: цена и кнопка должны стоять в строку, получено ${wide.dir}`);
  if (narrow.dir !== 'column') fail(`карточка ${narrow.card}px: цена и кнопка должны встать в столбик, получено ${narrow.dir}`);
}

/* ==========================================================================
   Калькулятор: счёт и русский формат чисел
   ========================================================================== */

{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(DIR, 'calculator.html'), { waitUntil: 'load' });
  await page.waitForTimeout(300);

  const read = () =>
    page.evaluate(() => ({
      answer: document.querySelector('[data-calc-answer]').textContent.trim(),
      rows: [...document.querySelectorAll('[data-calc-rows] li')].map((l) => l.textContent.trim()),
    }));

  /* 20 м² в один слой, запас 10 %, лист 3 м²: 22 / 3 = 7.33 → 8 листов */
  const gkl = await read();
  if (!/^8\s/.test(gkl.answer)) fail(`калькулятор: 20 м² должны дать 8 листов, получено «${gkl.answer}»`);

  /* Запятую на входе понимать обязан: по-русски дробное пишут через неё */
  await page.fill('[data-gkl-area]', '18,5');
  await page.waitForTimeout(200);
  const comma = await read();
  if (!/^7\s/.test(comma.answer)) fail(`калькулятор: 18,5 м² должны дать 7 листов, получено «${comma.answer}»`);

  /* И на выходе тоже запятая, а не точка */
  for (const row of comma.rows) {
    if (/\d\.\d/.test(row)) fail(`калькулятор: точка вместо запятой в дробном числе — «${row}»`);
  }

  await page.click('[data-calc-mode="mix"]');
  await page.waitForTimeout(200);
  for (const [sel, v] of [['[data-mix-area]', '120'], ['[data-mix-thick]', '8'], ['[data-mix-usage]', '1,4'], ['[data-mix-bag]', '30']]) {
    await page.fill(sel, v);
  }
  await page.waitForTimeout(250);
  const mix = await read();
  /* 120 × 8 × 1,4 × 1,1 = 1478,4 кг ÷ 30 = 49,28 → 50 мешков */
  if (!/^50\s/.test(mix.answer)) fail(`калькулятор: смеси должны дать 50 мешков, получено «${mix.answer}»`);
  for (const row of mix.rows) {
    if (/\d\.\d/.test(row)) fail(`калькулятор: точка вместо запятой — «${row}»`);
  }

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

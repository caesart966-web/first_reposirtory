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
/* 320 px не выдуманная ширина: это 400% увеличения на экране 1280,
   и по WCAG 1.4.10 при нём не должно появляться прокрутки вбок. */
const WIDTHS = [320, 360, 390, 768, 1024, 1280, 1440, 1920];
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

    /* Внешние адреса режем сами: на контактах стоят виджеты Яндекс.Карт,
       и проверка не должна зависеть от того, дотянулась ли машина
       до Яндекса. Всё, что ругается на наш собственный код, ловится
       по-прежнему. */
    const blockedHosts = ['yandex.ru'];

    /* У сообщения консоли есть адрес источника — по нему и отличаем
       свои ошибки от оборванных запросов к карте, не гадая по тексту. */
    const errors = [];
    page.on('console', (m) => {
      if (m.type() !== 'error') return;
      const from = (m.location() && m.location().url) || '';
      if (blockedHosts.some((h) => from.includes(h) || m.text().includes(h))) return;
      errors.push(m.text());
    });
    page.on('pageerror', (e) => errors.push(String(e)));

    await page.route('**/*', (route) => {
      const url = route.request().url();
      if (blockedHosts.some((h) => url.includes(h))) return route.abort();
      return route.continue();
    });

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
   Фокус виден на каждом элементе, до которого доводит Tab
   ==========================================================================

   По сайту фокус — красное кольцо, а у полей ввода его когда-то отключили
   ради вида под мышью. Человек с клавиатуры терял ориентир: по ссылкам
   кольцо есть, дошёл до поля — пропало. Теперь у полей своё, синее;
   проверка следит, чтобы ни один элемент не остался вовсе без кольца. */

for (const name of ['index', 'catalog', 'checkout', 'contacts', 'login']) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(DIR, `${name}.html`), { waitUntil: 'load' });
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    const c = document.querySelector('[data-cookie]');
    if (c) { c.hidden = true; document.body.classList.remove('has-cookie'); }

    /* Карты на странице контактов грузятся с чужого сервера, и попадёт ли
       кадр под Tab, зависит от того, есть ли на машине интернет: без сети
       кадр не загружается, браузер не считает его фокусируемым, и проверка
       его не видит. Из-за этого она молчала о настоящей ошибке — у карты
       не было видимого фокуса, — и сказала об этом только на сборочной
       машине, где сеть есть.

       Проверка, результат которой зависит от наличия интернета, бесполезна
       в обе стороны. Поэтому кадрам подставляется своё содержимое: фокус
       ведёт себя точно так же, а от сети больше ничего не зависит. */
    document.querySelectorAll('.shop-card__map').forEach((box) => box.classList.remove('is-mapfail'));
    document.querySelectorAll('.shop-card__mapframe').forEach((frame) => {
      frame.removeAttribute('src');
      frame.setAttribute('srcdoc', '<p>карта</p>');
    });
  });
  await page.waitForTimeout(200);

  const blind = new Set();
  for (let i = 0; i < 45; i++) {
    await page.keyboard.press('Tab');
    const spot = await page.evaluate(() => {
      const a = document.activeElement;
      if (!a || a === document.body) return null;
      const cs = getComputedStyle(a);
      const r = a.getBoundingClientRect();
      if (!r.width || !r.height) return null;   /* скрытое не считаем */
      const ring = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
      return ring ? null : a.tagName.toLowerCase() +
        (a.className && typeof a.className === 'string' ? '.' + a.className.trim().split(/\s+/)[0] : '');
    });
    if (spot) blind.add(spot);
  }
  if (blind.size) {
    fail(`${name}: фокус не виден на — ${[...blind].slice(0, 4).join(', ')}`);
  }
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

/* ==========================================================================
   Переключатель темы
   ==========================================================================

   Тему переводит View Transition, а на время перехода на <html> висит
   класс is-theme-vt, снимающий собственные transition заливок. Если он
   там застрянет — например, промах в обработке ошибки, — смена темы
   навсегда останется рывком в браузерах без View Transition. Проверяем
   и результат, и то, что класс убрался. */

{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('file://' + path.join(DIR, 'index.html'), { waitUntil: 'load' });
  await page.waitForTimeout(300);

  await page.click('[data-theme-toggle]');
  await page.waitForTimeout(600);
  let state = await page.evaluate(() => ({
    theme: document.documentElement.dataset.theme,
    stuck: document.documentElement.classList.contains('is-theme-vt'),
    meta: document.querySelector('meta[name="theme-color"]').content,
    pressed: document.querySelector('[data-theme-toggle]').getAttribute('aria-pressed'),
  }));
  if (state.theme !== 'dark') fail(`тема: нажатие не включило тёмную, осталось «${state.theme}»`);
  if (state.stuck) fail('тема: класс is-theme-vt остался на <html> после перехода');
  if (state.meta !== '#0e1117') fail(`тема: meta theme-color не обновился — «${state.meta}»`);
  if (state.pressed !== 'true') fail(`тема: aria-pressed у кнопки — «${state.pressed}», ожидалось true`);

  /* Частые нажатия: браузер отменяет незавершённый переход, и обработка
     отмены не должна оставлять класс или ронять страницу. */
  for (let i = 0; i < 6; i++) await page.click('[data-theme-toggle]');
  await page.waitForTimeout(900);
  state = await page.evaluate(() => ({
    theme: document.documentElement.dataset.theme,
    stuck: document.documentElement.classList.contains('is-theme-vt'),
  }));
  if (state.stuck) fail('тема: после частых нажатий класс is-theme-vt завис');
  if (!['light', 'dark'].includes(state.theme)) fail(`тема: после частых нажатий значение «${state.theme}»`);
  if (errors.length) fail(`тема: ошибка на странице — ${errors[0]}`);

  await ctx.close();
}

/* ==========================================================================
   Содержимое видно без JavaScript
   ==========================================================================

   Блоки с классом reveal появляются при прокрутке. Пока их прятал только
   CSS в расчёте на то, что класс вернёт JS, отключённый JavaScript
   оставлял главную без четырёх плиток, всех девятнадцати разделов
   каталога, карточек магазинов и обоих баннеров — тридцать блоков
   с opacity: 0 навсегда. Проверка простая: грузим страницы вообще без
   JS и смотрим, не оказался ли прозрачным хоть один блок на экране. */

{
  const ctx = await browser.newContext({
    javaScriptEnabled: false,
    viewport: { width: 1280, height: 900 },
  });
  const page = await ctx.newPage();

  for (const name of PAGES) {
    await page.goto('file://' + path.join(DIR, name + '.html'), { waitUntil: 'load' });
    const hidden = await page.evaluate(() =>
      [...document.querySelectorAll('.reveal')]
        .filter((el) => {
          const r = el.getBoundingClientRect();
          return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
        })
        .filter((el) => parseFloat(getComputedStyle(el).opacity) < 0.9)
        .map((el) => el.className));
    if (hidden.length) {
      fail(`${name}: без JS на экране прозрачных блоков — ${hidden.length} (${hidden[0]})`);
    }
  }

  await ctx.close();
}

/* ==========================================================================
   Появление при прокрутке доводит блок до конца
   ==========================================================================

   Обратная сторона той же анимации: блок, полностью попавший в экран,
   обязан быть непрозрачным. Если диапазон animation-range задан так,
   что высокий блок не успевает дойти до конца, он останется висеть
   полупрозрачным — и это заметно только при настоящей прокрутке. */

for (const name of ['index', 'catalog', 'contacts']) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(DIR, name + '.html'), { waitUntil: 'load' });
  await page.addStyleTag({ content: '*{scroll-behavior:auto !important}' });
  await page.waitForTimeout(200);

  const height = await page.evaluate(() => document.body.scrollHeight);
  for (let y = 0; y < height; y += 500) {
    await page.evaluate((v) => window.scrollTo(0, v), y);
    await page.waitForTimeout(120);
    const stuck = await page.evaluate(() =>
      [...document.querySelectorAll('.reveal')]
        .filter((el) => {
          const r = el.getBoundingClientRect();
          return r.height > 0 && r.top >= 0 && r.bottom <= innerHeight;
        })
        .filter((el) => parseFloat(getComputedStyle(el).opacity) < 0.95)
        .map((el) => el.className + ' — ' + getComputedStyle(el).opacity));
    if (stuck.length) {
      fail(`${name}: блок целиком на экране, но не проявился — ${stuck[0]}`);
      break;
    }
  }

  await ctx.close();
}

/* ==========================================================================
   Режим работы магазинов
   ==========================================================================

   Отметка «сейчас открыто» зависит от времени, то есть проверить её
   вживую можно только дождавшись субботы. Поэтому логика вынесена
   в отдельную функцию и прогоняется на заданных моментах — включая
   границы открытия и закрытия и разницу Чубарова с остальными
   (там выходные начинаются в 10:00, а не в 9:00). */

{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(DIR, 'contacts.html'), { waitUntil: 'load' });
  await page.waitForTimeout(300);

  const WD = '09:00-19:00';
  const WE = '09:00-18:00';
  const WE_LATE = '10:00-18:00';

  /* день недели (0 — воскресенье), минуты от полуночи, часы, ожидание */
  const cases = [
    [1, 8 * 60 + 59, WE, false, 'откроется в 9:00'],
    [1, 9 * 60, WE, true, 'до 19:00'],
    [1, 18 * 60 + 59, WE, true, 'до 19:00'],
    [1, 19 * 60, WE, false, 'завтра с 9:00'],
    [5, 19 * 60 + 30, WE_LATE, false, 'завтра с 10:00'],
    [6, 9 * 60 + 30, WE, true, 'до 18:00'],
    [6, 9 * 60 + 30, WE_LATE, false, 'откроется в 10:00'],
    [6, 18 * 60, WE_LATE, false, 'завтра с 10:00'],
    [0, 18 * 60 + 10, WE_LATE, false, 'завтра с 9:00'],
  ];

  for (const [day, minutes, weekend, shouldBeOpen, expect] of cases) {
    const got = await page.evaluate(([wd, we, d, m]) =>
      window.sgShopState(wd, we, { day: d, minutes: m }), [WD, weekend, day, minutes]);
    const when = `день ${day}, ${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`;
    if (got.open !== shouldBeOpen) {
      fail(`режим работы (${when}, выходные ${weekend}): «${got.text}», а должно быть ` +
           (shouldBeOpen ? 'открыто' : 'закрыто'));
    }
    if (!got.text.includes(expect)) {
      fail(`режим работы (${when}, выходные ${weekend}): «${got.text}», ожидалось «${expect}»`);
    }
  }

  /* И сама разметка: часы должны стоять у каждой карточки, а старого
     пустого места «режим работы — нужен от заказчика» остаться не должно. */
  const marks = await page.evaluate(() => ({
    карточек: document.querySelectorAll('[data-hours-weekday]').length,
    пустыхМест: document.body.innerHTML.includes('режим работы'),
  }));
  if (marks.карточек !== 3) fail(`контакты: часы стоят у ${marks.карточек} магазинов из трёх`);
  if (marks.пустыхМест) fail('контакты: осталось пустое место вместо режима работы');

  await ctx.close();
}

/* ==========================================================================
   Ничего не прячется под липкой шапкой
   ==========================================================================

   Два места, где числа были подобраны под широкий экран и держались
   только там:

   - scroll-padding-top стоял 96 px на все ширины, а шапка держится 130 px
     на телефоне и 142 на планшете. Переход по ссылке «Перейти
     к содержимому» — первое, чем пользуется человек с клавиатуры —
     оставлял цель на 34-46 px под шапкой;
   - панель фильтров прилипала на top: 16px при шапке в 70 px, то есть
     строка «Фильтры / Сбросить» была закрыта всегда.

   Обе проверки смотрят на настоящие пиксели: где кромка шапки и где
   верх того, к чему перешли. */

for (const width of [390, 768, 1280]) {
  const ctx = await browser.newContext({ viewport: { width, height: 900 } });
  const page = await ctx.newPage();

  for (const name of PAGES) {
    await page.goto('file://' + path.join(DIR, name + '.html'), { waitUntil: 'load' });
    await page.addStyleTag({ content: '*{scroll-behavior:auto !important}' });
    await page.waitForTimeout(150);

    const hidden = await page.evaluate(() => {
      location.hash = '#main';
      return new Promise((done) => setTimeout(() => {
        const main = document.querySelector('#main');
        if (!main) return done(null);
        const header = document.querySelector('.site-header');
        done(Math.round(header.getBoundingClientRect().bottom - main.getBoundingClientRect().top));
      }, 400));
    });

    if (hidden === null) fail(`${name}: нет цели #main для ссылки «Перейти к содержимому»`);
    else if (hidden > 1) fail(`${name} (${width}px): после перехода к содержимому цель на ${hidden} px под шапкой`);
  }

  await ctx.close();
}

/* Панель фильтров: прилипает под шапкой, целиком помещается в экран
   и не уносит кнопку «Сбросить» за его край. */
for (const width of [1024, 1280, 1440, 1920]) {
  const ctx = await browser.newContext({ viewport: { width, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(DIR, 'catalog.html'), { waitUntil: 'load' });
  await page.addStyleTag({ content: '*{scroll-behavior:auto !important}' });
  await page.waitForTimeout(200);
  /* Прокручиваем не на глазок: у липкого блока есть свой участок —
     он кончается там, где кончается колонка. На 1920 px колонка ниже
     (товары идут в больше колонок), и фиксированные 1000 px оказывались
     уже за её концом, где панель открепляется совершенно законно.
     Берём середину участка. */
  const target = await page.evaluate(() => {
    const layout = document.querySelector('.catalog-layout');
    const panel = document.querySelector('.filters');
    const top = layout.getBoundingClientRect().top + scrollY;
    const range = layout.getBoundingClientRect().height - panel.getBoundingClientRect().height;
    return range > 200 ? Math.round(top + range / 2) : null;
  });

  if (target === null) {
    fail(`фильтры (${width}px): колонка короче панели — липкости негде работать`);
    await ctx.close();
    continue;
  }

  await page.evaluate((y) => window.scrollTo(0, y), target);
  await page.waitForTimeout(600);

  const r = await page.evaluate(() => {
    const panel = document.querySelector('.filters');
    const reset = document.querySelector('.filters__reset');
    const header = document.querySelector('.site-header');
    const p = panel.getBoundingClientRect();
    const b = reset.getBoundingClientRect();
    const h = header.getBoundingClientRect();
    return {
      подШапкой: Math.round(h.bottom - p.top),
      вышеЭкрана: Math.round(p.height - innerHeight),
      сбросВиден: b.top >= h.bottom - 1 && b.bottom <= innerHeight,
    };
  });

  if (r.подШапкой > 1) fail(`фильтры (${width}px): панель заехала под шапку на ${r.подШапкой} px`);
  if (r.вышеЭкрана > 0) fail(`фильтры (${width}px): панель на ${r.вышеЭкрана} px выше экрана — липкость ничего не даёт`);
  if (!r.сбросВиден) fail(`фильтры (${width}px): кнопка «Сбросить» не видна при прокрутке`);

  await ctx.close();
}

/* Липкая шапка при прокрутке сжимается — и на этом однажды сломалась.

   Сжимаясь, шапка теряет до 95 px высоты. Браузер честно возвращает
   страницу на место: содержимое над экраном стало короче, и он вычитает
   ту же величину из прокрутки, чтобы картинка под курсором не прыгнула.
   С одним порогом получалась карусель — сжались, прокрутка сама упала
   ниже порога, разжались, прокрутка вернулась, сжались, — десятки раз
   в секунду. Выглядело как «страница лагает при прокрутке», и увидел
   это заказчик, а не проверки.

   Проверяем два следствия: шапка переключается один раз за проход,
   и переключается мгновенно. Плавный переход высоты или ширины стоил бы
   полного пересчёта раскладки на каждом кадре — под липкой шапкой это
   пересчёт всей страницы. */
for (const width of [390, 768, 1280]) {
  const ctx = await browser.newContext({ viewport: { width, height: 800 } });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(DIR, 'index.html'), { waitUntil: 'load' });
  await page.waitForTimeout(400);

  await page.evaluate(() => {
    window.__flips = 0;
    const header = document.querySelector('[data-header]');
    let was = header.classList.contains('is-compact');
    const tick = () => {
      const now = header.classList.contains('is-compact');
      if (now !== was) { window.__flips++; was = now; }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

  /* Колесом, а не window.scrollTo: поправку прокрутки браузер вносит
     только на настоящий ввод, и программной прокруткой эту ошибку
     не увидеть — мы сами перетираем его поправку каждым кадром. */
  await page.mouse.move(Math.round(width / 2), 400);
  for (let i = 0; i < 16; i++) {
    await page.mouse.wheel(0, 30);
    await page.waitForTimeout(70);
  }
  await page.waitForTimeout(300);
  const down = await page.evaluate(() => window.__flips);
  if (down > 1) fail(`шапка (${width}px): при прокрутке вниз переключилась ${down} раз вместо одного`);

  await page.evaluate(() => { window.__flips = 0; });
  for (let i = 0; i < 16; i++) {
    await page.mouse.wheel(0, -30);
    await page.waitForTimeout(70);
  }
  await page.waitForTimeout(300);
  const up = await page.evaluate(() => window.__flips);
  if (up > 1) fail(`шапка (${width}px): при прокрутке вверх переключилась ${up} раз вместо одного`);

  const slow = await page.evaluate(() => {
    const parts = ['.site-header', '.header-util', '.stripe-band', '.header-main',
      '.header-main__inner', '.header-quick', '.site-logo img'];
    const heavy = /^(all|width|height|padding|margin|inset|top|left|right|bottom)/;
    const found = [];
    for (const sel of parts) {
      const el = document.querySelector(sel);
      if (!el) continue;
      const css = getComputedStyle(el);
      /* transition-property сам по себе ничего не значит: без перехода
         он равен `all`, это его начальное значение. Смотреть надо пару
         «свойство + длительность». */
      const props = css.transitionProperty.split(',').map((x) => x.trim());
      const times = css.transitionDuration.split(',').map((x) => parseFloat(x) || 0);
      props.forEach((prop, i) => {
        const time = times[i % times.length] || 0;
        if (time > 0 && heavy.test(prop)) found.push(`${sel} → ${prop} ${time}s`);
      });
    }
    return found;
  });
  for (const f of slow) {
    fail(`шапка (${width}px): переход, пересчитывающий раскладку каждый кадр: ${f}`);
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

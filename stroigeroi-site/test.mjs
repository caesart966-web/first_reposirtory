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

      /* Ошибки форм — только после попытки отправки. Смотрим на display
         самого сообщения, а не на видимость: сообщение в закрытом окне
         «Заказать звонок» тоже не должно быть готово показаться. */
      const early = await page.evaluate(() => [...document.querySelectorAll('.form__error')]
        .filter((e) => getComputedStyle(e).display !== 'none')
        .map((e) => e.textContent.trim()));
      if (early.length) fail(`${name}: ошибки форм видны до отправки — ${[...new Set(early)].join('; ')}`);
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
    (await walk('главная → каталог', () => page.click('.first-screen a[href="catalog.html"]'), 'catalog.html')) &&
    (await walk('каталог → карточка', () => page.click('.product-card__title'), 'product.html')) &&
    (await walk('карточка → корзина', async () => {
      await page.click('[data-add="cart"]');
      await page.waitForTimeout(200);
      await page.click('a[href="cart.html"]');
    }, 'cart.html')) &&
    (await walk('корзина → оформление', () => page.click('a[href="checkout.html"]'), 'checkout.html')) &&
    (await walk('оформление → заказ принят', async () => {
      await page.fill('#co-name', 'Иван');
      await page.fill('#co-phone', '9638319999');
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
    } else {
      const consent = await page.evaluate(() => [...document.querySelectorAll('form.checkout .consent .form__error')]
        .map((e) => getComputedStyle(e).display !== 'none'));
      if (!consent.length || !consent.every(Boolean)) fail('сценарий: без галочки согласия сообщение под ней не показалось');
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
   Строительный калькулятор: 14 расчётов, склонения, адреса, список, отправка
   ==========================================================================

   Числа в ожиданиях посчитаны руками, формула — в комментарии рядом.
   Каждое поле заполняется тем же путём, каким его заполнит человек:
   число — вводом, список — выбором, переключатель — щелчком. */

{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  const pageUrl = 'file://' + path.join(DIR, 'calculator.html');
  await page.goto(pageUrl, { waitUntil: 'load' });
  await page.evaluate(() => localStorage.clear());
  await page.goto(pageUrl, { waitUntil: 'load' });
  await page.waitForTimeout(300);

  const picks = await page.$$eval('[data-calc-pick]', (b) => b.length);
  if (picks !== 14) fail(`калькулятор: карточек выбора ${picks}, а калькуляторов 14`);

  const open = async (id) => {
    await page.click(`[data-calc-pick="${id}"]`);
    await page.waitForTimeout(120);
  };
  /* Поле в «Дополнительных параметрах» сначала раскрываем — как человек. */
  const set = async (values) => {
    for (const [name, value] of Object.entries(values)) {
      const el = await page.$(`[data-calc-form] [name="${name}"]`);
      if (!el) { fail(`калькулятор: нет поля ${name}`); continue; }
      await el.evaluate((n) => { const d = n.closest('details'); if (d) d.open = true; });
      const kind = await el.evaluate((n) => (n.tagName === 'SELECT' ? 'select' : n.type));
      if (kind === 'select') await page.selectOption(`[data-calc-form] select[name="${name}"]`, value);
      else if (kind === 'radio') await page.check(`[data-calc-form] input[name="${name}"][value="${value}"]`);
      else await page.fill(`[data-calc-form] input[name="${name}"]`, value);
    }
    await page.waitForTimeout(150);
  };
  const read = () =>
    page.evaluate(() => {
      const clean = (t) => t.replace(/ /g, ' ').replace(/\s+/g, ' ').trim();
      const pairs = (sel) => [...document.querySelectorAll(sel)].map((li) => [clean(li.children[0].textContent), clean(li.children[1].textContent)]);
      return {
        eyebrow: clean(document.querySelector('[data-calc-eyebrow]').textContent),
        answer: clean(document.querySelector('[data-calc-answer]').textContent),
        buy: pairs('[data-calc-buy] li'),
        rows: pairs('[data-calc-rows] li'),
        note: clean(document.querySelector('[data-calc-note]').textContent),
      };
    });
  const expect = (label, got, want) => {
    if (got !== want) fail(`калькулятор, ${label}: ждали «${want}», получено «${got}»`);
  };
  const buyOf = (r, name) => (r.buy.find((b) => b[0].startsWith(name)) || [])[1];
  const noDots = (r, label) => {
    for (const [a, b] of r.rows.concat(r.buy)) {
      if (/\d\.\d/.test(a + b)) fail(`калькулятор, ${label}: точка вместо запятой — «${a} ${b}»`);
    }
  };

  /* Гипсокартон — весь комплект, а не одни листы: «там ещё идёт профиль»,
     сказал заказчик. По умолчанию стена 4 × 2,7 м на каркасе ПС + ПН:
     10,8 м² × 1,1 ÷ 3 = 3,96 → 4 листа; стоек 4 ÷ 0,6 → 7 + 1 = 8;
     ПН 2 × (4 ÷ 3 → 2) = 4; саморезов 4 листа × 33 = 132; клопов 8 × 4
     = 32; дюбелей 2 × (4 ÷ 0,5 + 1) по полу и потолку + 2 × (2,7 ÷ 0,5 → 6
     + 1) по крайним стойкам = 32; лента 2 × (4 + 2,7) = 13,4 м; серпянка
     3 шва × 2,7 + 1 × 4 = 12,1 м. */
  await open('gkl');
  let r = await read();
  expect('гипсокартон по умолчанию', r.answer, '4 листа');
  const kit = (label, r, want) => {
    for (const [name, qty] of Object.entries(want)) {
      const got = qty === null ? (r.buy.some((b) => b[0].startsWith(name)) ? 'есть' : null) : buyOf(r, name);
      if (got !== (qty === null ? null : qty)) fail(`калькулятор, ${label}: «${name}» — ждали ${qty === null ? 'нет в списке' : '«' + qty + '»'}, получено «${got}»`);
    }
  };
  kit('гипсокартон, стена на ПС', r, {
    'Профиль стоечный ПС, 3 м': '8 шт.', 'Профиль направляющий ПН, 3 м': '4 шт.', 'Саморезы для гипсокартона': '132 шт.',
    'Саморезы-клопы': '32 шт.', 'Дюбель-гвозди': '32 шт.', 'Лента уплотнительная': '13,4 м', 'Серпянка': '12,1 м', 'Подвесы': null,
  });
  if (!/Шпатлёвку и грунтовку посчитаем по расходу с упаковки/.test(r.note)) fail(`калькулятор, гипсокартон: не сказано, как посчитать шпатлёвку и грунтовку — «${r.note}»`);

  /* Каркас ПП на прямых подвесах: профилей те же 8, подвесов 2,7 ÷ 0,6
     → 5 − 1 = 4 на профиль (концы держат направляющие), всего 32; дюбелей
     18 по направляющим + 2 × 32 = 82; клопов 32 + 2 × 32 = 96; лента —
     только под направляющими, 8 м. */
  await set({ mount: 'pp' });
  kit('гипсокартон, стена на ПП', await read(), {
    'Профиль потолочный ПП 60 × 27, 3 м': '8 шт.', 'Профиль направляющий ПН 28 × 27, 3 м': '4 шт.', 'Подвесы прямые': '32 шт.',
    'Дюбель-гвозди': '82 шт.', 'Саморезы-клопы': '96 шт.', 'Лента уплотнительная': '8 м', 'Профиль стоечный': null,
  });

  /* Стены комнаты 4 × 3 × 2,7: 37,8 м² × 1,1 ÷ 3 = 13,9 → 14 листов;
     стоек 8 + 6 + 8 + 6 = 28 — у каждой стены свои крайние; ПН по периметру
     подряд: 2 × (14 ÷ 3 → 5) = 10; дюбели только по полу и потолку:
     2 × (9 + 7 + 9 + 7) = 64; серпянка 2 × 12,1 + 2 × 8,4 и 4 угла × 2,7
     = 51,8 м. */
  await set({ surf: 'walls', mount: 'ps' });
  r = await read();
  expect('гипсокартон, стены комнаты', r.answer, '14 листов');
  kit('гипсокартон, стены комнаты', r, {
    'Профиль стоечный ПС': '28 шт.', 'Профиль направляющий ПН': '10 шт.', 'Дюбель-гвозди': '64 шт.', 'Лента уплотнительная': '28 м', 'Серпянка': '51,8 м',
  });

  /* Потолок 4 × 3: 12 × 1,1 ÷ 3 = 4,4 → 5 листов; каркас потолка
     не считаем и говорим об этом; выбора крепления нет. Швы: листы вдоль
     длинной стены — 2 шва по 4 м и 1 поперёк по 3 м = 11 м. */
  await set({ surf: 'ceiling' });
  r = await read();
  expect('гипсокартон, потолок', r.answer, '5 листов');
  kit('гипсокартон, потолок', r, { 'Серпянка': '11 м', 'Профиль': null, 'Саморезы': null });
  if (!/Каркас потолка здесь не считаем/.test(r.note)) fail(`калькулятор, гипсокартон на потолок: не сказано, что каркас не посчитан — «${r.note}»`);
  if (!(await page.evaluate(() => document.querySelector('[data-field="mount"]').hidden))) fail('калькулятор, гипсокартон на потолок: выбор крепления листов должен прятаться');

  /* На клей: без каркаса и крепежа; клей — по расходу с мешка:
     10,8 × 5 = 54 кг → 2 мешка по 30 кг. Два слоя на клей не сажают —
     переключатель прячется, листов по-прежнему 4. */
  await set({ surf: 'wall', layers: '2', mount: 'glue' });
  r = await read();
  expect('гипсокартон на клей', r.answer, '4 листа');
  if (!/Клей посчитаем по расходу с мешка/.test(r.note)) fail(`калькулятор, гипсокартон на клей без расхода — «${r.note}»`);
  await set({ glueRate: '5', glueBag: '30' });
  kit('гипсокартон на клей', await read(), { 'Клей для гипсокартона, мешки по 30 кг': '2 мешка', 'Профиль': null, 'Дюбель-гвозди': null, 'Серпянка': '12,1 м' });
  await set({ mount: 'none' });
  r = await read();
  if (r.buy.map((b) => b[0]).join('|') !== 'Гипсокартон 1200 × 2500 мм|Серпянка для швов') fail(`калькулятор, только листы — ${JSON.stringify(r.buy)}`);
  expect('гипсокартон, только листы в два слоя', r.answer, '8 листов');

  /* Отделка: шпатлёвка 10,8 × 0,3 = 3,24 кг — 3,2 кг, с мешком 25 кг —
     1 мешок; грунтовка 10,8 × 150 мл = 1,62 л → канистра 10 л; уголок —
     5,4 м ÷ 3 = 1,8 → 2 шт.; утеплитель — площадь обшивки. */
  await page.click('[data-calc-reset]');
  await set({ puttyRate: '0,3', insul: '1', corners: '5,4' });
  kit('гипсокартон, шпатлёвка без мешка', await read(), { 'Шпатлёвка для швов': '3,2 кг', 'Утеплитель': '10,8 м²', 'Уголок перфорированный, 3 м': '2 шт.' });
  await set({ puttyBag: '25', primerRate: '150', primerCan: '10' });
  r = await read();
  kit('гипсокартон, отделка', r, { 'Шпатлёвка для швов, мешки по 25 кг': '1 мешок', 'Грунтовка, канистры по 10 л': '1 канистра' });
  if (/посчитаем по расходу/.test(r.note)) fail(`калькулятор, гипсокартон: расход вписан, а подсказка осталась — «${r.note}»`);
  await set({ primerRate: '0,15' });
  if (!(await page.evaluate(() => !document.querySelector('[data-warn-for="primerRate"]').hidden))) fail('калькулятор: грунтовка 0,15 мл на 1 м² — нет подсказки, что это литры');
  noDots(await read(), 'гипсокартон');
  await page.click('[data-calc-reset]');

  /* По площади: 20 м² + 10 % = 22 ÷ 3 = 7,3 → 8. Склонение: 57 м² → 20,9
     → «21 лист»; 60 → «22 листа» (было «22 листов»); 90 м² + 10 % = ровно
     99 ÷ 3 = 33, а дробь 33,00000000000001 давала 34. Запятая на входе.
     Каркас по площади — как у одной стены длиной площадь ÷ высота. */
  await set({ surf: 'area' });
  r = await read();
  expect('гипсокартон 20 м²', r.answer, '8 листов');
  expect('гипсокартон 20 м², каркас', (r.rows.find((x) => x[0].startsWith('Каркас')) || [])[1], '7,41 м × 2,7 м');
  for (const [area, want] of [['57', '21 лист'], ['60', '22 листа'], ['90', '33 листа'], ['18,5', '7 листов']]) {
    await set({ area });
    expect(`гипсокартон ${area} м²`, (await read()).answer, want);
  }
  await page.click('[data-calc-reset]');

  /* Перегородка 4 × 2,7 м, две стороны, лист 1200 × 2500: 10,8 × 2 × 1,1 ÷ 3
     = 7,9 → 8 листов; стоек 4 ÷ 0,6 → 7 + 1 = 8; ПН 2 × (4 ÷ 3 → 2) = 4;
     саморезов на лист 3 стойки × (2,5 ÷ 0,25 + 1) = 33, × 8 = 264;
     серпянка (3 шва × 2,7 + 1 × 4) × 2 = 24,2 м. Формула каркаса та же,
     что у гипсокартона. Шпатлёвка — на обе стороны: 21,6 × 0,3 = 6,5 кг. */
  await open('frame');
  r = await read();
  expect('перегородка, листы', r.answer, '8 листов');
  expect('перегородка, стойки', buyOf(r, 'Профиль стоечный'), '8 шт.');
  expect('перегородка, направляющие', buyOf(r, 'Профиль направляющий'), '4 шт.');
  expect('перегородка, саморезы', buyOf(r, 'Саморезы для гипсокартона'), '264 шт.');
  expect('перегородка, дюбели', buyOf(r, 'Дюбель-гвозди'), '32 шт.');
  expect('перегородка, серпянка', buyOf(r, 'Серпянка'), '24,2 м');
  expect('перегородка, клопы', buyOf(r, 'Саморезы-клопы'), '32 шт.');
  await set({ puttyRate: '0,3', insul: '1' });
  r = await read();
  expect('перегородка, шпатлёвка на две стороны', buyOf(r, 'Шпатлёвка для швов'), '6,5 кг');
  expect('перегородка, звукоизоляция', buyOf(r, 'Утеплитель'), '10,8 м²');
  await page.click('[data-calc-reset]');

  /* Смеси: без расхода — не считаем; 120 × 8 × 1,4 × 1,1 ÷ 30 = 49,3 → 50;
     запас у вкладки свой: 0 % → 1344 ÷ 30 = 44,8 → 45. */
  await open('mix');
  r = await read();
  expect('смеси без расхода', r.answer, '—');
  if (!/расход и вес мешка/.test(r.note)) fail(`калькулятор, смеси без расхода: не сказано, чего не хватает — «${r.note}»`);
  await set({ area: '120', thick: '8', usage: '1,4', bag: '30' });
  expect('смеси', (await read()).answer, '50 мешков');
  await set({ reserve: '0' });
  expect('смеси без запаса', (await read()).answer, '45 мешков');

  /* Краска: 30 м² × 2 слоя ÷ 10 м²/л × 1,1 = 6,6 л → банки по 2,5 л: 3.
     Расход «150 мл на 1 м²»: 30 × 2 × 0,15 × 1,1 = 9,9 л → 4 банки.
     По комнате 4 × 3 × 2,7 минус 3 м² окон: 34,8 м² → 7,66 л → 4 банки. */
  await open('paint');
  await set({ rate: '10' });
  expect('краска, литры', (await read()).answer, '6,6 л');
  await set({ can: '2,5' });
  expect('краска, банки', (await read()).answer, '3 банки');
  await set({ rateUnit: 'mlm2', rate: '150' });
  expect('краска, расход в мл', (await read()).answer, '4 банки');
  await set({ rateUnit: 'm2l', rate: '10', mode: 'room' });
  r = await read();
  expect('краска по комнате', r.answer, '4 банки');
  expect('краска, стены по комнате', (r.rows.find((x) => x[0].startsWith('Стены')) || [])[1], '34,8 м²');

  /* Обои 4 × 3 × 2,7: периметр 14 м, полоса 2,8 м, из рулона 10,05 м — 3
     полосы; полос 14 ÷ 0,53 → 27; рулонов 27 ÷ 3 → 9. Метровые — 14 полос,
     5 рулонов. Раппорт 64 см: полоса 3,44 м, из рулона 2, рулонов 14. */
  await open('wallpaper');
  expect('обои', (await read()).answer, '9 рулонов');
  await set({ roll: '1.06x10.05' });
  expect('обои метровые', (await read()).answer, '5 рулонов');
  await set({ roll: '0.53x10.05', rapport: '64', glue: '6' });
  r = await read();
  expect('обои с раппортом', r.answer, '14 рулонов');
  expect('обои, клей', buyOf(r, 'Клей для обоев'), '3 упаковки');

  /* Плитка 300 × 300, шов 2: 10 × 1,1 ÷ 0,302² = 120,6 → «121 плитка»;
     по 11 в упаковке — 11 упаковок; клей 10 × 4 × 1,1 = 44 кг → 2 мешка
     по 25; затирка (600 ÷ 90 000) × 8 × 2 × 1,6 × 10 × 1,1 = 1,88 кг →
     1 упаковка по 2 кг. */
  await open('tile');
  expect('плитка', (await read()).answer, '121 плитка');
  await set({ perPack: '11', glueRate: '4', glueBag: '25', thick: '8', density: '1,6', groutPack: '2' });
  r = await read();
  expect('плитка, упаковки', r.answer, '11 упаковок');
  expect('плитка, клей', buyOf(r, 'Плиточный клей'), '2 мешка');
  expect('плитка, затирка', buyOf(r, 'Затирка'), '1 упаковка');
  noDots(r, 'плитка');

  /* Ламинат 5 × 4: 22 м² с запасом; по 2 м² — 11 упаковок; подложка по 10 м²
     — 3; плинтус (18 − 0,8) × 1,1 ÷ 2,5 = 7,6 → 8. */
  await open('floor');
  expect('ламинат без упаковки', (await read()).answer, '22 м²');
  await set({ pack: '2', under: '10' });
  r = await read();
  expect('ламинат', r.answer, '11 упаковок');
  expect('ламинат, подложка', buyOf(r, 'Подложка'), '3 упаковки');
  expect('ламинат, плинтус', buyOf(r, 'Плинтус'), '8 шт.');

  /* «Армстронг» 5 × 4: ячеек 9 × 7 = 63 плиты; линий главного профиля
     4 ÷ 1,2 → 4 − 1 = 3, по 2 профиля 3,6 м — 6; поперечных 1,2: 8 линий ×
     4 = 32; 0,6: (6 − 3) × 9 = 27; уголок 2 × 2 + 2 × 2 = 8; подвесов
     3 × (5 ÷ 1,2 → 5 + 1) = 18. Светильники вместо 4 плит — 59 плит.
     Комната 1 × 1: четыре ячейки, главного профиля и подвесов нет. */
  await open('ceiling');
  r = await read();
  expect('армстронг, плиты', r.answer, '63 плиты');
  expect('армстронг, главный', buyOf(r, 'Профиль главный'), '6 шт.');
  expect('армстронг, 1,2', buyOf(r, 'Профиль поперечный 1,2'), '32 шт.');
  expect('армстронг, 0,6', buyOf(r, 'Профиль поперечный 0,6'), '27 шт.');
  expect('армстронг, уголок', buyOf(r, 'Уголок'), '8 шт.');
  expect('армстронг, подвесы', buyOf(r, 'Подвесы'), '18 шт.');
  await set({ lamps: '4' });
  r = await read();
  expect('армстронг со светильниками', r.answer, '59 плит');
  expect('армстронг, светильники', buyOf(r, 'Светильники'), '4 шт.');
  await set({ lamps: '0', length: '1', width: '1' });
  r = await read();
  expect('армстронг 1 × 1', r.answer, '4 плиты');
  if (buyOf(r, 'Подвесы') || buyOf(r, 'Профиль главный')) fail('калькулятор, армстронг 1 × 1: главного профиля и подвесов быть не должно');

  /* Панели 10 м² + 10 % ÷ (3 × 0,25) = 14,7 → 15; по 10 в упаковке — 2. */
  await open('panels');
  expect('панели', (await read()).answer, '15 панелей');
  await set({ perPack: '10' });
  expect('панели, упаковки', buyOf(await read(), 'Это упаковок'), '2 упаковки');

  /* Кирпич: 10 × 2,7 = 27 м², в кирпич — 2 ÷ (0,26 × 0,075) = 102,6 на м²,
     с запасом 5 % — 2908; раствор 27 × 0,25 − 2769 × 0,00195 = 1,35 м³.
     Блок 600 × 200 × 300 на клею, шов 3: 27 ÷ (0,603 × 0,203) × 1,05 = 231,6
     → 232; клей 0,16 м³. */
  await open('masonry');
  r = await read();
  expect('кирпич', r.answer, '2 908 кирпичей');
  expect('кирпич, раствор', buyOf(r, 'Раствор'), '1,35 м³');
  await set({ mat: 'block', joint: '3' });
  r = await read();
  expect('блоки', r.answer, '232 блока');
  expect('блоки, клей', buyOf(r, 'Раствор или клей'), '0,16 м³');

  /* Бетон: плита 6 × 6 × 0,2 × 1,05 = 7,56 м³; лента 24 × 0,4 × 0,8 × 1,05
     = 8,06; столбы 12 × π × 0,1² × 1,5 × 1,05 = 0,59; плита из мешков
     с выходом 20 л — 7560 ÷ 20 = 378. */
  await open('concrete');
  expect('бетон, плита', (await read()).answer, '7,56 м³');
  await set({ kind: 'strip' });
  expect('бетон, лента', (await read()).answer, '8,06 м³');
  await set({ kind: 'piles' });
  expect('бетон, столбы', (await read()).answer, '0,59 м³');
  await set({ kind: 'slab', bag: '20' });
  expect('бетон, мешки', buyOf(await read(), 'Сухая смесь'), '378 мешков');

  /* Утеплитель: 100 мм плитами по 50 — 2 слоя; 50 × 2 × 1,05 = 105 м²;
     по 6 м² в упаковке — 17,5 → 18. */
  await open('insulation');
  expect('утеплитель без упаковки', (await read()).answer, '105 м²');
  await set({ pack: '6' });
  expect('утеплитель', (await read()).answer, '18 упаковок');

  /* Кровля 8 × 4, два ската, рабочая ширина 1,1: 8 ÷ 1,1 → 8 листов в ряд,
     16 на крышу; конёк 8 ÷ 1,9 → 5. Листы по 1,5 м с нахлёстом 20 см:
     рядов (4 − 0,2) ÷ 1,3 → 3, листов 48. */
  await open('roof');
  expect('кровля без ширины листа', (await read()).answer, '—');
  await set({ useful: '1,1' });
  r = await read();
  expect('кровля', r.answer, '16 листов');
  expect('кровля, конёк', buyOf(r, 'Конёк'), '5 шт.');
  await set({ sheetLen: '1,5' });
  expect('кровля, короткие листы', (await read()).answer, '48 листов');

  /* Радиаторы: 15 × 2,7 × 41 × 1,15 = 1909,6 → 1910 Вт; ÷ 180 → 11 секций;
     кирпичный дом 15 × 2,7 × 34 × 1,15 = 1583,6 → 9; угловая +20 % — 2292 Вт
     → 13; 20 м²: 2547 Вт ÷ 125 → «21 секция», ÷ 120 → «22 секции». */
  await open('radiator');
  r = await read();
  expect('радиаторы без мощности', `${r.eyebrow}: ${r.answer}`, 'Нужно тепла: 1 910 Вт');
  if (!r.rows.some((x) => x[0] === 'Запас' && x[1] === '15 %')) fail('калькулятор, радиаторы: в расчёте нет строки «Запас 15 %»');
  await set({ power: '180' });
  expect('радиаторы', (await read()).answer, '11 секций');
  await set({ norm: '34' });
  expect('радиаторы, кирпичный дом', (await read()).answer, '9 секций');
  await set({ norm: '41', walls: '1.2' });
  expect('радиаторы, угловая', (await read()).answer, '13 секций');
  await set({ walls: '1', area: '20', power: '125' });
  expect('радиаторы, 125 Вт', (await read()).answer, '21 секция');
  await set({ power: '120' });
  expect('радиаторы, 120 Вт', (await read()).answer, '22 секции');

  /* Адрес: калькулятор и то, что отличается от значений по умолчанию
     (через 0,4 с после ввода). При <base href> на главную (так в теме
     OpenCart) адрес всё равно собирается от самой страницы. */
  await page.waitForTimeout(500);
  if (new URL(page.url()).hash !== '#radiatory?area=20&power=120') fail(`калькулятор: у радиаторов адрес …#radiatory?area=20&power=120, получено ${page.url()}`);
  await page.evaluate(() => {
    const base = document.createElement('base');
    base.href = 'file:///nonexistent/';
    document.head.prepend(base);
  });
  await open('wallpaper');
  if (page.url() !== pageUrl + '#oboi?rapport=64&glue=6') fail(`калькулятор: при <base href> адрес должен остаться …calculator.html#oboi?rapport=64&glue=6, получено ${page.url()}`);

  /* Отправка менеджеру: окно звонка открывается, расчёт уходит полем message;
     если окно открыть другой кнопкой — поле пустое. */
  await page.click('[data-calc-result] [data-calc-send]');
  await page.waitForTimeout(200);
  const sent = await page.evaluate(() => ({
    open: !!document.querySelector('#modal-callback[open]'),
    message: (document.querySelector('#modal-callback form input[name="message"]') || {}).value || '',
    note: (el => (el && !el.hidden ? el.textContent : ''))(document.querySelector('[data-calc-attached]')),
  }));
  if (!sent.open) fail('калькулятор: «Отправить менеджеру» не открыло окно заявки');
  if (!/строительный калькулятор/.test(sent.message) || !/Обои/.test(sent.message)) fail(`калькулятор: к заявке не приложен расчёт — «${sent.message.slice(0, 80)}»`);
  if (!/приложен\s+расчёт\s+«Обои»/.test(sent.note)) fail(`калькулятор: в окне заявки не сказано, какой расчёт приложен — «${sent.note}»`);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);
  await page.evaluate(() => document.querySelector('[data-modal-open="modal-callback"]:not([data-calc-send])').click());
  await page.waitForTimeout(200);
  const plain = await page.evaluate(() => (document.querySelector('#modal-callback form input[name="message"]') || {}).value || '');
  if (plain) fail('калькулятор: обычная заявка на звонок ушла бы с чужим расчётом');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);

  /* Копирование: в буфере — текст расчёта. */
  await page.click('[data-calc-copy]');
  await page.waitForTimeout(300);
  const copied = await page.evaluate(() => navigator.clipboard.readText().catch(() => ''));
  if (copied && !/Обои: комната/.test(copied)) fail(`калькулятор: скопирован не тот текст — «${copied.slice(0, 80)}»`);
  if (copied && !copied.includes('Открыть расчёт: ' + pageUrl + '#oboi?length=4&width=3&height=2.7&doors=0&roll=0.53x10.05&rapport=64&trim=10&glue=6')) {
    fail(`калькулятор: в тексте расчёта нет ссылки со всеми размерами — «${copied.split('\n').pop()}»`);
  }
  const toastText = await page.evaluate(() => document.querySelector('[data-demo-note]').textContent);
  if (!/скопирован/.test(toastText)) fail(`калькулятор: после копирования нет сообщения, получено «${toastText}»`);

  /* Список покупок: два расчёта, переживает перезагрузку, удаление,
     печать только списка, очистка. */
  await open('ceiling');
  await page.click('[data-calc-add]');
  await open('frame');
  await page.click('[data-calc-add]');
  await page.waitForTimeout(500);
  const listed = await page.evaluate(() => ({
    shown: !document.querySelector('[data-calc-list]').hidden,
    entries: [...document.querySelectorAll('.calc-list__name')].map((n) => n.textContent),
    share: !document.querySelector('[data-calc-list-share]').hidden,
    count: document.querySelector('[data-calc-list-count]').textContent.replace(/ /g, ' '),
  }));
  if (!listed.shown || listed.entries.length !== 2 || listed.count !== '2 расчёта') fail(`калькулятор: список покупок — ${JSON.stringify(listed)}`);
  if (listed.share) fail('калькулятор: на компьютере меню «Поделиться» нет — кнопка в списке должна прятаться');
  await page.goto(pageUrl, { waitUntil: 'load' });
  await page.waitForTimeout(300);
  const kept = await page.$$eval('.calc-list__name', (n) => n.map((x) => x.textContent));
  if (kept.length !== 2) fail(`калькулятор: список покупок не пережил перезагрузку — ${JSON.stringify(kept)}`);
  const lastOpen = await page.getAttribute('[data-calc-pick="frame"]', 'aria-pressed');
  if (lastOpen !== 'true') fail('калькулятор: после перезагрузки должен открыться последний калькулятор');
  await page.evaluate(() => { window.print = () => { window.__printed = document.body.classList.contains('is-print-calc'); }; });
  await page.click('[data-calc-list-print]');
  if (!(await page.evaluate(() => window.__printed))) fail('калькулятор: печать списка не включила режим «только список»');
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
  await page.click('[data-calc-list-remove="0"]');
  const left = await page.$$eval('.calc-list__name', (n) => n.map((x) => x.textContent));
  if (left.length !== 1 || left[0] !== 'Перегородка') fail(`калькулятор: после удаления в списке — ${JSON.stringify(left)}`);
  /* Очистка — со второго нажатия: первое только спрашивает. */
  await page.click('[data-calc-list-clear]');
  const armed = await page.evaluate(() => ({
    shown: !document.querySelector('[data-calc-list]').hidden,
    text: document.querySelector('[data-calc-list-clear]').textContent,
  }));
  if (!armed.shown || armed.text !== 'Точно очистить?') fail(`калькулятор: первое нажатие «Очистить» должно спросить, а не стереть — ${JSON.stringify(armed)}`);
  await page.click('[data-calc-list-clear]');
  if (!(await page.evaluate(() => document.querySelector('[data-calc-list]').hidden))) fail('калькулятор: пустой список должен прятаться');

  /* Длинный список уходит в заявку целыми расчётами, пока помещается
     в 2000 знаков обработчика, и считать надо, как считает он: перевод
     строки браузер отправляет парой \r\n, а & " < > движок хранит
     сущностями. Поэтому меряем то, что браузер на самом деле отправит.
     Одиннадцать расчётов ниже — 1 905 знаков по счёту JS и 2 015 по счёту
     обработчика: без учёта \r\n ушли бы все, и заявку отклонили бы. */
  await page.evaluate(() => {
    const items = [];
    for (let i = 1; i <= 8; i++) items.push([`Позиция ${i}`, `${i} шт.`]);
    const entries = [];
    for (let i = 1; i <= 11; i++) entries.push({ title: `Расчёт ${i}`, summary: 'кухня', items });
    localStorage.setItem('sg-calc-list', JSON.stringify(entries));
  });
  await page.goto(pageUrl, { waitUntil: 'load' });
  await page.waitForTimeout(300);
  await page.click('[data-calc-list-send]');
  await page.waitForTimeout(200);
  const long = await page.evaluate(async () => {
    const form = document.querySelector('#modal-callback form');
    const body = await new Response(new FormData(form)).text();
    const m = body.match(/name="message"\r\n\r\n([\s\S]*?)\r\n--/);
    const value = m ? m[1] : '';
    const server = value.trim().replace(/[&"<>]/g, (ch) => ({ '&': '&amp;', '"': '&quot;', '<': '&lt;', '>': '&gt;' })[ch]);
    return {
      length: [...server].length,
      entries: (value.match(/^Расчёт \d+:/gm) || []).length,
      items: (value.match(/^— Позиция \d+:/gm) || []).length,
      tail: /И ещё \d+ расчёт/.test(value),
      note: document.querySelector('[data-calc-attached]').textContent.replace(/\u00a0/g, ' '),
    };
  });
  if (long.length > 2000) fail(`калькулятор: список уходит в заявку длиной ${long.length} — обработчик принимает до 2000 знаков и отклонил бы заявку целиком`);
  if (long.entries < 1 || long.entries >= 11 || long.items !== long.entries * 8 || !long.tail) {
    fail(`калькулятор: длинный список — в заявке ${long.entries} расчётов из 11 и ${long.items} строк из ${long.entries * 8}, приписка об остальных ${long.tail ? 'есть' : 'НЕТ'}`);
  }
  if (!new RegExp(`поместились ${long.entries} расчёт\\S* из 11`).test(long.note)) fail(`калькулятор: не сказано, сколько расчётов вошло в заявку — «${long.note}»`);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);
  await page.click('[data-calc-list-clear]');
  await page.click('[data-calc-list-clear]');

  /* Память полей и «Сбросить» */
  await open('gkl');
  await set({ surf: 'walls', length: '6' });
  await page.waitForTimeout(500);
  await page.goto(pageUrl, { waitUntil: 'load' });
  await page.waitForTimeout(300);
  expect('гипсокартон после перезагрузки', await page.inputValue('[data-calc-form] input[name="length"]'), '6');
  expect('гипсокартон после перезагрузки, что обшиваем', await page.evaluate(() => document.querySelector('[data-calc-form] input[name="surf"]:checked').value), 'walls');
  await page.click('[data-calc-reset]');
  await page.waitForTimeout(150);
  expect('гипсокартон после «Сбросить»', await page.inputValue('[data-calc-form] input[name="length"]'), '4');

  /* Гипсокартон до правки 34: площадь задавали «Знаю площадь» или «По
     размерам комнаты» (mode). Старые ссылки и память браузера открываются
     теми же размерами, а не значениями по умолчанию: 30 м² → 11 листов,
     потолок 5 × 3 → 15 × 1,1 ÷ 3 = 5,5 → 6. Вариант, которого больше нет
     (surf=both), не оставляет переключатель без выбора. В памяти старого
     вида «Знаю площадь» стояло рядом с невидимым surf=walls — открыться
     должна площадь, а не стены комнаты 5 × 4 × 3 (54 м², 20 листов). */
  {
    const octx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const op = await octx.newPage();
    op.on('pageerror', (e) => errors.push(e.message));
    const state = () => op.evaluate(() => ({
      surf: (document.querySelector('[data-calc-form] input[name="surf"]:checked') || {}).value || null,
      answer: document.querySelector('[data-calc-answer]').textContent.replace(/\u00a0/g, ' '),
    }));
    for (const [hash, want] of [
      ['#gipsokarton?area=30', { surf: 'area', answer: '11 листов' }],
      ['#gipsokarton?mode=room&surf=ceiling&length=5', { surf: 'ceiling', answer: '6 листов' }],
      ['#gipsokarton?mode=room&surf=both', { surf: 'walls', answer: '14 листов' }],
    ]) {
      await op.goto(pageUrl + hash, { waitUntil: 'load' });
      await op.waitForTimeout(300);
      const got = await state();
      if (JSON.stringify(got) !== JSON.stringify(want)) fail(`калькулятор: старая ссылка ${hash} — ${JSON.stringify(got)}`);
    }
    /* Память пишется через 0,4 с после расчёта — ждём, чтобы она не
       затёрла подложенную запись, и уходим со страницы совсем: переход
       по одной решётке остался бы на той же странице. */
    await op.waitForTimeout(500);
    await op.evaluate(() => localStorage.setItem('sg-calc-v-gkl', JSON.stringify({ mode: 'area', area: '30', surf: 'walls', length: '5', width: '4', height: '3', openings: '0', sheet: '2.5', layers: '1', reserve: '10', mount: 'нет-такого' })));
    await op.goto('about:blank');
    await op.goto(pageUrl + '#gipsokarton', { waitUntil: 'load' });
    await op.waitForTimeout(300);
    const kept = await state();
    if (kept.surf !== 'area' || kept.answer !== '11 листов') fail(`калькулятор: память гипсокартона до правки 34 — ${JSON.stringify(kept)}`);
    const mount = await op.evaluate(() => (document.querySelector('[data-calc-form] input[name="mount"]:checked') || {}).value || null);
    if (mount !== 'ps') fail(`калькулятор: в памяти вариант крепления, которого нет, — переключатель должен стоять на варианте по умолчанию, а стоит ${mount}`);
    await octx.close();
  }

  /* Старые адреса вкладок и ссылка «Калькулятор радиаторов» с карточки */
  for (const [hash, id] of [['gipsokarton', 'gkl'], ['smesi', 'mix'], ['radiatory', 'radiator'], ['armstrong', 'ceiling']]) {
    const direct = await ctx.newPage();
    await direct.goto(pageUrl + '#' + hash, { waitUntil: 'load' });
    await direct.waitForTimeout(250);
    if ((await direct.getAttribute(`[data-calc-pick="${id}"]`, 'aria-pressed')) !== 'true') fail(`калькулятор: ссылка …#${hash} должна открывать ${id}`);
    await direct.close();
  }

  /* Ссылка на расчёт. По ссылке открываются те же размеры; чего в ссылке
     нет — по умолчанию; непонятное (не число, нет такого варианта)
     пропускается. Стёртое поле передаётся пустым. Ссылку можно вставить
     и в уже открытую страницу. */
  const values = (pg) => pg.evaluate(() => {
    const out = {};
    document.querySelectorAll('[data-calc-form] [name]').forEach((el) => {
      if (el.type === 'radio') { if (el.checked) out[el.name] = el.value; } else out[el.name] = el.value;
    });
    out.answer = document.querySelector('[data-calc-answer]').textContent.replace(/ /g, ' ');
    return out;
  });
  /* Своя вкладка в отдельном профиле: значения из ссылки запоминаются,
     и в общей памяти они подменили бы размеры для проверок ниже. */
  const lctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const linked = await lctx.newPage();
  linked.on('pageerror', (e) => errors.push(e.message));
  await linked.goto(pageUrl + '#armstrong?length=6&width=3&lamps=abc', { waitUntil: 'load' });
  await linked.waitForTimeout(300);
  let got = await values(linked);
  if (got.length !== '6' || got.width !== '3' || got.lamps !== '0' || got.answer !== '50 плит') fail(`калькулятор: ссылка с размерами — ${JSON.stringify(got)}`);
  await linked.fill('[data-calc-form] [name="length"]', '7');
  await linked.waitForTimeout(600);
  if (new URL(linked.url()).hash !== '#armstrong?length=7&width=3') fail(`калькулятор: адрес после ввода — ${new URL(linked.url()).hash}`);
  /* «Ссылка на расчёт» — со всеми видимыми полями. Буфер обмена подменяем:
     разрешения на чтение из него у страницы с file:// может не быть. */
  await linked.evaluate(() => {
    window.__copied = [];
    if (navigator.clipboard) navigator.clipboard.writeText = (t) => { window.__copied.push(t); return Promise.resolve(); };
    document.execCommand = () => { window.__copied.push(document.activeElement.value); return true; };
  });
  await linked.click('[data-calc-link]');
  await linked.waitForTimeout(200);
  const link = await linked.evaluate(() => window.__copied[0] || '');
  if (link !== pageUrl + '#armstrong?length=7&width=3&lamps=0&runner=3.6&angle=3&hang=1.2') fail(`калькулятор: «Ссылка на расчёт» скопировала «${link}»`);
  await linked.goto(pageUrl + '#peregorodka?sides=1&sheet=3&step=9', { waitUntil: 'load' });
  await linked.waitForTimeout(300);
  got = await values(linked);
  if (got.sides !== '1' || got.sheet !== '3' || got.step !== '0.6' || got.answer !== '4 листа') fail(`калькулятор: ссылка с вариантами — ${JSON.stringify(got)}`);
  /* Ссылку экранировали по дороге (письмо, мессенджер): «&amp;» вместо «&». */
  await linked.goto(pageUrl + '#armstrong?length=6&amp;width=3&amp;lamps=0', { waitUntil: 'load' });
  await linked.waitForTimeout(300);
  got = await values(linked);
  if (got.length !== '6' || got.width !== '3' || got.answer !== '50 плит') fail(`калькулятор: ссылка с «&amp;» — ${JSON.stringify(got)}`);
  await linked.evaluate(() => { location.hash = '#plitka?area=20'; });
  await linked.waitForTimeout(300);
  got = await values(linked);
  if (got.area !== '20' || got.answer !== '242 плитки') fail(`калькулятор: ссылка, вставленная в открытую страницу — ${JSON.stringify(got)}`);
  await linked.fill('[data-calc-form] [name="area"]', '');
  await linked.waitForTimeout(600);
  if (new URL(linked.url()).hash !== '#plitka?area=') fail(`калькулятор: стёртое поле должно попасть в адрес пустым — ${new URL(linked.url()).hash}`);
  await lctx.close();

  /* Площадь по размерам комнаты. Гипсокартон на стены 4 × 3 × 2,7, проёмы
     не вычитаем: 37,8 м² × 1,1 ÷ 3 = 13,9 → 14 листов; с окнами и дверями
     5 м² — 32,8 × 1,1 ÷ 3 = 12,03 → 13. Плитка на пол 4 × 3: 12 × 1,1
     ÷ 0,302² = 144,7 → 145; на стены 34,8 м² → 419,7 → 420. Стяжка на пол
     12 м² слоем 10 мм, расход 1,8, мешки по 25: 237,6 кг → 10. Панели
     на стены 34,8 × 1,1 ÷ 0,75 = 51,04 → 52. Перед каждой проверкой —
     «Сбросить»: выше в тех же калькуляторах вписаны свои числа. */
  await open('gkl');
  await page.click('[data-calc-reset]');
  await set({ surf: 'walls' });
  r = await read();
  expect('гипсокартон по комнате', r.answer, '14 листов');
  expect('гипсокартон по комнате, площадь', (r.rows.find((x) => x[0] === 'Площадь обшивки') || [])[1], '37,8 м²');
  await set({ openings: '5' });
  r = await read();
  expect('гипсокартон по комнате с проёмами', r.answer, '13 листов');
  expect('гипсокартон по комнате с проёмами, площадь', (r.rows.find((x) => x[0] === 'Площадь без окон и дверей') || [])[1], '32,8 м²');
  await set({ openings: '40' });
  expect('гипсокартон, проёмы больше стен', (await read()).note, 'Окна и двери получились больше стен — проверьте размеры.');
  await set({ openings: '0', height: '' });
  expect('гипсокартон без высоты', (await read()).note, 'Впишите высоту стен.');
  await page.click('[data-calc-reset]');
  await open('tile');
  await page.click('[data-calc-reset]');
  await set({ mode: 'room' });
  expect('плитка на пол по комнате', (await read()).answer, '145 плиток');
  await set({ surf: 'walls' });
  expect('плитка на стены по комнате', (await read()).answer, '420 плиток');
  await page.click('[data-calc-reset]');
  await open('mix');
  await page.click('[data-calc-reset]');
  await set({ kind: 'screed', mode: 'room', surf: 'floor', usage: '1,8', bag: '25' });
  expect('стяжка по комнате', (await read()).answer, '10 мешков');
  await page.click('[data-calc-reset]');
  await open('panels');
  await page.click('[data-calc-reset]');
  await set({ mode: 'room' });
  expect('панели по комнате', (await read()).answer, '52 панели');
  await page.click('[data-calc-reset]');

  /* Предупреждения о похожем на опечатку: видны под полем, связаны с ним
     для экранного диктора и пропадают, когда число исправили. */
  const warnOf = (name) => page.evaluate((n) => {
    const w = document.querySelector(`[data-warn-for="${n}"]`);
    const input = document.querySelector(`[data-calc-form] [name="${n}"]`);
    return { shown: !!w && !w.hidden, text: w ? w.textContent : '', linked: !!w && (input.getAttribute('aria-describedby') || '').split(' ').includes(w.id) };
  }, name);
  await open('tile');
  await set({ tileL: '30' });
  let warn = await warnOf('tileL');
  if (!warn.shown || !/миллиметрах/.test(warn.text) || !warn.linked) fail(`калькулятор: плитка 30 мм — нет предупреждения о миллиметрах — ${JSON.stringify(warn)}`);
  await set({ tileL: '300' });
  if ((await warnOf('tileL')).shown) fail('калькулятор: предупреждение не пропало после исправления');
  await page.click('[data-calc-reset]');
  await open('radiator');
  await set({ power: '1500' });
  warn = await warnOf('power');
  if (!warn.shown || !/одной секции/.test(warn.text)) fail(`калькулятор: мощность 1500 Вт на секцию — нет предупреждения — ${JSON.stringify(warn)}`);
  await page.click('[data-calc-reset]');
  await open('mix');
  await set({ usage: '9' });
  if (!(await warnOf('usage')).shown) fail('калькулятор: расход смеси 9 кг на 1 мм — нет предупреждения');
  await page.click('[data-calc-reset]');
  await open('paint');
  await set({ rate: '120' });
  if (!(await warnOf('rate')).shown) fail('калькулятор: 120 м² с литра — нет подсказки переключить единицы');
  await set({ rateUnit: 'mlm2' });
  if ((await warnOf('rate')).shown) fail('калькулятор: 120 мл на 1 м² — подсказки быть не должно');
  await page.click('[data-calc-reset]');

  /* Схемы рисуются по тем же числам, что в ответе. Потолок 5 × 4: три линии
     главного профиля, по 6 подвесов на линии — 18 точек, поперечных 1,2 —
     8 линий, 0,6 — 3, подрезка у двух стен. Перегородка: 8 стоек. Скат
     8 × 4 по листу 1,1 × 1,5: 7 стыков по ширине и 2 нахлёста. Обои:
     26 стыков полос, рулонов 9 — через один закрашены 4. */
  const scheme = () => page.evaluate(() => {
    const fig = document.querySelector('[data-calc-scheme]');
    const count = (cls, re) => {
      const el = fig.querySelector('.' + cls);
      return el ? (el.getAttribute('d').match(re) || []).length : 0;
    };
    return {
      shown: !!fig && !fig.hidden,
      main: count('scheme__main', /M/g), hang: count('scheme__hang', /a/g) / 2, t12: count('scheme__t12', /M/g), t06: count('scheme__t06', /M/g),
      studs: count('scheme__stud', /M/g), sheets: count('scheme__sheet', /M/g), seams: count('scheme__seam', /M/g),
      cut: fig.querySelectorAll('.scheme__cut').length, laps: fig.querySelectorAll('.scheme__lap').length, alt: fig.querySelectorAll('.scheme__alt').length,
      caption: fig.querySelector('[data-calc-scheme-cap]').textContent.replace(/ /g, ' '),
    };
  });
  await open('ceiling');
  await page.click('[data-calc-reset]');
  let sc = await scheme();
  if (!sc.shown || sc.main !== 3 || sc.hang !== 18 || sc.t12 !== 8 || sc.t06 !== 3 || sc.cut !== 2 || !/ячеек 9 × 7/.test(sc.caption)) fail(`калькулятор: схема потолка — ${JSON.stringify(sc)}`);
  await open('frame');
  await page.click('[data-calc-reset]');
  sc = await scheme();
  if (!sc.shown || sc.studs !== 8 || !/8 стоек/.test(sc.caption)) fail(`калькулятор: схема перегородки — ${JSON.stringify(sc)}`);
  /* Обшивка на подвесах: 8 профилей и 32 точки подвесов — столько же,
     сколько в ответе. Стены комнаты — развёрткой: четыре рамки, 28 стоек.
     У потолка каркас не считается — и схемы нет. */
  await open('gkl');
  await page.click('[data-calc-reset]');
  await set({ mount: 'pp' });
  sc = await scheme();
  if (!sc.shown || sc.studs !== 8 || sc.hang !== 32 || !/Схема обшивки 4 м × 2,7 м: 8 профилей ПП через 600 мм, на каждом 4 подвеса/.test(sc.caption)) {
    fail(`калькулятор: схема обшивки на подвесах — ${JSON.stringify(sc)}`);
  }
  await set({ surf: 'walls', mount: 'ps' });
  sc = await scheme();
  const frames = await page.evaluate(() => document.querySelectorAll('[data-calc-scheme] .scheme__edge').length);
  if (!sc.shown || sc.studs !== 28 || frames !== 4 || sc.hang || !/Развёртка стен 4 \+ 3 \+ 4 \+ 3 м, высота 2,7 м: 28 стоек/.test(sc.caption)) {
    fail(`калькулятор: развёртка стен комнаты — ${JSON.stringify(sc)}, рамок ${frames}`);
  }
  await set({ surf: 'ceiling' });
  if ((await scheme()).shown) fail('калькулятор: каркас потолка из гипсокартона не считается — схемы быть не должно');
  await page.click('[data-calc-reset]');
  await open('roof');
  await set({ useful: '1,1', sheetLen: '1,5' });
  sc = await scheme();
  if (!sc.shown || sc.sheets !== 9 || sc.laps !== 2 || sc.cut !== 1 || !/8 листов в ряд, 3 ряда/.test(sc.caption)) fail(`калькулятор: схема ската — ${JSON.stringify(sc)}`);
  await page.click('[data-calc-reset]');
  await open('wallpaper');
  await page.click('[data-calc-reset]');
  sc = await scheme();
  if (!sc.shown || sc.seams !== 26 || sc.alt !== 4 || !/27 полос по 0,53 м, из рулона — 3, рулонов 9/.test(sc.caption)) fail(`калькулятор: схема обоев — ${JSON.stringify(sc)}`);
  await open('radiator');
  if ((await scheme()).shown) fail('калькулятор: у радиаторов схемы нет — рамка должна прятаться');

  /* Поиск каждой позиции в каталоге: подпись — название товара, запрос —
     основа слова, чтобы стандартный поиск нашёл и «саморез», и «саморезы». */
  const chips = () => page.$$eval('[data-calc-find] .calc__chip', (a) => a.map((x) => [x.textContent.replace(/\u00a0/g, ' '), decodeURIComponent(x.getAttribute('href').split('search=')[1] || '')]));
  await open('frame');
  const frameChips = JSON.stringify(await chips());
  if (frameChips !== JSON.stringify([['Гипсокартон', 'гипсокартон'], ['Профиль', 'профиль'], ['Саморезы', 'саморез'], ['Дюбели', 'дюбел'], ['Уплотнительная лента', 'уплотнител'], ['Серпянка', 'серпянк'], ['Шпатлёвка', 'шпатлевк'], ['Грунтовка', 'грунт']])) {
    fail(`калькулятор: поиск позиций перегородки — ${frameChips}`);
  }
  /* У обшивки на подвесах — ещё и подвесы: запрос из двух основ находит
     «Подвес прямой» и не находит подвесы потолка «Армстронг». */
  await open('gkl');
  await set({ mount: 'pp', corners: '3' });
  const gklChips = JSON.stringify(await chips());
  if (gklChips !== JSON.stringify([['Гипсокартон', 'гипсокартон'], ['Профиль', 'профиль'], ['Подвесы прямые', 'подвес прям'], ['Саморезы', 'саморез'], ['Дюбели', 'дюбел'], ['Уплотнительная лента', 'уплотнител'], ['Серпянка', 'серпянк'], ['Шпатлёвка', 'шпатлевк'], ['Грунтовка', 'грунт'], ['Уголок перфорированный', 'уголок перфор']])) {
    fail(`калькулятор: поиск позиций обшивки — ${gklChips}`);
  }
  await set({ mount: 'glue' });
  if (!(await chips()).some((c) => c[1] === 'клей гипс') || (await chips()).some((c) => c[0] === 'Профиль')) fail(`калькулятор: поиск позиций обшивки на клей — ${JSON.stringify(await chips())}`);
  await page.click('[data-calc-reset]');
  await open('mix');
  await set({ kind: 'screed' });
  if (JSON.stringify(await chips()) !== JSON.stringify([['Смесь для стяжки', 'стяжк']])) fail(`калькулятор: поиск смеси для стяжки — ${JSON.stringify(await chips())}`);
  await page.click('[data-calc-reset]');
  await open('ceiling');
  await set({ lamps: '2' });
  if (!(await chips()).some((c) => c[0] === 'Светильники')) fail('калькулятор: при светильниках нет кнопки поиска светильников');
  await page.click('[data-calc-reset]');

  /* Всего по списку: одинаковые позиции разных расчётов сложены. Две
     перегородки, 4 и 3 м: гипсокартона 8 + 6 = 14 листов. Расчёт из
     списка открывается снова со своими размерами. */
  await open('frame');
  await page.click('[data-calc-add]');
  await set({ length: '3' });
  await page.click('[data-calc-add]');
  await page.waitForTimeout(200);
  const total = await page.evaluate(() => {
    const box = document.querySelector('[data-calc-list-total]');
    const rows = [...box.querySelectorAll('li')].map((li) => li.textContent.replace(/ /g, ' ').replace(/\s+/g, ' ').trim());
    return { shown: !box.hidden, rows };
  });
  if (!total.shown || !total.rows.includes('Гипсокартон 1200 × 2500 мм из 2 расчётов14 листов')) fail(`калькулятор: «Всего по списку» — ${JSON.stringify(total)}`);
  await page.evaluate(() => {
    window.__copied = [];
    if (navigator.clipboard) navigator.clipboard.writeText = (t) => { window.__copied.push(t); return Promise.resolve(); };
    document.execCommand = () => { window.__copied.push(document.activeElement.value); return true; };
  });
  await page.click('[data-calc-list-copy]');
  await page.waitForTimeout(200);
  const listCopy = await page.evaluate(() => (window.__copied[0] || '').replace(/\u00a0/g, ' '));
  if (!listCopy.includes('Всего по списку (одинаковые позиции сложены):\n— Гипсокартон 1200 × 2500 мм: 14 листов')) fail(`калькулятор: в тексте списка нет итога — «${listCopy.slice(0, 160)}»`);
  await set({ length: '9' });
  await page.click('[data-calc-list-open="0"]');
  await page.waitForTimeout(300);
  expect('перегородка, открытая из списка', await page.inputValue('[data-calc-form] input[name="length"]'), '4');
  await page.click('[data-calc-list-open="1"]');
  await page.waitForTimeout(300);
  expect('вторая перегородка, открытая из списка', await page.inputValue('[data-calc-form] input[name="length"]'), '3');
  await page.click('[data-calc-list-clear]');
  await page.click('[data-calc-list-clear]');

  /* Список, сохранённый до правки 32 (позиции без чисел), показывается как
     был: без «Всего по списку» и без «Открыть в калькуляторе». */
  await page.evaluate(() => localStorage.setItem('sg-calc-list', JSON.stringify([
    { title: 'Обои', summary: 'комната 4 × 3', items: [['Обои 0,53 × 10,05 м', '9 рулонов']] },
    { title: 'Обои', summary: 'комната 5 × 3', items: [['Обои 0,53 × 10,05 м', '10 рулонов']] },
  ])));
  await page.goto(pageUrl, { waitUntil: 'load' });
  await page.waitForTimeout(300);
  const old = await page.evaluate(() => ({
    entries: document.querySelectorAll('.calc-list__entry').length,
    total: !document.querySelector('[data-calc-list-total]').hidden,
    open: document.querySelectorAll('[data-calc-list-open]').length,
  }));
  if (old.entries !== 2 || old.total || old.open) fail(`калькулятор: старый список — ${JSON.stringify(old)}`);
  await page.click('[data-calc-list-clear]');
  await page.click('[data-calc-list-clear]');

  /* Enter — к следующему полю, как по бланку. */
  await open('ceiling');
  await page.focus('[data-calc-form] input[name="length"]');
  await page.keyboard.press('Enter');
  const next = await page.evaluate(() => document.activeElement && document.activeElement.name);
  if (next !== 'width') fail(`калькулятор: Enter из «Длины» должен вести в «Ширину», а привёл в «${next}»`);

  /* Находки вычитки кода (правка 33) — каждая закреплена проверкой. */
  {
    const rctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const rp = await rctx.newPage();
    rp.on('pageerror', (e) => errors.push(e.message));
    const url = pageUrl;
    const val = (name) => rp.inputValue(`[data-calc-form] input[name="${name}"]`);
    await rp.goto(url + '#gipsokarton', { waitUntil: 'load' });
    await rp.waitForTimeout(300);

    /* Число и единица — через неразрывный пробел: при правке 32 он
       превратился в обычный, и «4» могла уехать от «листа» на другую
       строку. Проверки выше заменяют его пробелом — здесь смотрим сам знак. */
    const nb = await rp.evaluate(() => document.querySelector('[data-calc-answer]').textContent);
    if (nb !== '4 листа') fail(`калькулятор: между числом и единицей не неразрывный пробел — ${JSON.stringify(nb)}`);

    /* Щелчок по уже открытой карточке не теряет только что введённое. */
    await rp.fill('[data-calc-form] input[name="wallLen"]', '6');
    await rp.click('[data-calc-pick="gkl"]');
    await rp.waitForTimeout(150);
    if ((await val('wallLen')) !== '6') fail(`калькулятор: после щелчка по открытой карточке длина стены ${await val('wallLen')}, а вписали 6`);

    /* «10%» — это 10; число, которое не разобрать, уходит в ссылку пустым,
       как и считается, а не подменяется значением по умолчанию. */
    await rp.evaluate(() => { document.querySelector('.calc__more').open = true; });
    await rp.fill('[data-calc-form] input[name="reserve"]', '10%');
    await rp.waitForTimeout(150);
    const pct = await rp.evaluate(() => [...document.querySelectorAll('[data-calc-rows] li')].map((li) => li.textContent.replace(/ /g, ' ')));
    if (!pct.includes('Запас на листы10 %')) fail(`калькулятор: «10%» не понят как 10 — ${JSON.stringify(pct)}`);
    await rp.fill('[data-calc-form] input[name="reserve"]', 'abc');
    await rp.waitForTimeout(600);
    if (!/[?&]reserve=(&|$)/.test(new URL(rp.url()).hash)) fail(`калькулятор: непонятный запас должен уйти в ссылку пустым — ${new URL(rp.url()).hash}`);
    await rp.click('[data-calc-reset]');

    /* Перезагрузка сразу после ввода: адрес ещё старый, память новее.
       Ссылка — в старом виде, до правки 34: площадь без surf=area. */
    const rp2 = await rctx.newPage();
    await rp2.goto(url + '#gipsokarton?area=30', { waitUntil: 'load' });
    await rp2.waitForTimeout(300);
    await rp2.fill('[data-calc-form] input[name="area"]', '42');
    await rp2.reload({ waitUntil: 'load' });
    await rp2.waitForTimeout(300);
    const afterReload = await rp2.inputValue('[data-calc-form] input[name="area"]');
    if (afterReload !== '42') fail(`калькулятор: перезагрузка сразу после ввода вернула площадь ${afterReload} вместо 42`);
    await rp2.close();

    /* Крошечный шаг подвесов: подсказка, а схема не рисуется — сотни тысяч
       точек подвесили бы страницу. */
    await rp.click('[data-calc-pick="ceiling"]');
    await rp.waitForTimeout(150);
    await rp.evaluate(() => { document.querySelector('.calc__more').open = true; });
    const t0 = Date.now();
    await rp.fill('[data-calc-form] input[name="hang"]', '0,00001');
    await rp.waitForTimeout(150);
    const tiny = await rp.evaluate(() => ({
      scheme: !document.querySelector('[data-calc-scheme]').hidden,
      warn: !document.querySelector('[data-warn-for="hang"]').hidden,
    }));
    if (tiny.scheme || !tiny.warn || Date.now() - t0 > 3000) fail(`калькулятор: шаг подвесов 0,00001 м — ${JSON.stringify(tiny)}, ${Date.now() - t0} мс`);
    await rp.click('[data-calc-reset]');

    /* Дверей больше, чем стен: плинтуса нет, а не «−0 шт.». */
    await rp.click('[data-calc-pick="floor"]');
    await rp.waitForTimeout(150);
    await rp.evaluate(() => { document.querySelector('.calc__more').open = true; });
    await rp.fill('[data-calc-form] input[name="doors"]', '30');
    await rp.waitForTimeout(150);
    /* Смотрим сам ответ и список покупок: кнопка поиска «Плинтус» ниже
       остаётся — искать плинтус в каталоге можно и так. */
    const floorText = await rp.evaluate(() => document.querySelector('[data-calc-answer]').textContent + ' ' + document.querySelector('[data-calc-buy]').textContent);
    if (/-0|−0|Плинтус/.test(floorText)) fail(`калькулятор: при дверях шире стен в ответе остался плинтус или «−0» — ${floorText}`);
    await rp.click('[data-calc-reset]');

    /* «Это плиток», «Это упаковок…» — пояснения к позиции, а не товар:
       две разные плитки не складываются в «Всего по списку». */
    await rp.click('[data-calc-pick="tile"]');
    await rp.waitForTimeout(150);
    await rp.fill('[data-calc-form] input[name="perPack"]', '11');
    await rp.waitForTimeout(150);
    await rp.click('[data-calc-add]');
    await rp.fill('[data-calc-form] input[name="tileL"]', '600');
    await rp.fill('[data-calc-form] input[name="tileW"]', '600');
    await rp.fill('[data-calc-form] input[name="perPack"]', '4');
    await rp.waitForTimeout(150);
    await rp.click('[data-calc-add]');
    await rp.waitForTimeout(150);
    if (!(await rp.evaluate(() => document.querySelector('[data-calc-list-total]').hidden))) fail('калькулятор: две разные плитки сложились во «Всего по списку»');

    /* Две вкладки: список дополняется, а не затирается чужой копией. */
    const tabB = await rctx.newPage();
    await tabB.goto(url + '#oboi', { waitUntil: 'load' });
    await tabB.waitForTimeout(300);
    await tabB.click('[data-calc-add]');
    await tabB.waitForTimeout(200);
    /* Первая вкладка узнаёт о расчёте из второй сама, без перезагрузки. */
    const seen = await rp.$$eval('.calc-list__name', (n) => n.map((x) => x.textContent));
    if (!seen.includes('Обои')) fail(`калькулятор: первая вкладка не увидела расчёт из второй — ${JSON.stringify(seen)}`);
    /* И перед добавлением список перечитывается: запись, о которой вкладка
       не узнала (событие не пришло), не затирается. */
    await rp.evaluate(() => {
      const l = JSON.parse(localStorage.getItem('sg-calc-list'));
      l.push({ key: 'silent', id: 'wallpaper', title: 'Тихая запись', summary: '', raw: {}, items: [['Обои', '1 рулон', 1, 'рулон']] });
      localStorage.setItem('sg-calc-list', JSON.stringify(l));
    });
    await rp.click('[data-calc-pick="gkl"]');
    await rp.waitForTimeout(150);
    await rp.click('[data-calc-add]');
    await rp.waitForTimeout(200);
    const tabs = await rp.evaluate(() => ({
      stored: JSON.parse(localStorage.getItem('sg-calc-list')).map((e) => e.title),
      shown: [...document.querySelectorAll('.calc-list__name')].map((n) => n.textContent),
    }));
    if (tabs.stored.length !== 5 || tabs.shown.length !== 5 || !tabs.stored.includes('Обои') || !tabs.stored.includes('Тихая запись')) fail(`калькулятор: две вкладки — ${JSON.stringify(tabs)}`);
    await tabB.close();
    await rp.click('[data-calc-list-clear]');
    await rp.click('[data-calc-list-clear]');

    /* Длинный список с итогом: итог — целиком, подробности — сколько
       влезет, строка о невошедших — всегда, и окно говорит то, что ушло. */
    await rp.click('[data-calc-pick="frame"]');
    await rp.waitForTimeout(150);
    await rp.click('[data-calc-add]');
    await rp.waitForTimeout(150);
    await rp.evaluate(() => {
      const one = JSON.parse(localStorage.getItem('sg-calc-list'))[0];
      localStorage.setItem('sg-calc-list', JSON.stringify(Array.from({ length: 15 }, (_, i) => ({ ...one, key: 'k' + i }))));
    });
    await rp.goto(url, { waitUntil: 'load' });
    await rp.waitForTimeout(300);
    const measure = async () => {
      await rp.click('[data-calc-list-send]');
      await rp.waitForTimeout(200);
      const out = await rp.evaluate(async () => {
        const body = await new Response(new FormData(document.querySelector('#modal-callback form'))).text();
        const value = (body.match(/name="message"\r\n\r\n([\s\S]*?)\r\n--/) || [])[1] || '';
        const server = value.trim().replace(/[&"<>]/g, (ch) => ({ '&': '&amp;', '"': '&quot;', '<': '&lt;', '>': '&gt;' })[ch]);
        return { length: [...server].length, value, note: document.querySelector('[data-calc-attached]').textContent.replace(/ /g, ' ') };
      });
      await rp.keyboard.press('Escape');
      await rp.waitForTimeout(150);
      return out;
    };
    let sent = await measure();
    if (sent.length > 2000 || !/Всего по списку/.test(sent.value) || !/И ещё \d+ расчёт/.test(sent.value.split('\n').pop()) ||
        !/из 15 .*«Всего по списку» приложен целиком/.test(sent.note)) {
      fail(`калькулятор: 15 перегородок в заявке — ${sent.length} знаков, конец «${sent.value.split('\n').pop()}», окно «${sent.note}»`);
    }
    /* Итог не влезает сам: шестьдесят разных расчётов и одна общая позиция. */
    await rp.evaluate(() => {
      const entries = Array.from({ length: 60 }, (_, i) => ({
        key: 'u' + i, id: 'gkl', title: 'Расчёт ' + i, summary: '', raw: {},
        items: [['Уникальная позиция номер ' + i + ' с длинным названием', '1 шт.', 1, 'шт.'], ['Общая позиция', '1 шт.', 1, 'шт.']],
      }));
      localStorage.setItem('sg-calc-list', JSON.stringify(entries));
    });
    await rp.goto(url, { waitUntil: 'load' });
    await rp.waitForTimeout(300);
    sent = await measure();
    if (sent.length > 2000 || !/И ещё 60 расчётов/.test(sent.value) || !/вошло только начало итога/.test(sent.note)) {
      fail(`калькулятор: итог длиннее заявки — ${sent.length} знаков, конец «${sent.value.split('\n').pop()}», окно «${sent.note}»`);
    }
    await rctx.close();
  }

  if (errors.length) fail(`калькулятор: ошибки скрипта — ${errors.join('; ')}`);
  await ctx.close();
}

/* Телефон: итог под длинной формой, поэтому пока форма на экране, внизу
   висит плашка с ответом; когда доскроллили до итога — прячется. */
{
  const ctx = await browser.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(DIR, 'calculator.html') + '#peregorodka', { waitUntil: 'load' });
  await page.waitForTimeout(400);
  await page.evaluate(() => window.scrollTo(0, 300));
  await page.waitForTimeout(400);
  const peek = await page.evaluate(() => {
    const p = document.querySelector('[data-calc-peek]');
    return { hidden: p.hidden, text: p.textContent.replace(/ /g, ' ').trim() };
  });
  if (peek.hidden || peek.text !== 'Итог: 8 листов') fail(`калькулятор на телефоне: плашка итога — ${JSON.stringify(peek)}`);
  /* Сообщение внизу экрана встаёт на место плашки — плашка ему уступает. */
  await page.evaluate(() => document.querySelector('[data-calc-reset]').click());
  await page.waitForTimeout(100);
  const under = await page.evaluate(() => ({
    note: !document.querySelector('[data-demo-note]').hidden,
    peek: getComputedStyle(document.querySelector('[data-calc-peek]')).visibility,
  }));
  if (!under.note || under.peek !== 'hidden') fail(`калькулятор на телефоне: плашка итога поверх сообщения внизу экрана — ${JSON.stringify(under)}`);
  await page.evaluate(() => { document.querySelector('[data-demo-note]').hidden = true; });
  if ((await page.evaluate(() => getComputedStyle(document.querySelector('[data-calc-peek]')).visibility)) !== 'visible') fail('калькулятор на телефоне: плашка итога не вернулась после сообщения');
  /* Прокрутка — мгновенная: плавная у длинной формы не успевает доехать
     за время проверки, а проверяем мы плашку, а не анимацию. */
  await page.evaluate(() => document.querySelector('[data-calc-result]').scrollIntoView({ behavior: 'instant' }));
  await page.waitForTimeout(400);
  if (!(await page.evaluate(() => document.querySelector('[data-calc-peek]').hidden))) fail('калькулятор на телефоне: плашка итога должна прятаться, когда итог на экране');
  await ctx.close();
}

/* Телефон: «Поделиться» открывает меню самого телефона — в сообщении
   позиции расчёта и ссылка со всеми размерами; у списка своя кнопка
   «Поделиться». Меню подменяем: в браузере для проверок его нет. */
{
  const ctx = await browser.newContext({ viewport: { width: 390, height: 780 }, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  await page.addInitScript(() => { navigator.share = (d) => { window.__shared = d; return Promise.resolve(); }; });
  await page.goto('file://' + path.join(DIR, 'calculator.html') + '#armstrong?length=6&width=3', { waitUntil: 'load' });
  await page.waitForTimeout(400);
  const label = (await page.textContent('[data-calc-link]')).trim();
  if (label !== 'Поделиться расчётом') fail(`калькулятор на телефоне: кнопка ссылки называется «${label}»`);
  await page.click('[data-calc-link]');
  await page.waitForTimeout(200);
  const shared = await page.evaluate(() => window.__shared || null);
  if (!shared || !/— Плиты 600 × 600 мм: 50\sплит/.test(shared.text) || !shared.url.endsWith('#armstrong?length=6&width=3&lamps=0&runner=3.6&angle=3&hang=1.2')) {
    fail(`калькулятор на телефоне: «Поделиться» отправило ${JSON.stringify(shared)}`);
  }
  await page.click('[data-calc-add]');
  await page.waitForTimeout(200);
  if (await page.evaluate(() => document.querySelector('[data-calc-list-share]').hidden)) fail('калькулятор на телефоне: у списка нет кнопки «Поделиться»');
  await page.click('[data-calc-list-share]');
  await page.waitForTimeout(200);
  const list = await page.evaluate(() => window.__shared || {});
  if (!/Список покупок/.test(list.title || '') || !/Потолок «Армстронг»/.test(list.text || '')) fail(`калькулятор на телефоне: список ушёл в «Поделиться» как ${JSON.stringify(list).slice(0, 120)}`);
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
    if (!got.text.replace(/\u00a0/g, ' ').includes(expect)) {
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
    const parts = ['.site-header', '.header-main', '.header-main__inner', '.header-nav',
      '.header-nav__inner', '.site-logo > img', '.header-catalog'];
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

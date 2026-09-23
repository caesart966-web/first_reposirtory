/*
  Постраничная навигация — в той разметке, в какой её отдаёт ЖИВОЙ сайт.

  На stroigeroi.ru навигацию рисует не OpenCart, а доставшийся от прежней
  темы stroyhero вариант system/library/pagination.php: <div>, а не <ul>,
  стрелка — <svg> без размеров со ссылкой на спрайт старой темы, текущая
  страница — <div class="pagination__item active">. Наши стили ждали
  разметку движка, и на сайте вышла стрелка на полстраницы: браузер рисует
  svg без размеров в 300 на 150.

  Разметка ниже снята с сайта 23.09.2026 (Chrome, «Просмотреть код»).
  Варианты, которых на снимке не было — первая страница, середина,
  неизвестная стрелка, текущая без span и обычная разметка движка, —
  проверяются тоже: заранее не угадать, какую из них отдаст движок завтра.

  Название у стрелок проверяется по дереву доступности самого Chrome,
  а не по Playwright: Playwright считает названия своим кодом, а экранный
  диктор читает дерево браузера. На этом уже ошиблись один раз — запись
  content: "" / "подпись" Playwright принимал, а Chrome отдавал пустое имя.

  Запуск: node tools/test-pagination.mjs
*/
import { chromium } from 'playwright';
import { writeFileSync, mkdtempSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const ROOT = resolve(import.meta.dirname, '..');
const CSS = [
  join(ROOT, 'assets/style.css'),
  join(ROOT, 'opencart-theme/catalog/view/theme/stroigeroi2026/stylesheet/opencart.css'),
];

const SVG = '<svg class="svg"><use xlink:href="catalog/view/theme/stroyhero/img/icons/icons.svg#arrow"></use></svg>';
const U = 'https://stroigeroi.ru/index.php?route=product/category&amp;path=92';
const arrow = m => `<a href="${U}" class="pagination__arrow pagination__arrow_${m}">${SVG}</a>`;
const item = n => `<a href="${U}&amp;page=${n}" class="pagination__item">${n}</a>`;
const cur = n => `<div class="pagination__item active"><span>${n}</span></div>`;

const CASES = {
  'как на сайте, 2 из 2': arrow('first') + item(1) + cur(2),
  'первая из трёх': cur(1) + item(2) + item(3) + arrow('last'),
  'середина, 3 из 5': arrow('first') + arrow('prev') + item(2) + cur(3) + item(4) + arrow('next') + arrow('last'),
  'неизвестная стрелка': arrow('weird') + item(1) + cur(2),
  'текущая без span': arrow('first') + item(1) + '<div class="pagination__item active">2</div>',
};
const VANILLA = '<ul class="pagination"><li><a href="#">|&lt;</a></li><li><a href="#">&lt;</a></li>'
              + '<li><a href="#">1</a></li><li class="active"><span>2</span></li></ul>';

const names = Object.keys(CASES);
const body = names.map((t, i) => `<div class="pagination" data-case="${i}">${CASES[t]}</div>`).join('\n')
           + `\n<div data-case="v">${VANILLA}</div>`;
const dir = mkdtempSync(join(tmpdir(), 'pg-'));
const page = join(dir, 'index.html');
writeFileSync(page, `<!DOCTYPE html><html lang="ru" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
${CSS.map(c => `<link rel="stylesheet" href="file://${c}">`).join('\n')}
</head><body><main><div class="container">${body}</div></main></body></html>`);

const ARROWS = {
  first: 'Первая страница', prev: 'Предыдущая страница',
  next: 'Следующая страница', last: 'Последняя страница',
};

// Браузер выбирается так же, как в test.mjs: CHROMIUM_PATH, затем браузер
// из образа, иначе тот, что playwright поставил себе сам (так на GitHub Actions).
const exe = [process.env.CHROMIUM_PATH, '/opt/pw-browsers/chromium'].find(c => c && existsSync(c));
const browser = await chromium.launch(exe ? { executablePath: exe } : {});
let bad = 0;
const fail = m => { console.log('  ' + m); bad++; };
const label = c => c === 'v' ? 'разметка OpenCart' : names[+c];

for (const theme of ['light', 'dark']) {
  for (const width of [390, 1280]) {
    const p = await browser.newPage({ viewport: { width, height: 900 } });
    await p.goto('file://' + page);
    await p.evaluate(t => { document.documentElement.dataset.theme = t; }, theme);
    const at = `${theme === 'light' ? 'светлая' : 'тёмная'}, ${width}px`;

    // 1. Ни одна кнопка не больше обычной — стрелка не раздувается
    const boxes = await p.$$eval('.pagination > *, .pagination li > *', els => els.map(e => {
      const r = e.getBoundingClientRect();
      return { c: e.closest('[data-case]').dataset.case, cls: String(e.className || e.tagName), w: r.width, h: r.height };
    }));
    for (const b of boxes)
      if (b.w > 64 || b.h > 48)
        fail(`${at}, «${label(b.c)}»: ${b.cls} размером ${Math.round(b.w)}×${Math.round(b.h)}`);

    // 2. Видимый svg в навигации — не больше стрелки
    const svgs = await p.$$eval('.pagination svg', els => els
      .filter(e => getComputedStyle(e).display !== 'none')
      .map(e => { const r = e.getBoundingClientRect(); return [r.width, r.height]; }));
    for (const [w, h] of svgs)
      if (w > 18 || h > 18) fail(`${at}: svg ${Math.round(w)}×${Math.round(h)}`);

    // 3. Текущая страница выделена фоном — в каждом варианте разметки
    for (const c of [...names.keys(), 'v']) {
      const lit = await p.$$eval(`[data-case="${c}"] .active > span, [data-case="${c}"] div.active`,
        els => els.some(e => getComputedStyle(e).backgroundColor !== 'rgba(0, 0, 0, 0)'));
      if (!lit) fail(`${at}, «${label(c)}»: текущая страница не выделена`);
    }

    // 4. Стрелки смотрят куда надо и видны: у псевдоэлемента есть маска
    for (const mod of Object.keys(ARROWS)) {
      const mask = await p.$eval(`[data-case="2"] .pagination__arrow_${mod}`,
        e => getComputedStyle(e, '::before').maskImage || getComputedStyle(e, '::before').webkitMaskImage);
      if (!mask || mask === 'none') fail(`${at}: у стрелки _${mod} нет рисунка`);
    }

    // 5. Названия — по дереву доступности Chrome
    const cdp = await p.context().newCDPSession(p);
    await cdp.send('Accessibility.enable');
    const { root } = await cdp.send('DOM.getDocument', { depth: -1 });
    for (const [mod, want] of Object.entries(ARROWS)) {
      const { nodeId } = await cdp.send('DOM.querySelector',
        { nodeId: root.nodeId, selector: `[data-case="2"] .pagination__arrow_${mod}` });
      const ax = await cdp.send('Accessibility.getPartialAXTree', { nodeId, fetchRelatives: false });
      const got = ax.nodes[0]?.name?.value;
      if (got !== want) fail(`${at}: у стрелки _${mod} имя ${JSON.stringify(got)}, ждали «${want}»`);
    }

    // 6. Скрытая подпись не даёт горизонтальной прокрутки
    const over = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    if (over > 0) fail(`${at}: горизонтальная прокрутка ${over}px`);
    await p.close();
  }
}
await browser.close();
console.log(bad ? `Навигация по страницам: ошибок ${bad}` : 'Навигация по страницам: 6 вариантов разметки, 2 темы, 2 ширины — чисто');
process.exit(bad ? 1 : 0);

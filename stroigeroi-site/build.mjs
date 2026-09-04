/**
 * Сборщик макета «Строй-Герой».
 *
 * Делает три вещи, которые руками делать нельзя — забудешь и получишь
 * рассыпавшуюся страницу у заказчика:
 *
 * 1. Проставляет к style.css и app.js отпечаток содержимого (?v=…). Без него
 *    браузер берёт свежий HTML со старым CSS из кэша.
 * 2. Собирает stroigeroi-preview.html — все страницы, стили, скрипт и картинки
 *    одним файлом. Его пересылают заказчику вложением, рядом с ним ничего
 *    не нужно.
 * 3. Проверяет результат: битые внутренние ссылки, пропавшие файлы, картинки
 *    без alt, дубли id.
 *
 * Запуск:
 *   node build.mjs           пересобрать
 *   node build.mjs --check   только проверить, ничего не писать (для CI)
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.dirname(fileURLToPath(import.meta.url));
const CHECK_ONLY = process.argv.includes('--check');

/* Порядок здесь же задаёт порядок вкладок в превью. */
const PAGES = [
  ['index', 'Главная'],
  ['catalog', 'Каталог'],
  ['product', 'Карточка товара'],
  ['cart', 'Корзина'],
  ['calculator', 'Калькулятор'],
  ['delivery', 'Доставка'],
  ['contacts', 'Контакты'],
  ['404', '404'],
];

const read = (f) => readFileSync(path.join(DIR, f), 'utf8');
const readBin = (f) => readFileSync(path.join(DIR, f));
const md5 = (buf) => createHash('md5').update(buf).digest('hex').slice(0, 8);

const problems = [];
const changed = [];

function write(file, next) {
  const full = path.join(DIR, file);
  const prev = readFileSync(full, 'utf8');
  if (prev === next) return;
  changed.push(file);
  if (!CHECK_ONLY) writeFileSync(full, next);
}

/* ==========================================================================
   1. Отпечатки содержимого
   ========================================================================== */

const cssFingerprint = md5(readBin('assets/style.css'));
const jsFingerprint = md5(readBin('assets/app.js'));

for (const [name] of PAGES) {
  const file = `${name}.html`;
  const next = read(file)
    .replace(/assets\/style\.css(\?v=[a-f0-9]+)?/g, `assets/style.css?v=${cssFingerprint}`)
    .replace(/assets\/app\.js(\?v=[a-f0-9]+)?/g, `assets/app.js?v=${jsFingerprint}`);
  write(file, next);
}

/* ==========================================================================
   2. Превью одним файлом
   ========================================================================== */

/* Ссылки между страницами внутри одного файла ведут на секцию, а не на файл.
   Якорь при этом теряется: разделов в превью нет, есть только страницы.
   Раньше эту замену делали без учёта якоря, и ссылки вида delivery.html#payment
   оставались в файле битыми. */
const pageNames = PAGES.map(([name]) => name);
function relink(html) {
  return html.replace(
    new RegExp(`(href|action)="(${pageNames.join('|')})\\.html(#[\\w-]+)?"`, 'g'),
    (_, attr, name) => `${attr}="#p-${name}"`,
  );
}

/* Картинки уезжают в сам файл: превью открывают из письма, папки assets
   рядом с ним не будет. WebP — он вдвое легче, а Safari его понимает
   с 2020 года, отдельный JPEG для одного файла-просмотра не нужен. */
const bannerData = `data:image/webp;base64,${readBin('assets/banner.webp').toString('base64')}`;
const logoData = `data:image/png;base64,${readBin('assets/logo.png').toString('base64')}`;

function inlineImages(html) {
  return (
    html
      /* <picture> с набором размеров разворачивается в одну картинку:
         адаптивные srcset внутри data: не имеют смысла и раздули бы файл. */
      .replace(
        /<picture>.*?<img class="hero__banner"([^>]*?)>.*?<\/picture>/gs,
        (_, attrs) =>
          `<img class="hero__banner"${attrs
            .replace(/\s(?:src|srcset|sizes)="[^"]*"/g, '')
            .trimEnd()} src="${bannerData}">`,
      )
      .replace(/src="assets\/logo\.png"/g, `src="${logoData}"`)
  );
}

const indexHtml = read('index.html');

function section(html, tag) {
  const m = html.match(new RegExp(`<${tag}[^>]*>[\\s\\S]*<\\/${tag}>`));
  if (!m) throw new Error(`в index.html не найден <${tag}>`);
  return m[0];
}

/* Шапка, подвал и модалки одинаковы на всех страницах — в превью они
   существуют в одном экземпляре, вокруг переключаемых секций. */
const header = section(indexHtml, 'header');
const tail = indexHtml.slice(indexHtml.indexOf('</main>') + '</main>'.length)
  .replace(/\s*<script src="assets\/app\.js[^"]*"><\/script>\s*<\/body>\s*<\/html>\s*$/, '');

const previewCss = `
/* Панель переключения страниц — только для этого файла-просмотра */
.preview-bar{position:sticky;top:0;z-index:60;display:flex;flex-wrap:wrap;align-items:center;
  gap:8px;padding:10px 16px;background:var(--sg-ink);color:#fff;font-size:14px}
.preview-bar__label{font-weight:700;margin-right:8px}
.preview-tab{display:inline-block;padding:8px 14px;border-radius:6px;background:rgba(255,255,255,.12);
  color:#fff;font-weight:600;text-decoration:none}
.preview-tab:hover{background:rgba(255,255,255,.22);text-decoration:none}
.preview-tab[aria-current="true"]{background:var(--sg-red)}
.preview-hint{margin-left:auto;color:#c9c9d4;font-size:13px}
.preview-page{display:none}
.preview-page.is-active{display:block}
@media (max-width:640px){.preview-hint{display:none}}
`;

const previewNavScript = `
// Переключение страниц внутри одного файла
(function(){
  var pages = document.querySelectorAll('[data-page]');
  var links = document.querySelectorAll('[data-tab-link]');
  function show(id){
    var found = false;
    pages.forEach(function(p){
      var on = p.id === id;
      p.classList.toggle('is-active', on);
      if (on) found = true;
    });
    if (!found && pages.length) pages[0].classList.add('is-active');
    links.forEach(function(l){
      l.setAttribute('aria-current', l.getAttribute('data-tab-link') === id ? 'true' : 'false');
    });
    window.scrollTo(0, 0);
  }
  function current(){ return (location.hash || '#p-index').replace('#',''); }
  window.addEventListener('hashchange', function(){ show(current()); });
  document.addEventListener('click', function(e){
    var a = e.target.closest ? e.target.closest('a[href^="#p-"]') : null;
    if (a) setTimeout(function(){ show(current()); }, 0);
  });
  show(current());
})();
`;

const tabs = PAGES.map(
  ([name, label]) => `<a class="preview-tab" href="#p-${name}" data-tab-link="p-${name}">${label}</a>`,
).join('');

const sections = PAGES.map(([name]) => {
  const html = read(`${name}.html`);
  const start = html.indexOf('<main id="main">') + '<main id="main">'.length;
  const body = html.slice(start, html.indexOf('</main>'));
  return `<section class="preview-page" id="p-${name}" data-page>${body}</section>`;
}).join('');

const preview = inlineImages(
  relink(`<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Строй-Герой — макет сайта (просмотр)</title>
<meta name="theme-color" content="#ffffff">
<meta name="robots" content="noindex, nofollow">
<script>(function(){try{var t=JSON.parse(localStorage.getItem('sg-theme'));if(t){document.documentElement.setAttribute('data-theme',t);}}catch(e){}})();</script>
<style>
${read('assets/style.css').trim()}
${previewCss.trim()}
</style>
</head>
<body>
<a class="skip-link" href="#main">Перейти к содержимому</a>

<div class="preview-bar">
  <span class="preview-bar__label">Макет сайта:</span>
  ${tabs}
  <span class="preview-hint">Один файл — папка assets не нужна</span>
</div>

${header}

<main id="main">
${sections}
</main>
${tail}
<script>
${read('assets/app.js').trim()}

${previewNavScript.trim()}
</script>
</body>
</html>
`),
);

write('stroigeroi-preview.html', preview);

/* ==========================================================================
   3. Проверки
   ========================================================================== */

const assetsUsed = new Set();

for (const [name] of PAGES) {
  const file = `${name}.html`;
  const html = read(file);

  /* Ссылки на соседние страницы */
  for (const m of html.matchAll(/href="([\w-]+)\.html(#[\w-]+)?"/g)) {
    if (!pageNames.includes(m[1])) problems.push(`${file}: ссылка на несуществующую страницу ${m[1]}.html`);
  }

  /* Файлы в assets. srcset — это список «путь ширина», его надо разобрать
     по запятым, иначе в проверку уедет вся строка целиком. */
  for (const m of html.matchAll(/(?:src|href)="(assets\/[^"?]+)/g)) assetsUsed.add(m[1]);
  for (const m of html.matchAll(/srcset="([^"]+)"/g)) {
    for (const part of m[1].split(',')) {
      const url = part.trim().split(/\s+/)[0];
      if (url.startsWith('assets/')) assetsUsed.add(url.split('?')[0]);
    }
  }

  /* Картинка без alt — читалка экрана прочитает вслух имя файла */
  for (const m of html.matchAll(/<img (?![^>]*\balt=)[^>]*>/g)) {
    problems.push(`${file}: <img> без alt — ${m[0].slice(0, 70)}…`);
  }

  /* Дубли id ломают и якоря, и aria-controls */
  const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
  const dup = ids.filter((id, i) => ids.indexOf(id) !== i);
  if (dup.length) problems.push(`${file}: повторяющиеся id — ${[...new Set(dup)].join(', ')}`);

  /* Внутренние якоря должны существовать на той же странице */
  for (const m of html.matchAll(/href="#([\w-]+)"/g)) {
    if (!ids.includes(m[1])) problems.push(`${file}: якорь #${m[1]} никуда не ведёт`);
  }
}

for (const asset of assetsUsed) {
  try {
    readBin(asset);
  } catch {
    problems.push(`нет файла ${asset}, а на него ссылаются`);
  }
}

if (/href="[\w-]+\.html/.test(preview)) {
  problems.push('в превью остались ссылки на отдельные файлы — рядом с ним их не будет');
}
if (/(?:src|href)="assets\//.test(preview)) {
  problems.push('в превью осталась ссылка на папку assets — он должен быть самодостаточным');
}

/* ==========================================================================
   Итог
   ========================================================================== */

console.log(`Отпечатки: style.css ?v=${cssFingerprint}, app.js ?v=${jsFingerprint}`);
console.log(`Превью: ${(Buffer.byteLength(preview) / 1024 / 1024).toFixed(2)} МБ, ${PAGES.length} страниц`);

if (changed.length) {
  console.log(`${CHECK_ONLY ? 'Устарели' : 'Обновлено'}: ${changed.join(', ')}`);
} else {
  console.log('Всё уже собрано, менять нечего');
}

if (problems.length) {
  console.error(`\nПроблемы (${problems.length}):`);
  for (const p of problems) console.error('  • ' + p);
  process.exit(1);
}

if (CHECK_ONLY && changed.length) {
  console.error('\nСборка устарела: запустите node build.mjs и закоммитьте результат');
  process.exit(1);
}

console.log('Проверки пройдены');

/**
 * Сборщик макета «Строй-Герой».
 *
 * Делает три вещи, которые руками делать нельзя — забудешь и получишь
 * рассыпавшуюся страницу у заказчика:
 *
 * 1. Проставляет к style.css, app.js и calc.js отпечаток содержимого (?v=…).
 *    Без него браузер берёт свежий HTML со старым CSS из кэша.
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

import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
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
  ['checkout', 'Оформление'],
  ['order-done', 'Заказ принят'],
  ['favourites', 'Избранное'],
  ['compare', 'Сравнение'],
  ['login', 'Вход'],
  ['policy', 'Политика'],
  ['terms', 'Соглашение'],
  ['404', '404'],
];

const read = (f) => readFileSync(path.join(DIR, f), 'utf8');
const readBin = (f) => readFileSync(path.join(DIR, f));
const md5 = (buf) => createHash('md5').update(buf).digest('hex').slice(0, 8);

const problems = [];
const changed = [];

function write(file, next) {
  const full = path.join(DIR, file);
  /* Файла может ещё не быть: так появилась копия calc.js в теме. */
  const prev = existsSync(full) ? readFileSync(full, 'utf8') : null;
  if (prev === next) return;
  changed.push(file);
  if (!CHECK_ONLY) writeFileSync(full, next);
}

/* ==========================================================================
   1. Отпечатки содержимого
   ========================================================================== */

const cssFingerprint = md5(readBin('assets/style.css'));
const jsFingerprint = md5(readBin('assets/app.js'));
/* Калькулятор — отдельный файл: 14 расчётов нужны на одной странице,
   и тащить их на каждую страницу сайта в app.js незачем. */
const calcFingerprint = md5(readBin('assets/calc.js'));

for (const [name] of PAGES) {
  const file = `${name}.html`;
  const next = read(file)
    .replace(/assets\/style\.css(\?v=[a-f0-9]+)?/g, `assets/style.css?v=${cssFingerprint}`)
    .replace(/assets\/app\.js(\?v=[a-f0-9]+)?/g, `assets/app.js?v=${jsFingerprint}`)
    .replace(/assets\/calc\.js(\?v=[a-f0-9]+)?/g, `assets/calc.js?v=${calcFingerprint}`);
  write(file, next);
}

/* ==========================================================================
   1a. Типографика: висячие предлоги
   ========================================================================== */

/* По-русски нельзя обрывать строку на предлоге или союзе: «Товары для
   дома и» / «дачи…» читается как спотыкание. Ни один браузер этого сам
   не делает — text-wrap: balance выравнивает длину строк, но про предлоги
   не знает. Поэтому короткие слова связываются со следующим неразрывным
   пробелом, а тире — с предыдущим словом, чтобы не начинать строку.
   Проход идёт только по тексту между тегами: содержимое атрибутов,
   <script> и <style> не трогается. */
/* Однобуквенные и двухбуквенные — обязательно, плюс короткие предлоги.
   Союзы «что» и «как» намеренно не берём: они длиннее, начинать с них
   строку не ошибка, а на узком экране связка вышла бы слишком длинной
   и распирала бы вёрстку. */
const SHORT_WORDS = 'а|в|и|к|о|с|у|я|бы|во|да|до|же|за|из|ко|ли|на|не|ни|но|об|от|по|со|то|ту|уж|для|при|над|под|про|без';

function typography(text) {
  return (
    text
      /* предлог или союз в начале — приклеиваем к следующему слову */
      .replace(new RegExp(`(^|[\\s(«"])(${SHORT_WORDS})\\s+(?=[«"(\\wА-Яа-яЁё])`, 'gi'), '$1$2 ')
      /* тире не начинает строку — держим его при предыдущем слове */
      .replace(/(\S) +—/g, '$1 —')
      /* число и единица не расходятся по строкам: «10 м²», «500 ₽» */
      .replace(/(\d) +(₽|%|м²|м³|мм|см|кг|шт|л|т)\b/g, '$1 $2')
  );
}

/* Слово, за которым идёт строчный тег, разбито на два куска: «посчитайте в »
   и <a>калькуляторе</a>. Внутри одного куска связать их нельзя — предлог
   оказывается последним словом текста, и просмотр вперёд не срабатывает.
   Поэтому конец куска проверяем отдельно, зная, какой тег идёт следом. */
const INLINE_TAGS = /^(a|b|i|em|strong|span|abbr|small|sup|sub|time|mark)$/i;
const TRAILING_SHORT = new RegExp(`(^|[\\s(«"])(${SHORT_WORDS}) $`, 'i');

function applyTypography(html) {
  const skip = /^(script|style|pre|textarea)$/i;
  let out = '';
  let pos = 0;
  let muted = null;
  const tag = /<\/?([a-zA-Z][\w-]*)\b[^>]*>/g;
  let m;
  while ((m = tag.exec(html))) {
    let text = html.slice(pos, m.index);
    if (!muted) {
      text = typography(text);
      const name = m[1].toLowerCase();
      if (!m[0].startsWith('</') && INLINE_TAGS.test(name)) {
        text = text.replace(TRAILING_SHORT, '$1$2 ');
      }
    }
    out += text + m[0];
    pos = tag.lastIndex;
    const name = m[1].toLowerCase();
    if (!m[0].startsWith('</') && skip.test(name)) muted = name;
    else if (m[0].startsWith('</') && muted === name) muted = null;
  }
  return out + (muted ? html.slice(pos) : typography(html.slice(pos)));
}

for (const [name] of PAGES) {
  const file = `${name}.html`;
  write(file, applyTypography(read(file)));
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

/* Картинки и шрифты главной (assets/home, assets/fonts) тоже уезжают
   в файл. <source> с AVIF в превью не нужны: остаётся одна картинка
   <img>, и вместо JPEG сцены берётся WebP среднего размера — он легче. */
const MIME = { webp: 'image/webp', png: 'image/png', jpg: 'image/jpeg', avif: 'image/avif', woff2: 'font/woff2' };
const dataUri = (file) => `data:${MIME[file.split('.').pop()]};base64,${readBin(file).toString('base64')}`;
const PREVIEW_SWAP = { 'assets/home/scene-1200.jpg': 'assets/home/scene-1600.webp' };
function inlineAssets(html) {
  return html
    .replace(/<source[^>]*srcset="assets\/[^"]*"[^>]*>/g, '')
    .replace(/<img\b([^>]*?)\ssrc="(assets\/[^"]+)"([^>]*)>/g, (m, before, src, after) => {
      const attrs = (before + after).replace(/\s(?:srcset|sizes)="[^"]*"/g, '');
      return `<img${attrs} src="${dataUri(PREVIEW_SWAP[src] || src)}">`;
    });
}
const inlineFonts = (css) => css.replace(/url\("fonts\/([^"]+)"\)/g, (m, f) => `url("${dataUri('assets/fonts/' + f)}")`);
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

const inlineAll = (html) => inlineAssets(inlineImages(html));

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
  /* Правила предзагрузки соседних страниц в превью не нужны: отдельных
     файлов рядом с ним нет, и браузер ходил бы за ними впустую. */
  .replace(/\s*<script type="speculationrules">[\s\S]*?<\/script>/g, '')
  .replace(/\s*<script src="assets\/app\.js[^"]*"><\/script>\s*<\/body>\s*<\/html>\s*$/, '');

const previewCss = `
/* Панель переключения страниц — только для этого файла-просмотра.

   Страниц стало четырнадцать, и переносом по строкам панель съедала
   на телефоне больше половины экрана: человек открывал ссылку и видел
   не сайт, а список вкладок. Поэтому она в одну строку с прокруткой
   вбок — высота фиксированная независимо от числа страниц. */
.preview-bar{position:sticky;top:0;z-index:60;display:flex;align-items:center;
  gap:8px;padding:10px 16px;background:var(--sg-ink);color:#fff;font-size:14px;
  flex-wrap:nowrap;overflow-x:auto;overscroll-behavior-x:contain;
  scrollbar-width:none}
.preview-bar::-webkit-scrollbar{display:none}
.preview-bar__label{font-weight:700;margin-right:4px;flex:none}
.preview-tab{display:inline-block;padding:8px 14px;border-radius:6px;background:rgba(255,255,255,.12);
  color:#fff;font-weight:600;text-decoration:none;white-space:nowrap;flex:none}
.preview-tab:hover{background:rgba(255,255,255,.22);text-decoration:none}
.preview-tab[aria-current="true"]{background:var(--sg-red)}
.preview-hint{margin-left:auto;padding-left:16px;color:#c9c9d4;font-size:13px;white-space:nowrap;flex:none}
.preview-page{display:none}
.preview-page.is-active{display:block}
/* Подсказка про один файл на телефоне не помещается и не нужна:
   человек и так уже открыл этот файл. */
@media (max-width:900px){.preview-hint{display:none}
  .preview-bar{padding:8px 12px;gap:6px;font-size:13px}
  .preview-tab{padding:7px 11px}}
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
      var on = l.getAttribute('data-tab-link') === id;
      l.setAttribute('aria-current', on ? 'true' : 'false');
      // Панель прокручивается вбок: подтягиваем открытую вкладку в видимую
      // часть, иначе на телефоне она остаётся за правым краем.
      if (on && l.scrollIntoView) l.scrollIntoView({block: 'nearest', inline: 'center'});
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

const preview = inlineAll(
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
${inlineFonts(read('assets/style.css').trim())}
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

${read('assets/calc.js').trim()}

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
   4. Тема OpenCart берёт те же стили и тот же скрипт
   ========================================================================== */

/* Тема живёт своей копией style.css и app.js: движок отдаёт их
   из catalog/view/theme/…, а не из папки assets. Копии делались руками,
   и это ровно та ошибка, которую здесь принято ловить заранее: правку
   в макете видно сразу, а на живом сайте всё по-старому, и причину
   искать негде - файлы называются одинаково.

   Отпечаток подставляется тот же, что и в макете. Раньше в шаблоне
   стояло `asset_v = '1'`, и после каждой правки стилей заказчику
   приходилось объяснять, что надо нажать Ctrl+F5. */

const THEME_DIR = 'opencart-theme/catalog/view/theme/stroigeroi2026';
const COPIES = [
  ['assets/style.css', `${THEME_DIR}/stylesheet/style.css`],
  ['assets/app.js', `${THEME_DIR}/javascript/app.js`],
  ['assets/calc.js', `${THEME_DIR}/javascript/calc.js`],
];

for (const [from, to] of COPIES) {
  write(to, read(from));
}

/* Шрифты лежат рядом со стилями (url("fonts/…") в style.css), картинки
   главной — в image/home темы. Копируются байт в байт, как есть. */
const BINARY_DIRS = [
  ['assets/fonts', `${THEME_DIR}/stylesheet/fonts`],
  ['assets/home', `${THEME_DIR}/image/home`],
];
for (const [from, to] of BINARY_DIRS) {
  mkdirSync(path.join(DIR, to), { recursive: true });
  for (const f of readdirSync(path.join(DIR, from))) {
    const src = path.join(DIR, from, f);
    const dst = path.join(DIR, to, f);
    const buf = readFileSync(src);
    let same = false;
    try { same = readFileSync(dst).equals(buf); } catch { /* файла ещё нет */ }
    if (same) continue;
    changed.push(`${to}/${f}`);
    if (!CHECK_ONLY) writeFileSync(dst, buf);
  }
}

/* Отпечаток один на все файлы темы: style.css, opencart.css, app.js
   и calc.js. Шапка, подвал и калькулятор рисуются движком по отдельности,
   своими вызовами, поэтому `asset_v` объявляется в каждом из этих
   шаблонов — значение одно и то же. */
const assetV = md5(Buffer.concat([
  readBin('assets/style.css'),
  readBin(`${THEME_DIR}/stylesheet/opencart.css`),
  readBin('assets/app.js'),
  readBin('assets/calc.js'),
]));

for (const tpl of ['common/header', 'common/footer', 'information/calculator']) {
  const file = `${THEME_DIR}/template/${tpl}.twig`;
  const mark = /\{% set asset_v = '[^']*' %\}/;
  if (!mark.test(read(file))) {
    problems.push(`в ${tpl}.twig нет строки {% set asset_v = … %} — тема потеряет отпечаток стилей`);
    continue;
  }
  write(file, read(file).replace(mark, `{% set asset_v = '${assetV}' %}`));
}

/* ==========================================================================
   Итог
   ========================================================================== */

console.log(`Отпечатки: style.css ?v=${cssFingerprint}, app.js ?v=${jsFingerprint}, calc.js ?v=${calcFingerprint}`);
console.log(`Тема OpenCart: asset_v = ${assetV}`);
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

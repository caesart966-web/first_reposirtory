'use strict';
/**
 * Сборка буклетов. Оглавление собирается в два прохода: первый проход даёт
 * документ без номеров страниц, он рендерится в PDF, из PDF снимается карта
 * «заголовок → страница», второй проход подставляет настоящие номера.
 */
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFileSync } = require('child_process');
const { writeBooklet } = require('./lib/make');
const { plain } = require('./lib/inline');

const DIST = path.join(__dirname, 'dist');

const BOOKLETS = {
  export: { spec: './content/export-operations', file: 'Turkish-Export-Operations-Field-Guide.docx' },
  deik: { spec: './content/deik-formation', file: 'DEIK-Economic-Diplomacy-Formation-Guide.docx' },
};

function needleFor(entry) {
  if (entry.key === 'FWD') return 'Foreword';
  if (entry.key === 'BIB') return 'Bibliography';
  if (entry.key === 'IDX') return 'Index';
  if (entry.key.startsWith('C')) return `CHAPTER ${entry.key.slice(1)}`;
  if (entry.key.startsWith('A')) return entry.title;
  return `${entry.label} ${plain(entry.title)}`;
}

function renderPdf(docx, outDir) {
  execFileSync('soffice', ['--headless', '--norestore', '--convert-to', 'pdf', '--outdir', outDir, docx],
    { stdio: 'ignore', timeout: 600000 });
  return path.join(outDir, path.basename(docx).replace(/\.docx$/, '.pdf'));
}

function pageMap(pdf, headings, tmp) {
  const needles = headings.map((h) => ({ key: h.key, needle: needleFor(h) }));
  const file = path.join(tmp, 'needles.json');
  fs.writeFileSync(file, JSON.stringify(needles));
  const out = execFileSync('python3', [path.join(__dirname, 'tools', 'pagemap.py'), pdf, file], { encoding: 'utf8' });
  return JSON.parse(out);
}

async function build(name) {
  const config = BOOKLETS[name];
  if (!config) throw new Error('Bilinmeyen buklet: ' + name);
  delete require.cache[require.resolve(config.spec)];
  const spec = require(config.spec);
  const out = path.join(DIST, config.file);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'booklet-'));

  let info = await writeBooklet(spec, out, null);
  let pdf = renderPdf(out, tmp);
  let map = pageMap(pdf, info.headings, tmp);

  info = await writeBooklet(spec, out, map.pages);
  pdf = renderPdf(out, tmp);
  const check = pageMap(pdf, info.headings, tmp);

  const drifted = Object.keys(check.pages).filter((k) => check.pages[k] !== map.pages[k]);
  if (drifted.length) {
    // Sayfa numaralarının eklenmesi sayfalamayı kaydırdıysa bir tur daha.
    info = await writeBooklet(spec, out, check.pages);
    pdf = renderPdf(out, tmp);
  }
  const final = pageMap(pdf, info.headings, tmp);
  const stillDrifting = Object.keys(final.pages).filter((k) => final.pages[k] !== check.pages[k]);

  console.log(`${config.file}`);
  console.log(`  sayfa       : ${final.total}`);
  console.log(`  başlık      : ${info.headings.length} (içindekilerde)`);
  console.log(`  dipnot      : ${info.footnotes}`);
  if (final.missing.length) console.log(`  BULUNAMAYAN : ${final.missing.join(', ')}`);
  if (stillDrifting.length) console.log(`  KAYAN SAYFA : ${stillDrifting.join(', ')}`);
  else console.log('  içindekiler : sayfa numaraları oturdu');
  fs.copyFileSync(pdf, path.join(DIST, path.basename(pdf)));
  fs.rmSync(tmp, { recursive: true, force: true });
  return final;
}

async function main() {
  const target = process.argv[2] || 'all';
  const names = target === 'all' ? Object.keys(BOOKLETS) : [target];
  for (const name of names) await build(name);
}

main().catch((error) => { console.error(error); process.exit(1); });

// node shot.mjs view.html outdir — снимки видов модели
import { chromium } from 'playwright-core';
import path from 'node:path';
const [html, outdir, ...views] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const p = await b.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1.5 });
p.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
p.on('pageerror', e => console.log('pageerror:', e.message));
for (const v of (views.length ? views : ['iso'])) {
  const [name, q] = v.split('?');
  await p.goto('file://' + path.resolve(html) + '?' + (q || `view=${name}&ui=0`));
  await p.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  await p.waitForTimeout(700);
  await p.screenshot({ path: path.join(outdir, name + '.png') });
  console.log('ok', name);
}
await b.close();

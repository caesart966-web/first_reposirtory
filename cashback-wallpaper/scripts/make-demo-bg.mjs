// Два тестовых фона для демо: светлый пастельный и тёмный вечерний.
// Настоящие обои делаются на фоне пользователя — эти только показывают,
// как стекло подстраивается под светлое и тёмное.
import { mkdirSync } from 'node:fs';
import { chromium } from 'playwright';

const W = 440, H = 956;
const grain = `<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 .55 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>`;
const scenes = {
  'demo-light': `
    background:
      radial-gradient(60% 40% at 18% 22%, #f6d5c3 0%, transparent 70%),
      radial-gradient(55% 35% at 85% 40%, #dfe5d0 0%, transparent 70%),
      radial-gradient(70% 45% at 40% 70%, #f3e3cf 0%, transparent 70%),
      radial-gradient(50% 30% at 90% 88%, #e9c9b8 0%, transparent 70%),
      #f4ece2;`,
  'demo-dark': `
    background:
      radial-gradient(45% 28% at 75% 30%, #b6566b 0%, transparent 70%),
      radial-gradient(60% 35% at 20% 55%, #3d3f8f 0%, transparent 72%),
      radial-gradient(70% 30% at 60% 92%, #e08a5a 0%, transparent 70%),
      radial-gradient(40% 25% at 15% 15%, #22305e 0%, transparent 70%),
      linear-gradient(180deg, #0e1226 0%, #1b1838 55%, #3a2140 100%);`,
};

mkdirSync('backgrounds', { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 3 });
for (const [name, css] of Object.entries(scenes)) {
  await page.setContent(`<html><body style="margin:0;width:${W}px;height:${H}px;${css}">
    <div style="position:absolute;inset:0;background:url(&quot;data:image/svg+xml,${grain}&quot;);opacity:.16;mix-blend-mode:overlay"></div>
  </body></html>`);
  await page.screenshot({ path: `backgrounds/${name}.jpg`, type: 'jpeg', quality: 92 });
  console.log(`backgrounds/${name}.jpg`);
}
await browser.close();

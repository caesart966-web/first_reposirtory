// node html2pdf.js in.html out.pdf [widthmm heightmm]
const { chromium } = require('playwright');
(async () => {
  const [inp, out, w = '210', h = '297'] = process.argv.slice(2);
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
  const p = await b.newPage();
  await p.goto('file://' + inp, { waitUntil: 'load' });
  await p.pdf({ path: out, width: w + 'mm', height: h + 'mm', printBackground: true, preferCSSPageSize: true });
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });

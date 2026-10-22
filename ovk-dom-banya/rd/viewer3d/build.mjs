// node build.mjs model.json out.html — собирает просмотрщик в один файл
import { build } from 'esbuild';
import fs from 'node:fs';
const [model, out] = process.argv.slice(2);
const r = await build({ entryPoints: ['main.js'], bundle: true, minify: true, format: 'iife', write: false,
  target: ['es2019'], legalComments: 'eof' });
const js = r.outputFiles[0].text;
const html = fs.readFileSync('template.html', 'utf8')
  .replace('__MODEL__', () => fs.readFileSync(model, 'utf8'))
  .replace('__JS__', () => js.replace(/<\/script/gi, '<\\/script'));
fs.writeFileSync(out, html);
console.log(out, Math.round(html.length / 1024) + ' КБ');

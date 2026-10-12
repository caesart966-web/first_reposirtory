// Выгрузка примитивов DWG раздела ВК (формат AutoCAD 2018 — LibreDWG 0.13 его не читает)
// в JSONL: по строке на примитив пространства модели.
//   npm install @mlightcad/libredwg-web@0.7.17
//   node vk_dump.mjs <файл.dwg> <ents.jsonl>
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const pkg = path.dirname(require.resolve('@mlightcad/libredwg-web/package.json'));
const { Dwg_File_Type, LibreDwg } = await import(path.join(pkg, 'dist', 'libredwg-web.js'));

const [src, dst] = process.argv.slice(2);
const lib = await LibreDwg.create(path.join(pkg, 'wasm') + '/');
const db = lib.convert(lib.dwg_read_data(fs.readFileSync(src), Dwg_File_Type.DWG));
const fd = fs.openSync(dst, 'w');
for (const e of db.entities) fs.writeSync(fd, JSON.stringify(e, (k, v) => (typeof v === 'bigint' ? Number(v) : v)) + '\n');
fs.closeSync(fd);
console.log('примитивов', db.entities.length);

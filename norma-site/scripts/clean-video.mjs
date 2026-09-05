// Чистит ролик, сгенерированный нейросетью, перед сжатием.
//
// Зачем понадобился. Ролик с картой России, который прислал заказчик,
// пришёл с тремя болячками, типичными для видеогенераторов:
//
//   1. Водяной знак в углу — четырёхлучевая звёздочка сервиса.
//   2. Подписи городов латиницей, которых в задании не было: Magadan,
//      Yakutsk, Vladivostok. Причём каждая по два раза в разных местах,
//      а одно слово вообще не читается — набор букв. На сайте, который
//      весь построен на точности, «Vladivostok» латиницей — приговор.
//   3. Ролик кончается не там, где начался: поставленный на повтор,
//      он дёргается на стыке.
//
// Что делает скрипт:
//
//   • обрезает ролик до момента, пока подписи ещё не появились;
//   • по желанию обрезает и сам кадр: у карты сверху и снизу оставалось
//     пустое море, из-за которого страна на сайте выходила мелкой;
//   • закрашивает водяной знак (delogo достраивает пиксели по краям
//     рамки, а мягкое размытие поверх убирает след от этой достройки —
//     без второго шага остаётся вертикальная полоска);
//   • склеивает петлю «туда и обратно»: прямой ход, затем тот же ход
//     задом наперёд. Стык получается идеальным по определению, а движение
//     читается как дыхание. Кадр на развороте и кадр на замыкании
//     выбрасываются — иначе они показались бы дважды подряд.
//
// Запуск:
//   node scripts/clean-video.mjs <исходник.mp4> <результат.mp4> [сек] [знак] [кадр]
//   где «знак» и «кадр» — рамки вида x,y,ширина,высота
//   node scripts/clean-video.mjs ~/karta.mp4 /tmp/master.mp4 4.3 1126,566,68,64 0,56,1280,604
//
// ВАЖНО: если меняете обрезку кадра, поменяйте и пропорцию полосы в
// src/components/MapPlate.astro (свойство aspect-ratio) — иначе по краям
// карты появятся пустые поля.
//
// Как найти, с какой секунды лезут подписи, и где именно знак:
//   node scripts/clean-video.mjs --кадры <исходник.mp4>
// — разложит ролик на картинки по полсекунды, останется их пролистать.
//
// Результат — промежуточный файл без сжатия для сайта. Дальше его
// нужно пропустить через scripts/encode-video.mjs.

import { spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const ffmpeg = spawnSync('python3', [
  '-c',
  'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())',
]).stdout?.toString().trim()

if (!ffmpeg || !existsSync(ffmpeg)) {
  console.error('Не нашёл ffmpeg. Поставьте его: pip install imageio-ffmpeg')
  process.exit(1)
}

const args = process.argv.slice(2)

// Режим осмотра: разложить ролик на кадры и показать, куда их положил.
if (args[0] === '--кадры' || args[0] === '--frames') {
  const src = args[1]
  if (!src || !existsSync(src)) {
    console.error('Как запускать: node scripts/clean-video.mjs --кадры <исходник.mp4>')
    process.exit(1)
  }
  const dir = mkdtempSync(join(tmpdir(), 'kadry-'))
  const r = spawnSync(ffmpeg, ['-y', '-loglevel', 'error', '-i', src,
    '-vf', 'fps=2,drawtext=text=%{pts\\\\:hms}:x=16:y=16:fontsize=28:fontcolor=yellow',
    join(dir, '%03d.png')])
  if (r.status !== 0) {
    // Подпись времени рисуется шрифтом из системы, а его может не быть.
    spawnSync(ffmpeg, ['-y', '-loglevel', 'error', '-i', src, '-vf', 'fps=2', join(dir, '%03d.png')])
    console.log('Время на кадрах подписать не вышло (нет системного шрифта).')
    console.log('Кадры идут по два в секунду: 001 — это 0.0 с, 002 — 0.5 с и так далее.')
  }
  console.log(`Кадры здесь: ${dir}`)
  process.exit(0)
}

const [src, out, until = '4.3', logo = '', frame = ''] = args
if (!src || !out) {
  console.error('Как запускать: node scripts/clean-video.mjs <исходник.mp4> <результат.mp4> [сек] [знак] [кадр]')
  process.exit(1)
}

const box = (v, what) => {
  const n = v.split(',').map(Number)
  if (n.length !== 4 || n.some((x) => !Number.isFinite(x))) {
    console.error(`${what} задают четырьмя числами через запятую: x,y,ширина,высота`)
    process.exit(1)
  }
  return n
}
if (!existsSync(src)) {
  console.error(`Не нашёл файл: ${src}`)
  process.exit(1)
}

const chain = [`trim=0:${until}`, 'setpts=PTS-STARTPTS']

if (logo) {
  const [x, y, w, h] = box(logo, 'Рамку знака')
  // Достраиваем пиксели под рамкой…
  chain.push(`delogo=x=${x}:y=${y}:w=${w}:h=${h}`)
}

// Обрезка кадра идёт последней: координаты водяного знака заданы по
// исходному кадру, и обрежь мы раньше — рамка уехала бы.
const cropTail = frame
  ? (() => {
      // Рамки во всём скрипте пишутся как x,y,ширина,высота — так их удобнее
      // снимать с картинки. У ffmpeg порядок другой: ширина:высота:x:y.
      const [x, y, w, h] = box(frame, 'Рамку кадра')
      return `,crop=${w}:${h}:${x}:${y}`
    })()
  : ''

const filters = logo
  ? (() => {
      const [x, y, w, h] = box(logo, 'Рамку знака')
      // …и растушёванным пятном размытия убираем след от достройки.
      // Пятно берётся с запасом вокруг рамки и гаснет к краям по гауссу,
      // поэтому прямоугольной заплатки на картинке не видно.
      const px = Math.max(0, x - 31)
      const py = Math.max(0, y + 8)
      const pw = w + 62
      const ph = h + 32
      return `${chain.join(',')}[d];` +
        `[d]split[base][src];` +
        `[src]crop=${pw}:${ph}:${px}:${py},gblur=sigma=9,format=yuva420p,` +
        `geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':` +
        `a='255*exp(-((pow(X-${Math.round(pw / 2)},2)+pow(Y-${Math.round(ph / 2)},2))/(2*pow(38,2))))'[patch];` +
        `[base][patch]overlay=${px}:${py}${cropTail}[c]`
    })()
  : `${chain.join(',')}${cropTail}[c]`

// Петля «туда и обратно». reverse держит весь отрезок в памяти —
// поэтому обрезка идёт до него, а не после.
const complex =
  `[0:v]${filters};` +
  `[c]split[a][b];[b]reverse,trim=start_frame=1,setpts=PTS-STARTPTS[r];` +
  `[a][r]concat=n=2:v=1:a=0[cat];[cat]trim=start_frame=0,setpts=PTS-STARTPTS[v]`

process.stdout.write('Чищу и заворачиваю в петлю… ')
const r = spawnSync(ffmpeg, ['-y', '-loglevel', 'error', '-i', src, '-an',
  '-filter_complex', complex, '-map', '[v]',
  '-c:v', 'libx264', '-crf', '12', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', out],
  { stdio: ['ignore', 'pipe', 'pipe'] })

if (r.status !== 0) {
  console.log('не вышло')
  console.error(r.stderr?.toString())
  process.exit(1)
}
console.log('готово')
console.log(`\n${out}\nДальше: node scripts/encode-video.mjs ${out} hero karta\n`)

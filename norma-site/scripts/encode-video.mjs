// Готовит присланный ролик к публикации на сайте.
//
// Зачем скрипт. Ролик из нейросети весит 5–7 МБ и снят в дымке: на сайте
// он выглядит блёкло, а на телефоне открывается мучительно долго. Здесь
// он ужимается примерно в семь раз и получает фирменную обработку.
// Раньше эти команды жили только в истории разработчика — теперь их
// можно повторить одной строкой.
//
// Запуск:
//   node scripts/encode-video.mjs <исходник.mp4> <имя-на-сайте>
//   node scripts/encode-video.mjs ~/uslugi.mp4 uslugi
//
// Получится три файла в public/video/:
//   uslugi.webm         — для Chrome, Яндекс.Браузера, Firefox, Edge
//   uslugi.mp4          — для Safari и айфонов
//   uslugi-poster.webp  — первый кадр, показывается пока ролик грузится
//
// Что делается с картинкой:
// • контраст, гамма и насыщенность поднимаются прямо в файле. Делать это
//   фильтром в браузере нельзя: он пересчитывает каждый кадр на видеокарте
//   и заметно греет телефон;
// • верх кадра дополнительно притемняется. Небо в кадре почти всегда
//   светлее остального, а поверх него идёт белый текст;
// • звук выбрасывается совсем. Браузеры запрещают автозапуск со звуком,
//   так что дорожка всё равно не прозвучала бы, а место занимает.

import { spawnSync } from 'node:child_process'
import { existsSync, statSync, mkdirSync } from 'node:fs'
import { resolve, join } from 'node:path'

const [src, name, preset = 'stroyka'] = process.argv.slice(2)
if (!src || !name) {
  console.error('Как запускать: node scripts/encode-video.mjs <исходник.mp4> <имя-на-сайте> [обработка]')
  console.error('Обработка: stroyka (по умолчанию) или karta')
  process.exit(1)
}
if (!existsSync(src)) {
  console.error(`Не нашёл файл: ${src}`)
  process.exit(1)
}

// ffmpeg берём из пакета imageio-ffmpeg — он ставится вместе с Python
// и не требует отдельной установки в систему.
const ffmpeg = spawnSync('python3', [
  '-c',
  'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())',
]).stdout?.toString().trim()

if (!ffmpeg || !existsSync(ffmpeg)) {
  console.error('Не нашёл ffmpeg. Поставьте его: pip install imageio-ffmpeg')
  process.exit(1)
}

const OUT = resolve('public/video')
mkdirSync(OUT, { recursive: true })

// Обработка картинки, одна на все форматы. Обработок две, потому что
// съёмка и рисованная карта требуют противоположного.
//
// stroyka — для настоящей съёмки стройки. Кадр снят в утренней дымке:
//   eq       — контраст, гамма и насыщенность вытягивают его из молока;
//   gradfun  — убирает ступеньки на небе. После подъёма контраста ровная
//              заливка распадается на полосы, и на градиенте это видно;
//   geq      — верхняя четверть кадра гасится ещё на 18%. Небо всегда самое
//              светлое место, а первая строка текста идёт как раз по нему.
//
// karta — для карты России, нарисованной нейросетью. Её вытягивать не надо:
//   она и так тёмная и контрастная, и та же обработка, что спасает съёмку,
//   превратила бы море в чёрное, а точки городов — в белые кляксы. Здесь
//   контраст поднимается едва-едва, зато добавляется виньетка: середина
//   кадра с картой остаётся яркой, а края гаснут и сходятся с тёмно-синим
//   фоном секции, так что граница ролика на странице не читается.
// Вместе с обработкой у каждого набора своя сила сжатия. Съёмка стройки —
// это шум, листва и мелкая фактура: там сжимать приходится жёстко, иначе
// файл не влезает в бюджет. Карта — крупные ровные заливки, она ужимается
// сама по себе, и на тех же настройках вышла бы вчетверо легче нормы,
// зато с мылом вместо рельефа. Поэтому для карты числа мягче.
const GRADES = {
  stroyka: {
    filter: [
      'eq=contrast=1.55:gamma=1.12:saturation=1.35',
      'gradfun=strength=1.2:radius=16',
      "geq=lum='lum(X,Y)*(1-0.18*max(0,1-Y/(H/4)))':cb='cb(X,Y)':cr='cr(X,Y)'",
    ].join(','),
    webmCrf: '34',
    webmRate: '600k',
    mp4Crf: '35',
  },
  karta: {
    filter: [
      'eq=contrast=1.14:gamma=1.02:saturation=1.18',
      'vignette=angle=PI/6.2',
      'gradfun=strength=1.1:radius=16',
    ].join(','),
    webmCrf: '30',
    webmRate: '900k',
    mp4Crf: '28',
  },
}

const cfg = GRADES[preset]
if (!cfg) {
  console.error(`Не знаю обработку «${preset}». Есть: ${Object.keys(GRADES).join(', ')}`)
  process.exit(1)
}
const GRADE = cfg.filter

const run = (args, what) => {
  process.stdout.write(`  ${what}… `)
  const r = spawnSync(ffmpeg, ['-y', '-loglevel', 'error', ...args], { stdio: ['ignore', 'pipe', 'pipe'] })
  if (r.status !== 0) {
    console.log('не вышло')
    console.error(r.stderr?.toString())
    process.exit(1)
  }
  console.log('готово')
}

const kb = (f) => Math.round(statSync(f).size / 1024)

console.log(`\nГотовлю «${name}» из ${src}, обработка «${preset}»\n`)

// WebM (VP9). Основной формат: при том же весе картинка заметно чище,
// чем у MP4. Два прохода — первый собирает статистику по всему ролику,
// второй по ней распределяет биты. Разница против одного прохода видна
// на движении камеры.
const webm = join(OUT, `${name}.webm`)
const passLog = join(OUT, `.${name}-pass`)
const vp9 = ['-vf', GRADE, '-an', '-c:v', 'libvpx-vp9', '-b:v', cfg.webmRate, '-crf', cfg.webmCrf,
  '-row-mt', '1', '-tile-columns', '2', '-g', '240', '-passlogfile', passLog]
run(['-i', src, ...vp9, '-pass', '1', '-f', 'null', '/dev/null'], 'webm, первый проход')
run(['-i', src, ...vp9, '-pass', '2', webm], 'webm, второй проход')

// MP4 (H.264). Нужен только для Safari и айфонов: они не умеют VP9
// в фоновом видео. Профиль main и yuv420p — чтобы файл открылся
// и на старых устройствах тоже.
//
// Сжатие сильнее, чем у webm (crf 35 против 34), и это не описка:
// H.264 старше и при равном числе даёт файл вдвое тяжелее. Подобрано
// так, чтобы оба формата весили примерно одинаково.
const mp4 = join(OUT, `${name}.mp4`)
run([
  '-i', src, '-vf', GRADE, '-an',
  '-c:v', 'libx264', '-profile:v', 'main', '-pix_fmt', 'yuv420p',
  '-crf', cfg.mp4Crf, '-preset', 'slow', '-movflags', '+faststart',
  mp4,
], 'mp4')

// Постер: первый кадр ролика с той же обработкой, иначе в момент запуска
// видео картинка заметно «моргнёт» яркостью.
const poster = join(OUT, `${name}-poster.webp`)
run(['-i', src, '-vf', GRADE, '-frames:v', '1', '-q:v', '58', poster], 'постер')

// Файл статистики от двухпроходного сжатия в сборке не нужен.
spawnSync('rm', ['-f', `${passLog}-0.log`])

console.log(`\nГотово:
  ${name}.webm         ${kb(webm)} КБ
  ${name}.mp4          ${kb(mp4)} КБ
  ${name}-poster.webp  ${kb(poster)} КБ

Если webm или mp4 вышли тяжелее 900 КБ — поднимите crf (34 → 36) и повторите.
Чем больше число, тем сильнее сжатие и тем хуже картинка.\n`)

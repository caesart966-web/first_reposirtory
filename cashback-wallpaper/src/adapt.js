/* Подгонка стекла и цветов под фон. Работает в браузере до съёмки кадра.

   Считает не «на глаз», а по настоящим пикселям фона: берёт прямоугольник
   под карточкой, усредняет его так, как это сделает размытие стекла,
   и подбирает непрозрачность стекла — наименьшую, при которой самая
   тёмная и самая светлая точка под карточкой всё ещё дают тексту 4.5:1.
   Стекло должно оставаться стеклом: чем меньше заливки, тем лучше,
   но не ценой читаемости.

   Фирменные цвета банков подгоняются в OKLCH: тон и насыщенность
   сохраняются, меняется только светлота. Иначе жёлтый Т-Банка
   на светлом фоне даёт 1.4:1, а синий Ozon на тёмном — 2.1:1;
   и то и другое на обоях нечитаемо. */

(() => {
  /* ——— sRGB ↔ OKLab ——— */
  const srgbToLin = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  const linToSrgb = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055);

  function hexToRgb(hex) {
    const h = hex.replace('#', '');
    const n = h.length === 3 ? h.split('').map((x) => x + x).join('') : h;
    return [parseInt(n.slice(0, 2), 16), parseInt(n.slice(2, 4), 16), parseInt(n.slice(4, 6), 16)];
  }
  const rgbToHex = (r, g, b) =>
    '#' + [r, g, b].map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0')).join('');

  function rgbToOklab([r, g, b]) {
    const R = srgbToLin(r / 255), G = srgbToLin(g / 255), B = srgbToLin(b / 255);
    const l = Math.cbrt(0.4122214708 * R + 0.5363325363 * G + 0.0514459929 * B);
    const m = Math.cbrt(0.2119034982 * R + 0.6806995451 * G + 0.1073969566 * B);
    const s = Math.cbrt(0.0883024619 * R + 0.2817188376 * G + 0.6299787005 * B);
    return [
      0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
      1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
      0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    ];
  }

  function oklabToRgb([L, a, b]) {
    const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
    const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
    const s_ = L - 0.0894841775 * a - 1.2914855480 * b;
    const l = l_ ** 3, m = m_ ** 3, s = s_ ** 3;
    return [
      linToSrgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s) * 255,
      linToSrgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s) * 255,
      linToSrgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s) * 255,
    ];
  }

  const inGamut = ([r, g, b]) => r >= -0.5 && g >= -0.5 && b >= -0.5 && r <= 255.5 && g <= 255.5 && b <= 255.5;

  /* Возврат в охват: светлоту держим, насыщенность отпускаем.
     Наоборот было бы хуже — потеря светлоты означает потерю контраста,
     ради которого всё и затевалось. */
  function fitGamut(L, C, h) {
    let lo = 0, hi = C;
    const at = (c) => oklabToRgb([L, c * Math.cos(h), c * Math.sin(h)]);
    if (inGamut(at(C))) return at(C);
    for (let i = 0; i < 24; i++) {
      const mid = (lo + hi) / 2;
      if (inGamut(at(mid))) lo = mid; else hi = mid;
    }
    return at(lo);
  }

  /* ——— контраст по WCAG ——— */
  const relLum = ([r, g, b]) =>
    0.2126 * srgbToLin(r / 255) + 0.7152 * srgbToLin(g / 255) + 0.0722 * srgbToLin(b / 255);
  function contrast(a, b) {
    const la = relLum(a), lb = relLum(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }
  const over = (fg, bg, alpha) => fg.map((c, i) => c * alpha + bg[i] * (1 - alpha));

  /* ——— чтение фона ——— */
  /* Кадр рисуется по правилу cover — так же, как его покажет CSS.
     Считать по неотмасштабированному исходнику нельзя: обрезанные края
     в замер попадать не должны, а центр — должен, и ровно тот, что видно. */
  function paintBackdrop(img, W, H) {
    const cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    const ctx = cv.getContext('2d', { willReadFrequently: true });
    const s = Math.max(W / img.naturalWidth, H / img.naturalHeight);
    const dw = img.naturalWidth * s, dh = img.naturalHeight * s;
    ctx.drawImage(img, (W - dw) / 2, (H - dh) / 2, dw, dh);
    return ctx;
  }

  /* Локальные средние — приближение того, что сделает backdrop-filter: blur.
     Размытие усредняет окрестность, поэтому в замер идёт не отдельный пиксель
     (его стекло всё равно размажет), а среднее по окну радиусом с размытие. */
  function localMeans(ctx, rect, blurPx, step = 6) {
    const x0 = Math.max(0, Math.floor(rect.x - blurPx));
    const y0 = Math.max(0, Math.floor(rect.y - blurPx));
    const x1 = Math.min(ctx.canvas.width, Math.ceil(rect.x + rect.w + blurPx));
    const y1 = Math.min(ctx.canvas.height, Math.ceil(rect.y + rect.h + blurPx));
    const w = x1 - x0, h = y1 - y0;
    const data = ctx.getImageData(x0, y0, w, h).data;

    const cols = Math.ceil(w / step), rows = Math.ceil(h / step);
    const grid = new Float64Array(cols * rows * 3);
    for (let gy = 0; gy < rows; gy++) {
      for (let gx = 0; gx < cols; gx++) {
        let r = 0, g = 0, b = 0, n = 0;
        for (let y = gy * step; y < Math.min((gy + 1) * step, h); y++) {
          for (let x = gx * step; x < Math.min((gx + 1) * step, w); x++) {
            const i = (y * w + x) * 4;
            r += data[i]; g += data[i + 1]; b += data[i + 2]; n++;
          }
        }
        const k = (gy * cols + gx) * 3;
        grid[k] = r / n; grid[k + 1] = g / n; grid[k + 2] = b / n;
      }
    }

    /* Прямоугольное размытие по сетке: два прохода, по осям. */
    const rad = Math.max(1, Math.round(blurPx / step));
    const blur1 = (src, cw, ch, horiz) => {
      const out = new Float64Array(src.length);
      for (let y = 0; y < ch; y++) {
        for (let x = 0; x < cw; x++) {
          let r = 0, g = 0, b = 0, n = 0;
          for (let d = -rad; d <= rad; d++) {
            const xx = horiz ? Math.min(cw - 1, Math.max(0, x + d)) : x;
            const yy = horiz ? y : Math.min(ch - 1, Math.max(0, y + d));
            const k = (yy * cw + xx) * 3;
            r += src[k]; g += src[k + 1]; b += src[k + 2]; n++;
          }
          const k = (y * cw + x) * 3;
          out[k] = r / n; out[k + 1] = g / n; out[k + 2] = b / n;
        }
      }
      return out;
    };
    const blurred = blur1(blur1(grid, cols, rows, true), cols, rows, false);

    /* Наружу отдаём только то, что реально под карточкой. */
    const samples = [];
    const insetX = Math.round((rect.x - x0) / step), insetY = Math.round((rect.y - y0) / step);
    const spanX = Math.round(rect.w / step), spanY = Math.round(rect.h / step);
    for (let gy = insetY; gy < Math.min(rows, insetY + spanY); gy++) {
      for (let gx = insetX; gx < Math.min(cols, insetX + spanX); gx++) {
        const k = (gy * cols + gx) * 3;
        samples.push([blurred[k], blurred[k + 1], blurred[k + 2]]);
      }
    }
    return samples;
  }

  /* ——— подбор ——— */
  /* Наименьшая непрозрачность стекла, при которой ВСЕ точки под карточкой
     дают тексту нужный контраст. Проверяются все, а не среднее: среднее
     проходит там, где под одним углом карточки текст всё ещё сливается. */
  function solveAlpha(samples, glassRgb, textRgb, target, min = 0.16, max = 0.72) {
    for (let a = min; a <= max + 1e-9; a += 0.01) {
      let worst = Infinity;
      for (const s of samples) worst = Math.min(worst, contrast(textRgb, over(glassRgb, s, a)));
      if (worst >= target) return { alpha: +a.toFixed(2), worst: +worst.toFixed(2), ok: true };
    }
    let worst = Infinity;
    for (const s of samples) worst = Math.min(worst, contrast(textRgb, over(glassRgb, s, max)));
    return { alpha: max, worst: +worst.toFixed(2), ok: false };
  }

  /* Фирменный цвет: тон и насыщенность банка сохраняются, светлота едет
     в сторону контраста ровно настолько, насколько нужно. */
  function fitBrand(hex, backdrops, target) {
    const [L0, A0, B0] = rgbToOklab(hexToRgb(hex));
    const C = Math.hypot(A0, B0), h = Math.atan2(B0, A0);
    const worstAt = (L) => {
      const rgb = fitGamut(L, C, h);
      let w = Infinity;
      for (const bg of backdrops) w = Math.min(w, contrast(rgb, bg));
      return w;
    };
    if (worstAt(L0) >= target) {
      const [r, g, b] = fitGamut(L0, C, h);
      return { hex: rgbToHex(r, g, b), contrast: +worstAt(L0).toFixed(2), moved: 0 };
    }
    /* Куда двигать светлоту — решает фон: на тёмном светлеем, на светлом темнеем. */
    let meanL = 0;
    for (const bg of backdrops) meanL += relLum(bg);
    meanL /= backdrops.length;
    const up = meanL < 0.4;
    let lo = L0, hi = up ? 1 : 0;
    for (let i = 0; i < 30; i++) {
      const mid = (lo + hi) / 2;
      if (worstAt(mid) >= target) hi = mid; else lo = mid;
    }
    const L = hi;
    const [r, g, b] = fitGamut(L, C, h);
    return { hex: rgbToHex(r, g, b), contrast: +worstAt(L).toFixed(2), moved: +(L - L0).toFixed(3) };
  }

  window.__adapt = function (opts) {
    const { blurPx = 30, target = 4.6, targetSoft = 4.2, glassMin = 0.18, mutedMin = 0.62 } = opts || {};
    const root = document.documentElement;
    const W = window.innerWidth, H = window.innerHeight;
    const img = document.getElementById('bg');
    const ctx = paintBackdrop(img, W, H);

    const card = document.querySelector('.card');
    const r = card.getBoundingClientRect();
    const rect = { x: r.left, y: r.top, w: r.width, h: r.height };
    const samples = localMeans(ctx, rect, blurPx);

    let meanL = 0;
    for (const s of samples) meanL += relLum(s);
    meanL /= samples.length;

    /* Тема — от того, что под карточкой. Светлый фон → тёмное стекло
       было бы вернее по контрасту, но темнее и тяжелее; светлое стекло
       с тёмным текстом на светлом фоне выглядит так, как стекло и должно. */
    const dark = meanL < 0.42;
    const glass = dark ? [10, 13, 18] : [255, 255, 255];
    const text = dark ? [252, 252, 253] : [14, 16, 20];

    const main = solveAlpha(samples, glass, text, target, glassMin);
    const alpha = main.alpha;

    /* Фон, который увидит текст, — после наложения стекла. По нему и меряем
       всё остальное: фирменные цвета, приглушённые подписи, линейки. */
    const composited = samples.map((s) => over(glass, s, alpha));

    const brands = {};
    for (const el of document.querySelectorAll('[data-brand]')) {
      const src = el.getAttribute('data-brand');
      if (brands[src]) continue;
      brands[src] = fitBrand(src, composited, target);
    }
    for (const el of document.querySelectorAll('[data-brand]')) {
      el.style.setProperty('--brand', brands[el.getAttribute('data-brand')].hex);
    }

    /* Приглушённая подпись: ей 4.5 не нужно — это не содержание таблицы,
       но и раствориться ей нельзя. Подбираем прозрачность так же честно,
       и так же не даём уйти ниже разумного: на чёрном фоне расчёт
       пропускал 42%, а это уже не «тише», а «не видно». */
    let mutedA = 1;
    for (let a = 1; a >= mutedMin; a -= 0.02) {
      const t = text.map((c, i) => c * a + (dark ? 10 : 255) * (1 - a));
      let worst = Infinity;
      for (const bg of composited) worst = Math.min(worst, contrast(t, bg));
      if (worst >= targetSoft) mutedA = +a.toFixed(2); else break;
    }

    root.style.setProperty('--glass', `rgba(${glass.join(',')},${alpha})`);
    root.style.setProperty('--ink', `rgb(${text.join(',')})`);
    root.style.setProperty('--ink-muted', `rgba(${text.join(',')},${mutedA})`);
    root.style.setProperty('--hairline', dark ? 'rgba(255,255,255,.20)' : 'rgba(10,14,20,.16)');
    root.style.setProperty('--hairline-soft', dark ? 'rgba(255,255,255,.09)' : 'rgba(10,14,20,.08)');
    root.style.setProperty('--edge-top', dark ? 'rgba(255,255,255,.22)' : 'rgba(255,255,255,.85)');
    root.style.setProperty('--card-shadow', dark
      ? '0 30px 80px rgba(0,0,0,.45), 0 2px 10px rgba(0,0,0,.30)'
      : '0 30px 80px rgba(40,34,26,.20), 0 2px 10px rgba(40,34,26,.10)');
    root.dataset.theme = dark ? 'dark' : 'light';

    return {
      theme: dark ? 'dark' : 'light',
      backdropLuminance: +meanL.toFixed(3),
      glassAlpha: alpha,
      textContrast: main.worst,
      textContrastOk: main.ok,
      mutedAlpha: mutedA,
      brands,
      samples: samples.length,
    };
  };
})();

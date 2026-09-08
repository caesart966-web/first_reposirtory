/* Генератор фона. Работает в браузере: рисует в canvas и отдаёт data-URL.
   Фон рисуется, а не берётся стоковой картинкой, по трём причинам:
   он всегда точно в разрешении телефона (никакого растягивания),
   он заведомо спокойный под таблицей (пятна света расставлены так,
   чтобы центр оставался ровным), и его можно пересобрать другим
   размером, не ища заново исходник.

   Все пресеты держат одно правило: в центре — ровное поле без деталей.
   Стекло таблицы размывает то, что под ним; пёстрый центр превращается
   в грязь и роняет контраст текста. */

(() => {
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

  /* Мягкое пятно света: эллипс произвольного наклона.
     Рисуется радиальным градиентом в изменённой системе координат —
     так пятно получается вытянутым и повёрнутым, а не кругом. */
  function bloom(ctx, { x, y, rx, ry, angle = 0, color, alpha }) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.scale(1, ry / rx);
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx);
    g.addColorStop(0, `rgba(${color},${alpha})`);
    g.addColorStop(0.45, `rgba(${color},${alpha * 0.42})`);
    g.addColorStop(0.75, `rgba(${color},${alpha * 0.1})`);
    g.addColorStop(1, `rgba(${color},0)`);
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(0, 0, rx, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  const PRESETS = {
    /* Ночь. Глубокий сине-графитовый лист: синее пятно сверху — от Ozon,
       тёплое снизу — от Т-Банка. Оба приглушены до фона: цвет банка должен
       звучать в его строке, а не в обоях. */
    midnight: {
      base: [['#0E1322', 0], ['#0A0E1A', 0.40], ['#07090F', 1]],
      blooms: [
        { x: 0.78, y: 0.10, rx: 1.00, ry: 0.64, angle: -0.35, color: '0,91,255', alpha: 0.34 },
        { x: 0.10, y: 0.30, rx: 0.84, ry: 0.60, angle: 0.5, color: '62,40,128', alpha: 0.28 },
        { x: 0.16, y: 0.88, rx: 1.00, ry: 0.52, angle: 0.18, color: '255,186,70', alpha: 0.17 },
        { x: 0.96, y: 0.66, rx: 0.72, ry: 0.50, angle: -0.25, color: '0,132,205', alpha: 0.15 },
      ],
      vignette: 0.40,
      grain: 8,
    },

    /* Графит. Ни одного цветного пятна — только свет и тень.
       Самый спокойный вариант: под ним читается любая иконка. */
    graphite: {
      base: [['#1A1B1F', 0], ['#121317', 0.5], ['#0B0C0E', 1]],
      blooms: [
        { x: 0.78, y: 0.10, rx: 1.0, ry: 0.66, angle: -0.3, color: '255,252,244', alpha: 0.10 },
        { x: 0.10, y: 0.70, rx: 0.85, ry: 0.60, angle: 0.35, color: '150,160,180', alpha: 0.07 },
      ],
      vignette: 0.34,
      grain: 8,
    },

    /* Индиго. Тот же приём, что у «ночи», но синего больше и он холоднее:
       вариант для тех, кому графит кажется пустым. */
    indigo: {
      base: [['#12203E', 0], ['#0C142A', 0.45], ['#080B18', 1]],
      blooms: [
        { x: 0.20, y: 0.12, rx: 0.95, ry: 0.60, angle: 0.3, color: '0,91,255', alpha: 0.32 },
        { x: 0.88, y: 0.42, rx: 0.75, ry: 0.55, angle: -0.4, color: '90,60,200', alpha: 0.24 },
        { x: 0.55, y: 0.95, rx: 1.0, ry: 0.50, angle: 0, color: '0,150,220', alpha: 0.14 },
      ],
      vignette: 0.38,
      grain: 8,
    },

    /* Бумага. Светлый вариант: тёплый лист с мягкой тенью по краям.
       Проверка контраста сама переключит таблицу на тёмный текст. */
    paper: {
      base: [['#FBF8F3', 0], ['#F3EFE7', 0.5], ['#E8E2D6', 1]],
      blooms: [
        { x: 0.80, y: 0.14, rx: 0.9, ry: 0.6, angle: -0.3, color: '255,255,255', alpha: 0.75 },
        { x: 0.12, y: 0.78, rx: 0.85, ry: 0.6, angle: 0.3, color: '214,199,175', alpha: 0.35 },
      ],
      vignette: 0.16,
      grain: 6,
    },
  };

  window.__makeBackground = function (w, h, name) {
    const p = PRESETS[name] || PRESETS.midnight;
    const cv = document.createElement('canvas');
    cv.width = w;
    cv.height = h;
    const ctx = cv.getContext('2d');

    const g = ctx.createLinearGradient(0, 0, w * 0.22, h);
    for (const [c, s] of p.base) g.addColorStop(s, c);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);

    const d = Math.hypot(w, h);
    for (const b of p.blooms) {
      bloom(ctx, {
        x: b.x * w, y: b.y * h,
        rx: b.rx * d * 0.5, ry: b.ry * d * 0.5,
        angle: b.angle, color: b.color, alpha: b.alpha,
      });
    }

    /* Виньетка: к краям темнее. Держит взгляд в центре, где таблица.
       Три остановки вместо двух — на двух у чёрного края видна граница:
       глаз ловит перегиб яркости там, где градиент упирается в предел. */
    if (p.vignette) {
      const v = ctx.createRadialGradient(w / 2, h * 0.47, w * 0.18, w / 2, h * 0.5, d * 0.70);
      v.addColorStop(0, 'rgba(0,0,0,0)');
      v.addColorStop(0.55, `rgba(0,0,0,${p.vignette * 0.28})`);
      v.addColorStop(0.82, `rgba(0,0,0,${p.vignette * 0.68})`);
      v.addColorStop(1, `rgba(0,0,0,${p.vignette})`);
      ctx.fillStyle = v;
      ctx.fillRect(0, 0, w, h);
    }

    /* Зерно. Без него у градиента на телефоне видны кольца (бандинг):
       8-битный экран не умеет плавно, а шум разбивает границы полос. */
    if (p.grain) {
      const img = ctx.getImageData(0, 0, w, h);
      const px = img.data;
      const amp = p.grain;
      for (let i = 0; i < px.length; i += 4) {
        const n = (Math.random() - 0.5) * amp;
        px[i] = clamp(px[i] + n, 0, 255);
        px[i + 1] = clamp(px[i + 1] + n, 0, 255);
        px[i + 2] = clamp(px[i + 2] + n, 0, 255);
      }
      ctx.putImageData(img, 0, 0);
    }

    return cv.toDataURL('image/png');
  };

  window.__backgroundPresets = Object.keys(PRESETS);
})();

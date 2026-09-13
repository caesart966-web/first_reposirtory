// Генератор презентации к докладу «Налоговое законодательство при трансграничной торговле»
// Запуск: node build-presentation.js
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.author = "Доклад";
pres.title = "Налоговое законодательство при трансграничной торговле";

const W = 13.333;
const H = 7.5;
const M = 0.8; // поле

// ── палитра: «банкнотная зелень + таможенный сургуч» ────────────────────────
const DARK = "0F3B34"; // доминанта
const DARK_2 = "0A2A25";
const INK = "17211F";
const MUTED = "5E6D68";
const TINT = "F1F5F3";
const TINT_2 = "FBF4EF";
const ACCENT = "C8642B"; // акцент (крупный текст / плашки на белом)
const ACCENT_D = "A34E1E"; // акцент для мелкого текста на белом
const ACCENT_L = "E08A4E"; // акцент на тёмном фоне
const SAGE = "9FBDB3"; // вторичный текст на тёмном
const LINE = "D8E2DE";

const SERIF = "Cambria";
const SANS = "Calibri";

// ── помощники ───────────────────────────────────────────────────────────────
function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: DARK };
  return s;
}
function lightSlide() {
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };
  return s;
}

// круглый номер-«печать» — сквозной мотив всей колоды
function badge(slide, text, x, y, d, bg, fg, fs) {
  slide.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: bg }, line: { color: bg, width: 0 } });
  slide.addText(text, {
    x, y, w: d, h: d, margin: 0, align: "center", valign: "middle",
    fontFace: SANS, fontSize: fs || 14, bold: true, color: fg, isTextBox: true,
  });
}

function ring(slide, x, y, d, color, width) {
  slide.addShape(pres.ShapeType.ellipse, {
    x, y, w: d, h: d, fill: { color: DARK, transparency: 100 }, line: { color, width: width || 1.25 },
  });
}

function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: fill || TINT }, line: { color: fill || TINT, width: 0 },
  });
}

function kicker(slide, text, color) {
  slide.addText(text, {
    x: M, y: 0.52, w: W - 2 * M, h: 0.28, margin: 0,
    fontFace: SANS, fontSize: 11, bold: true, charSpacing: 2.2,
    color: color || ACCENT_D, isTextBox: true,
  });
}

function title(slide, text, color) {
  slide.addText(text, {
    x: M, y: 0.85, w: W - 2 * M, h: 0.85, margin: 0, valign: "top",
    fontFace: SERIF, fontSize: 32, bold: true, color: color || DARK, isTextBox: true,
  });
}

function lede(slide, text, color, y) {
  slide.addText(text, {
    x: M, y: y || 1.72, w: W - 2 * M - 0.6, h: 0.42, margin: 0,
    fontFace: SANS, fontSize: 14.5, color: color || MUTED, isTextBox: true,
  });
}

function body(slide, runs, opts) {
  slide.addText(runs, Object.assign({
    margin: 0, fontFace: SANS, fontSize: 13, color: INK, lineSpacing: 19, isTextBox: true,
  }, opts));
}

function bullets(slide, items, opts) {
  const runs = items.map((t, i) => ({
    text: t,
    options: { bullet: { code: "2013" }, breakLine: i !== items.length - 1, paraSpaceAfter: 7 },
  }));
  slide.addText(runs, Object.assign({
    margin: 0, fontFace: SANS, fontSize: 13, color: INK, lineSpacing: 18, isTextBox: true,
  }, opts));
}

function stat(slide, value, label, x, y, w, valueColor, labelColor, fs) {
  slide.addText(value, {
    x, y, w, h: 0.72, margin: 0, align: "left", valign: "middle",
    fontFace: SERIF, fontSize: fs || 34, bold: true, color: valueColor || ACCENT, isTextBox: true,
  });
  slide.addText(label, {
    x, y: y + 0.68, w, h: 0.62, margin: 0, valign: "top",
    fontFace: SANS, fontSize: 11.5, color: labelColor || MUTED, lineSpacing: 15, isTextBox: true,
  });
}

function hline(slide, x, y, w, color) {
  slide.addShape(pres.ShapeType.line, { x, y, w, h: 0, line: { color: color || LINE, width: 1 } });
}

function chip(slide, text, x, y, w, bg, fg) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h: 0.38, rectRadius: 0.19, fill: { color: bg }, line: { color: bg, width: 0 },
  });
  slide.addText(text, {
    x, y, w, h: 0.38, margin: 0, align: "center", valign: "middle",
    fontFace: SANS, fontSize: 11.5, bold: true, color: fg, isTextBox: true,
  });
}

// ─────────────────────────────────────────────────────────────── 1. Титул ──
{
  const s = darkSlide();
  ring(s, 9.35, -1.15, 5.2, "1C5A4F", 1.5);
  ring(s, 10.15, -0.35, 3.6, "27766A", 1.25);
  ring(s, 10.95, 0.45, 2.0, ACCENT_L, 1.5);
  s.addText("ТАМОЖНЯ · НДС · НАЛОГ У ИСТОЧНИКА", {
    x: M, y: 1.15, w: 8.2, h: 0.3, margin: 0,
    fontFace: SANS, fontSize: 11, bold: true, charSpacing: 2.4, color: SAGE, isTextBox: true,
  });

  s.addText("Налоговое законодательство\nпри трансграничной торговле", {
    x: M, y: 1.72, w: 9.4, h: 1.7, margin: 0, valign: "top",
    fontFace: SERIF, fontSize: 36, bold: true, color: "FFFFFF", lineSpacing: 44, isTextBox: true,
  });

  s.addText("Кто вправе облагать, где возникает объект налогообложения и что изменилось в 2023–2026 годах", {
    x: M, y: 3.52, w: 8.6, h: 0.8, margin: 0,
    fontFace: SANS, fontSize: 15.5, color: SAGE, lineSpacing: 22, isTextBox: true,
  });

  hline(s, M, 4.78, 4.2, "2A6A5E");
  s.addText("Доклад · магистратура, 2 курс · 10–12 минут", {
    x: M, y: 4.98, w: 7.0, h: 0.32, margin: 0,
    fontFace: SANS, fontSize: 12.5, color: SAGE, isTextBox: true,
  });
  s.addNotes(
    "Тема доклада — как налоговое право распределяет базу между странами, когда сделка пересекает границу. " +
    "Разберу четыре среза: косвенные налоги, прямые налоги, международные механизмы против размывания базы и российский контур 2023–2026 годов."
  );
}

// ──────────────────────────────────────────────────────── 2. Постановка ──
{
  const s = lightSlide();
  kicker(s, "ПОСТАНОВКА ПРОБЛЕМЫ");
  title(s, "Две суверенные юрисдикции в одной сделке");
  lede(s, "Каждая из них решает сама, что облагать. Обязанности считаться с соседом у неё нет — отсюда всего три возможных исхода.");

  const items = [
    ["01", "«Облагаем мы» — обе", "Двойное налогообложение", "Сделка теряет экономический смысл: одна и та же база облагается дважды."],
    ["02", "«Облагаем не мы» — обе", "Двойное необложение", "База не облагается нигде. На этом построена почти вся международная оптимизация."],
    ["03", "Правила согласованы", "Распределение базы", "Коллизионные нормы: СИДН, принцип назначения, правила о месте реализации."],
  ];
  const cw = 3.72, gap = 0.35;
  items.forEach(([n, head, verdict, text], i) => {
    const x = M + i * (cw + gap);
    card(s, x, 2.42, cw, 3.28, i === 2 ? TINT_2 : TINT);
    badge(s, n, x + 0.34, 2.78, 0.46, i === 2 ? ACCENT : DARK, "FFFFFF", 13);
    s.addText(head, {
      x: x + 0.34, y: 3.45, w: cw - 0.68, h: 0.34, margin: 0,
      fontFace: SANS, fontSize: 12, bold: true, color: MUTED, isTextBox: true,
    });
    s.addText(verdict, {
      x: x + 0.34, y: 3.8, w: cw - 0.68, h: 0.72, margin: 0, valign: "top",
      fontFace: SERIF, fontSize: 19, bold: true, color: i === 2 ? ACCENT_D : DARK, lineSpacing: 23, isTextBox: true,
    });
    body(s, text, { x: x + 0.34, y: 4.6, w: cw - 0.68, h: 1.0, fontSize: 12.5 });
  });

  s.addText("Право трансграничной торговли — это набор коллизионных правил, распределяющих налоговую базу между странами, плюс механизмы контроля за тем, чтобы их не обходили.", {
    x: M, y: 6.02, w: W - 2 * M, h: 0.5, margin: 0,
    fontFace: SANS, fontSize: 13, italic: true, color: DARK, isTextBox: true,
  });
  s.addNotes(
    "Внутренняя сделка облагается по правилам одной страны. Трансграничная сталкивает минимум две юрисдикции. " +
    "Два вопроса: кто вправе облагать и где возникает объект. Если оба государства отвечают «мы» — двойное налогообложение. " +
    "Если оба отвечают «не мы» — двойное необложение, и на нём выстроена почти вся оптимизация."
  );
}

// ───────────────────────────────────────────────────────── 3. План ──
{
  const s = lightSlide();
  kicker(s, "СТРУКТУРА ДОКЛАДА");
  title(s, "Четыре среза темы");

  const plan = [
    ["01", "Косвенные налоги", "Принцип страны назначения. Экспорт, импорт, ЕАЭС, цифровая торговля."],
    ["02", "Прямые налоги", "Постоянное представительство, налог у источника, трансфертное ценообразование."],
    ["03", "Международная повестка", "BEPS и MLI, глобальный минимальный налог Pillar Two, углеродный механизм CBAM."],
    ["04", "Российский контур", "Приостановление СИДН, новая договорная сеть, рост косвенной нагрузки."],
  ];
  plan.forEach(([n, head, text], i) => {
    const y = 2.2 + i * 1.16;
    badge(s, n, M, y, 0.5, i % 2 === 0 ? DARK : ACCENT, "FFFFFF", 13.5);
    s.addText(head, {
      x: M + 0.78, y: y - 0.03, w: 4.1, h: 0.4, margin: 0,
      fontFace: SERIF, fontSize: 20, bold: true, color: DARK, isTextBox: true,
    });
    body(s, text, { x: M + 4.95, y: y - 0.02, w: W - M - 4.95 - M, h: 0.62, fontSize: 13, color: MUTED });
    if (i < 3) hline(s, M, y + 0.86, W - 2 * M);
  });
  s.addNotes("Короткая навигация по докладу — четыре части, в каждой одна главная мысль.");
}

// ───────────────────────────────────── 4. Две системы привязки ──
{
  const s = lightSlide();
  kicker(s, "ФУНДАМЕНТ");
  title(s, "Две системы привязки к юрисдикции");
  lede(s, "Косвенные и прямые налоги отвечают на вопрос «где облагать» принципиально по-разному. Это ключ ко всей теме.");

  const cw = 5.79;
  // левая колонка
  card(s, M, 2.42, cw, 3.35, TINT);
  chip(s, "КОСВЕННЫЕ НАЛОГИ", M + 0.34, 2.72, 2.7, DARK, "FFFFFF");
  s.addText("Принцип страны назначения", {
    x: M + 0.34, y: 3.24, w: cw - 0.68, h: 0.45, margin: 0,
    fontFace: SERIF, fontSize: 21, bold: true, color: DARK, isTextBox: true,
  });
  bullets(s, [
    "Товар облагается там, где потребляется",
    "Экспорт — ставка 0% с сохранением вычета",
    "Импорт — по ставкам страны ввоза",
    "Принцип происхождения не применяется: он давал бы товарам из стран с низким НДС преимущество на чужом рынке",
  ], { x: M + 0.34, y: 3.82, w: cw - 0.68, h: 1.8 });

  // правая колонка
  const x2 = M + cw + 0.35;
  card(s, x2, 2.42, cw, 3.35, TINT_2);
  chip(s, "ПРЯМЫЕ НАЛОГИ", x2 + 0.34, 2.72, 2.4, ACCENT, "FFFFFF");
  s.addText("Резидентство + источник", {
    x: x2 + 0.34, y: 3.24, w: cw - 0.68, h: 0.45, margin: 0,
    fontFace: SERIF, fontSize: 21, bold: true, color: ACCENT_D, isTextBox: true,
  });
  bullets(s, [
    "Резидентство: облагается мировой доход резидента",
    "Источник: облагается доход, возникший на территории",
    "Принципы применяются одновременно и пересекаются",
    "Пересечение снимают СИДН — метод освобождения или метод зачёта",
  ], { x: x2 + 0.34, y: 3.82, w: cw - 0.68, h: 1.8 });

  s.addText("Косвенные налоги следуют за потреблением, прямые — за лицом и за источником дохода.", {
    x: M, y: 6.05, w: W - 2 * M, h: 0.4, margin: 0,
    fontFace: SANS, fontSize: 13, italic: true, color: DARK, isTextBox: true,
  });
  s.addNotes(
    "Косвенные налоги — принцип страны назначения: НДС это налог на потребление, а потребление у покупателя. " +
    "Прямые налоги — комбинация резидентства и источника; они применяются одновременно, поэтому неизбежно пересекаются, " +
    "и это пересечение устраняют соглашения об избежании двойного налогообложения."
  );
}

// ─────────────────────────────── 5. Экспорт / импорт ──
{
  const s = lightSlide();
  kicker(s, "КОСВЕННЫЕ НАЛОГИ · 1");
  title(s, "Экспорт и импорт: граница как точка перелома");

  // схема
  const yTop = 2.3;
  card(s, M, yTop, 4.6, 1.5, TINT);
  s.addText("СТРАНА ВЫВОЗА", { x: M + 0.3, y: yTop + 0.24, w: 4.0, h: 0.28, margin: 0, fontFace: SANS, fontSize: 10.5, bold: true, charSpacing: 1.6, color: MUTED, isTextBox: true });
  s.addText("Ставка 0% + вычет входного налога", { x: M + 0.3, y: yTop + 0.58, w: 4.0, h: 0.7, margin: 0, fontFace: SERIF, fontSize: 17, bold: true, color: DARK, lineSpacing: 21, isTextBox: true });

  s.addShape(pres.ShapeType.line, { x: 6.05, y: yTop - 0.18, w: 0, h: 1.86, line: { color: ACCENT, width: 1.5, dashType: "dash" } });
  s.addText("ГРАНИЦА", { x: 5.45, y: yTop + 1.72, w: 1.2, h: 0.26, margin: 0, align: "center", fontFace: SANS, fontSize: 10, bold: true, charSpacing: 1.4, color: ACCENT_D, isTextBox: true });
  s.addShape(pres.ShapeType.rightArrow, { x: 5.56, y: yTop + 0.62, w: 0.42, h: 0.26, fill: { color: DARK }, line: { color: DARK, width: 0 } });
  s.addShape(pres.ShapeType.rightArrow, { x: 6.55, y: yTop + 0.62, w: 0.55, h: 0.26, fill: { color: ACCENT }, line: { color: ACCENT, width: 0 } });

  card(s, 7.35, yTop, 5.18, 1.5, TINT_2);
  s.addText("СТРАНА ВВОЗА", { x: 7.65, y: yTop + 0.24, w: 4.6, h: 0.28, margin: 0, fontFace: SANS, fontSize: 10.5, bold: true, charSpacing: 1.6, color: MUTED, isTextBox: true });
  s.addText("НДС на таможне: таможенная стоимость + пошлина + акциз", { x: 7.65, y: yTop + 0.58, w: 4.6, h: 0.75, margin: 0, fontFace: SERIF, fontSize: 17, bold: true, color: ACCENT_D, lineSpacing: 21, isTextBox: true });

  // пояснения
  const items = [
    ["Не льгота, а принцип", "Страна вывоза полностью очищает товар от собственного налога — иначе он был бы обложен дважды.", "пп. 1 п. 1 ст. 164 НК РФ"],
    ["Всё решает подтверждение", "С 1 января 2024 года бумажный пакет заменён электронными реестрами; база определяется на конец квартала сбора документов.", "ст. 165 НК РФ"],
    ["Налог смыкается с таможней", "Таможенная стоимость считается по ТК ЕАЭС и Соглашению ВТО, поэтому спор о стоимости — это спор о налоге.", "ст. 151, 160 НК РФ"],
  ];
  const cw = 3.72, gap = 0.35;
  items.forEach(([head, text, ref], i) => {
    const x = M + i * (cw + gap);
    s.addText(head, { x, y: 4.32, w: cw, h: 0.32, margin: 0, fontFace: SANS, fontSize: 13.5, bold: true, color: DARK, isTextBox: true });
    body(s, text, { x, y: 4.68, w: cw, h: 1.15, fontSize: 12.5, color: MUTED });
    s.addText(ref, { x, y: 5.78, w: cw, h: 0.28, margin: 0, fontFace: SANS, fontSize: 10.5, bold: true, color: ACCENT_D, isTextBox: true });
  });

  card(s, M, 6.28, W - 2 * M, 0.66, DARK);
  s.addText([
    { text: "22%  ", options: { fontFace: SERIF, fontSize: 20, bold: true, color: ACCENT_L } },
    { text: "— основная ставка НДС с 1 января 2026 года (ФЗ от 28.11.2025 № 425-ФЗ). Нагрузка на импорт выросла напрямую.", options: { fontFace: SANS, fontSize: 13, color: "FFFFFF" } },
  ], { x: M + 0.34, y: 6.28, w: W - 2 * M - 0.68, h: 0.66, margin: 0, valign: "middle", isTextBox: true });

  s.addNotes(
    "Экспорт: ставка 0% с сохранением вычета — это не льгота, а элемент принципа назначения. Практически всё сводится к подтверждению по ст. 165. " +
    "Импорт: НДС на таможне, база — таможенная стоимость плюс пошлина плюс акциз. Спор о таможенной стоимости автоматически становится спором о налоге. " +
    "С 2026 года основная ставка 22 процента, это прямо увеличивает нагрузку на импорт."
  );
}

// ───────────────────────────────────────── 6. ЕАЭС ──
{
  const s = lightSlide();
  kicker(s, "КОСВЕННЫЕ НАЛОГИ · 2");
  title(s, "ЕАЭС: границы нет — механизм другой");
  lede(s, "Приложение № 18 к Договору о ЕАЭС. Таможня в цепочке не участвует, поэтому налог администрируют сами налоговые органы двух стран.");

  const steps = [
    ["01", "Экспортёр применяет 0%", "Страна А освобождает товар от своего НДС, как при обычном экспорте."],
    ["02", "Импортёр платит сам", "Страна Б: покупатель исчисляет НДС и платит его в свой налоговый орган до 20-го числа следующего месяца."],
    ["03", "Заявление возвращается", "Заявление о ввозе с отметкой налогового органа уходит экспортёру — это его единственное доказательство нулевой ставки."],
  ];
  const cw = 3.72, gap = 0.35;
  steps.forEach(([n, head, text], i) => {
    const x = M + i * (cw + gap);
    card(s, x, 2.48, cw, 2.92, TINT);
    badge(s, n, x + 0.34, 2.82, 0.46, DARK, "FFFFFF", 13);
    s.addText(head, { x: x + 0.34, y: 3.42, w: cw - 0.68, h: 0.76, margin: 0, valign: "top", fontFace: SERIF, fontSize: 17, bold: true, color: DARK, lineSpacing: 21, isTextBox: true });
    body(s, text, { x: x + 0.34, y: 4.22, w: cw - 0.68, h: 1.05, fontSize: 12.5, color: MUTED });
    if (i < 2) {
      s.addShape(pres.ShapeType.rightArrow, { x: x + cw + 0.06, y: 3.68, w: 0.23, h: 0.22, fill: { color: ACCENT }, line: { color: ACCENT, width: 0 } });
    }
  });

  card(s, M, 5.68, W - 2 * M, 1.28, TINT_2);
  badge(s, "!", M + 0.36, 5.96, 0.44, ACCENT, "FFFFFF", 15);
  s.addText("Уязвимость конструкции", { x: M + 1.02, y: 5.92, w: 10.6, h: 0.32, margin: 0, fontFace: SANS, fontSize: 13.5, bold: true, color: ACCENT_D, isTextBox: true });
  body(s, "Право экспортёра на нулевую ставку обеспечивается административным действием органа другой страны: нет отметки на заявлении — нет и подтверждения, хотя товар вывезен и налог покупателем уплачен.", {
    x: M + 1.02, y: 6.26, w: 10.6, h: 0.6, fontSize: 13, color: INK,
  });

  s.addNotes(
    "Внутри Союза таможенных границ нет. Экспортёр применяет ноль, импортёр сам исчисляет и платит НДС в свой налоговый орган до 20-го числа. " +
    "Заявление о ввозе с отметкой налогового органа — единственное доказательство нулевой ставки для экспортёра. " +
    "То есть обязательство одной стороны обеспечивается административным действием органа другой страны, и это уязвимость конструкции."
  );
}

// ─────────────────────────── 7. Цифровая торговля (тёмный) ──
{
  const s = darkSlide();
  ring(s, 11.4, -1.0, 4.4, "1C5A4F", 1.25);
  kicker(s, "КОСВЕННЫЕ НАЛОГИ · 3", SAGE);
  title(s, "Цифровая торговля сломала обе предпосылки", "FFFFFF");

  card(s, M, 2.15, 4.5, 3.05, DARK_2);
  s.addText("Классические правила рассчитаны на товар, который пересекает границу и предъявляется таможне", {
    x: M + 0.34, y: 2.45, w: 3.82, h: 0.95, margin: 0,
    fontFace: SANS, fontSize: 13, color: SAGE, lineSpacing: 18, isTextBox: true,
  });
  s.addText([
    { text: "Услуга", options: { fontFace: SERIF, fontSize: 16, bold: true, color: "FFFFFF" } },
    { text: " границу не пересекает вовсе", options: { fontFace: SANS, fontSize: 13, color: "FFFFFF", breakLine: true } },
    { text: "Товар", options: { fontFace: SERIF, fontSize: 16, bold: true, color: "FFFFFF" } },
    { text: " идёт миллионами мелких посылок, которые нельзя администрировать поштучно", options: { fontFace: SANS, fontSize: 13, color: "FFFFFF" } },
  ], { x: M + 0.34, y: 3.5, w: 3.82, h: 1.5, margin: 0, lineSpacing: 19, isTextBox: true });

  const sols = [
    ["01", "Место реализации — страна покупателя", "Иностранный поставщик встаёт на учёт в налоговом органе страны потребления.", "ст. 174.2 НК РФ, с 2017 · B2B через налогового агента с октября 2022"],
    ["02", "Обязанность переносится на платформу", "Не тысячи продавцов, а один маркетплейс: он и считает, и платит налог.", "ст. 174.3 НК РФ с 01.07.2024 (ФЗ № 100-ФЗ) · режим OSS/IOSS в ЕС с 01.07.2021"],
    ["03", "Пересмотр беспошлинных порогов", "Мелкая посылка перестаёт быть беспошлинной по умолчанию.", "Решение Совета ЕЭК от 05.12.2025 № 112 · в ЕС отменено освобождение до 22 евро"],
  ];
  const x0 = M + 4.85, cw = W - M - x0;
  sols.forEach(([n, head, text, ref], i) => {
    const y = 2.15 + i * 1.08;
    badge(s, n, x0, y + 0.04, 0.44, ACCENT_L, DARK, 12.5);
    s.addText(head, { x: x0 + 0.66, y, w: cw - 0.66, h: 0.3, margin: 0, fontFace: SERIF, fontSize: 17, bold: true, color: "FFFFFF", isTextBox: true });
    s.addText(text, { x: x0 + 0.66, y: y + 0.32, w: cw - 0.66, h: 0.28, margin: 0, fontFace: SANS, fontSize: 12.5, color: SAGE, isTextBox: true });
    s.addText(ref, { x: x0 + 0.66, y: y + 0.6, w: cw - 0.66, h: 0.28, margin: 0, fontFace: SANS, fontSize: 11, bold: true, color: ACCENT_L, isTextBox: true });
  });

  hline(s, M, 5.62, W - 2 * M, "2A6A5E");
  s.addText("Администрирование уходит с границы и с покупателя — на посредника. Фискальная привязка уходит к стране потребления.", {
    x: M, y: 5.82, w: W - 2 * M, h: 0.4, margin: 0,
    fontFace: SANS, fontSize: 13.5, italic: true, color: "FFFFFF", isTextBox: true,
  });

  s.addNotes(
    "Электронная торговля разрушила обе предпосылки классических правил: услуга границу не пересекает, а товар приходит миллионами мелких посылок. " +
    "Ответ — три решения, воспроизведённые почти всеми юрисдикциями: место реализации переносится в страну покупателя; обязанность возлагается на платформу; пересматриваются беспошлинные пороги."
  );
}

// ──────────────────────────── 8. Пороги ЕАЭС с 2026 ──
{
  const s = lightSlide();
  kicker(s, "КОСВЕННЫЕ НАЛОГИ · 4");
  title(s, "Новый режим посылок в ЕАЭС с 2026 года");
  lede(s, "Решение Совета ЕЭК от 05.12.2025 № 112. Товары электронной торговли выделены в отдельную категорию со своим порядком обложения.");

  const stats = [
    ["200 €", "Порог беспошлинного ввоза для физического лица", DARK],
    ["5%", "Пошлина со стоимости сверх порога", ACCENT],
    ["1 €/кг", "Минимальная пошлина — не даёт занижать стоимость", DARK],
    ["01.07.2026", "Дата вступления нового порядка в силу", ACCENT],
  ];
  const cw = 2.7, gap = 0.31;
  stats.forEach(([v, l, c], i) => {
    const x = M + i * (cw + gap);
    card(s, x, 2.5, cw, 1.86, i % 2 === 0 ? TINT : TINT_2);
    s.addText(v, { x: x + 0.3, y: 2.74, w: cw - 0.6, h: 0.66, margin: 0, valign: "middle", fontFace: SERIF, fontSize: i === 3 ? 24 : 32, bold: true, color: c, isTextBox: true });
    body(s, l, { x: x + 0.3, y: 3.44, w: cw - 0.6, h: 0.75, fontSize: 12, color: MUTED });
  });

  s.addText("Что это меняет на практике", {
    x: M, y: 4.72, w: 6.0, h: 0.34, margin: 0, fontFace: SERIF, fontSize: 20, bold: true, color: DARK, isTextBox: true,
  });
  bullets(s, [
    "Трансграничная розница перестаёт быть налогово привилегированной по сравнению с внутренней",
    "НДС при этом взимается отдельно и по национальным ставкам — пошлина его не заменяет",
    "Расчёт и уплату несёт оператор электронной торговли, а не миллионы покупателей",
  ], { x: M, y: 5.2, w: W - 2 * M, h: 1.4, fontSize: 13.5 });

  s.addNotes(
    "С 1 июля 2026 года порог беспошлинного ввоза товаров электронной торговли для физических лиц в ЕАЭС — 200 евро, " +
    "сверх него пошлина 5 процентов от стоимости, но не менее 1 евро за килограмм. " +
    "Минимальная ставка за килограмм закрывает схему с занижением заявленной стоимости посылки."
  );
}

// ───────────────────── 9. Постоянное представительство ──
{
  const s = lightSlide();
  kicker(s, "ПРЯМЫЕ НАЛОГИ · 1");
  title(s, "Постоянное представительство");
  lede(s, "Ст. 5 Модельной конвенции ОЭСР, ст. 306–308 НК РФ. Государство источника облагает прибыль иностранной компании только при её присутствии.");

  const cw = 5.79;
  card(s, M, 2.42, cw, 2.55, TINT);
  chip(s, "ОБРАЗУЕТ ПП", M + 0.34, 2.72, 2.05, DARK, "FFFFFF");
  bullets(s, [
    "Постоянное место деятельности: филиал, бюро, стройплощадка",
    "Зависимый агент, регулярно заключающий контракты",
    "Регулярная предпринимательская деятельность на территории",
  ], { x: M + 0.34, y: 3.26, w: cw - 0.68, h: 1.5, fontSize: 13 });

  const x2 = M + cw + 0.35;
  card(s, x2, 2.42, cw, 2.55, TINT_2);
  chip(s, "НЕ ОБРАЗУЕТ ПП", x2 + 0.34, 2.72, 2.35, ACCENT, "FFFFFF");
  bullets(s, [
    "Сама по себе поставка товаров в страну покупателя",
    "Подготовительная и вспомогательная деятельность",
    "Хранение, демонстрация, сбор информации",
  ], { x: x2 + 0.34, y: 3.26, w: cw - 0.68, h: 1.5, fontSize: 13 });

  card(s, M, 5.2, W - 2 * M, 1.42, DARK);
  s.addText("Практический смысл и предел нормы", {
    x: M + 0.36, y: 5.42, w: 10.9, h: 0.3, margin: 0, fontFace: SANS, fontSize: 12, bold: true, charSpacing: 1.4, color: ACCENT_L, isTextBox: true,
  });
  s.addText("Экспортёр платит налог на прибыль дома, а не в стране покупателя. Но цифровая экономика позволяет извлекать значительную выручку в стране вообще без присутствия в ней — и физическая привязка перестаёт работать. Это предмет Pillar One.", {
    x: M + 0.36, y: 5.74, w: W - 2 * M - 0.72, h: 0.7, margin: 0,
    fontFace: SANS, fontSize: 13.5, color: "FFFFFF", lineSpacing: 19, isTextBox: true,
  });

  s.addNotes(
    "Постоянное представительство — центральная категория прямого налогообложения. Государство источника вправе облагать прибыль иностранной компании " +
    "только при наличии постоянного места деятельности либо зависимого агента. Поставка товаров сама по себе представительства не образует. " +
    "Но цифровая экономика позволяет зарабатывать в стране без всякого присутствия — физическая привязка перестаёт работать."
  );
}

// ─────────────────── 10. Налог у источника и СИДН ──
{
  const s = lightSlide();
  kicker(s, "ПРЯМЫЕ НАЛОГИ · 2");
  title(s, "Налог у источника: удержание, соглашение, фильтр");

  // цепочка
  const yc = 2.32;
  card(s, M, yc, 3.3, 1.24, TINT);
  s.addText("Российский плательщик", { x: M + 0.26, y: yc + 0.22, w: 2.8, h: 0.32, margin: 0, fontFace: SERIF, fontSize: 15.5, bold: true, color: DARK, isTextBox: true });
  s.addText("налоговый агент, ст. 310 НК РФ", { x: M + 0.26, y: yc + 0.62, w: 2.8, h: 0.3, margin: 0, fontFace: SANS, fontSize: 11.5, color: MUTED, isTextBox: true });

  s.addShape(pres.ShapeType.rightArrow, { x: 4.28, y: yc + 0.5, w: 0.5, h: 0.24, fill: { color: DARK }, line: { color: DARK, width: 0 } });

  card(s, 4.95, yc, 3.44, 1.24, TINT_2);
  s.addText("Фактическое право на доход", { x: 5.21, y: yc + 0.2, w: 2.95, h: 0.36, margin: 0, fontFace: SERIF, fontSize: 15.5, bold: true, color: ACCENT_D, isTextBox: true });
  s.addText("ст. 7 НК РФ — фильтр против транзитных компаний", { x: 5.21, y: yc + 0.6, w: 2.95, h: 0.45, margin: 0, fontFace: SANS, fontSize: 11.5, color: MUTED, lineSpacing: 14, isTextBox: true });

  s.addShape(pres.ShapeType.rightArrow, { x: 8.55, y: yc + 0.5, w: 0.5, h: 0.24, fill: { color: ACCENT }, line: { color: ACCENT, width: 0 } });

  card(s, 9.22, yc, 3.31, 1.24, TINT);
  s.addText("Иностранный получатель", { x: 9.48, y: yc + 0.22, w: 2.8, h: 0.32, margin: 0, fontFace: SERIF, fontSize: 15.5, bold: true, color: DARK, isTextBox: true });
  s.addText("дивиденды, проценты, роялти", { x: 9.48, y: yc + 0.62, w: 2.8, h: 0.3, margin: 0, fontFace: SANS, fontSize: 11.5, color: MUTED, isTextBox: true });

  hline(s, M, 4.06, W - 2 * M);

  s.addText("Ставки без соглашения (НК РФ)", { x: M, y: 4.28, w: 5.6, h: 0.32, margin: 0, fontFace: SANS, fontSize: 12, bold: true, charSpacing: 1.3, color: MUTED, isTextBox: true });
  stat(s, "15%", "дивиденды", M, 4.66, 1.7, DARK);
  stat(s, "25%", "проценты и роялти", M + 1.9, 4.66, 2.4, DARK);

  s.addText("Что даёт и чего требует соглашение", { x: 7.1, y: 4.28, w: 5.4, h: 0.32, margin: 0, fontFace: SANS, fontSize: 12, bold: true, charSpacing: 1.3, color: MUTED, isTextBox: true });
  bullets(s, [
    "СИДН понижает ставку у источника — вплоть до нуля по процентам",
    "Льгота не даётся кондуитной компании, встроенной ради доступа к соглашению",
    "Подтверждение резидентства и фактического права на доход — до выплаты",
  ], { x: 7.1, y: 4.66, w: 5.43, h: 1.6, fontSize: 12.5 });

  card(s, M, 6.42, 5.5, 0.62, TINT_2);
  s.addText("Ставка — вопрос второй. Первый вопрос всегда: кому реально принадлежит доход.", {
    x: M + 0.28, y: 6.42, w: 5.0, h: 0.62, margin: 0, valign: "middle",
    fontFace: SANS, fontSize: 12.5, italic: true, color: ACCENT_D, isTextBox: true,
  });

  s.addNotes(
    "Пассивные доходы — дивиденды, проценты, роялти — облагаются в стране выплаты удержанием налоговым агентом по ст. 309 и 310. " +
    "Соглашения понижают ставки, но применение пониженной ставки обусловлено концепцией фактического права на доход по ст. 7: " +
    "льгота не предоставляется транзитной компании, встроенной в структуру только ради доступа к соглашению."
  );
}

// ───────────────── 11. Трансфертное ценообразование ──
{
  const s = lightSlide();
  kicker(s, "ПРЯМЫЕ НАЛОГИ · 3");
  title(s, "Трансфертное ценообразование");
  lede(s, "Раздел V.1 НК РФ. Если продавец и покупатель — одна группа, цена сделки перестаёт быть рыночным фактом и становится инструментом распределения прибыли.");

  const cols = [
    ["Механика размывания", [
      "Экспорт своей же торговой компании по заниженной цене",
      "Импорт от своей же структуры по завышенной цене",
      "Роялти и внутригрупповые услуги как канал вывода прибыли",
    ], TINT, DARK],
    ["Ответ правопорядка", [
      "Принцип «вытянутой руки»: цена сопоставляется с рыночной",
      "Разница доначисляется по правилам раздела V.1 НК РФ",
      "Документация по контролируемым сделкам и уведомления",
    ], TINT_2, ACCENT_D],
  ];
  const cw = 5.79;
  cols.forEach(([head, list, bg, hc], i) => {
    const x = M + i * (cw + 0.35);
    card(s, x, 2.62, cw, 2.35, bg);
    s.addText(head, { x: x + 0.34, y: 2.88, w: cw - 0.68, h: 0.36, margin: 0, fontFace: SERIF, fontSize: 19, bold: true, color: hc, isTextBox: true });
    bullets(s, list, { x: x + 0.34, y: 3.32, w: cw - 0.68, h: 1.45, fontSize: 12.5 });
  });

  s.addText("Ужесточение с 2024 года — ФЗ от 27.11.2023 № 539-ФЗ", {
    x: M, y: 5.22, w: 8.0, h: 0.34, margin: 0, fontFace: SANS, fontSize: 12, bold: true, charSpacing: 1.3, color: MUTED, isTextBox: true,
  });
  card(s, M, 5.6, 5.9, 1.3, DARK);
  s.addText([
    { text: "= дивиденды", options: { fontFace: SERIF, fontSize: 22, bold: true, color: ACCENT_L, breakLine: true } },
    { text: "Доход, скрытый в нерыночной цене, приравнивается к дивидендам и облагается налогом у источника", options: { fontFace: SANS, fontSize: 12.5, color: "FFFFFF" } },
  ], { x: M + 0.34, y: 5.72, w: 5.22, h: 1.06, margin: 0, lineSpacing: 17, isTextBox: true });

  card(s, M + 6.25, 5.6, 5.5, 1.3, DARK);
  s.addText([
    { text: "100%", options: { fontFace: SERIF, fontSize: 22, bold: true, color: ACCENT_L, breakLine: true } },
    { text: "Штраф от неуплаченной суммы вместо прежних 40% — цена ошибки в ценообразовании удвоилась", options: { fontFace: SANS, fontSize: 12.5, color: "FFFFFF" } },
  ], { x: M + 6.59, y: 5.72, w: 4.82, h: 1.06, margin: 0, lineSpacing: 17, isTextBox: true });

  s.addNotes(
    "Внутри группы цену назначает сама группа, и через цену прибыль перемещается в низконалоговую юрисдикцию. " +
    "Ответ — принцип вытянутой руки: цена сопоставляется с рыночной, разница доначисляется. " +
    "С 2024 года режим ужесточён: скрытый в цене доход приравнивается к дивидендам и облагается налогом у источника, штраф повышен до 100 процентов."
  );
}

// ────────────────── 12. BEPS → MLI → Pillar Two (тёмный) ──
{
  const s = darkSlide();
  ring(s, -1.6, 4.3, 4.6, "1C5A4F", 1.25);
  kicker(s, "МЕЖДУНАРОДНАЯ ПОВЕСТКА · 1", SAGE);
  title(s, "От BEPS к глобальному минимальному налогу", "FFFFFF");
  lede(s, "Международная реакция на разрыв между местом создания стоимости и местом уплаты налога — три этапа за десять лет.", SAGE);

  // таймлайн
  const ty = 2.75;
  hline(s, M + 0.15, ty, W - 2 * M - 0.3, "2A6A5E");
  const points = [
    ["2015", "План BEPS", "15 действий ОЭСР и G20 против разрыва между местом создания стоимости и местом уплаты налога"],
    ["2021", "MLI в России", "Многосторонняя конвенция меняет сотни двусторонних СИДН одним актом. Тест основной цели (PPT)"],
    ["2024+", "Pillar Two", "Глобальный минимальный налог действует в ЕС, Великобритании, Японии, Корее, Канаде, Австралии"],
  ];
  const cw = 3.72, gap = 0.35;
  points.forEach(([year, head, text], i) => {
    const x = M + i * (cw + gap);
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.15, y: ty - 0.09, w: 0.18, h: 0.18, fill: { color: ACCENT_L }, line: { color: ACCENT_L, width: 0 } });
    s.addText(year, { x, y: ty + 0.2, w: cw, h: 0.4, margin: 0, fontFace: SERIF, fontSize: 26, bold: true, color: ACCENT_L, isTextBox: true });
    s.addText(head, { x, y: ty + 0.68, w: cw, h: 0.3, margin: 0, fontFace: SERIF, fontSize: 17, bold: true, color: "FFFFFF", isTextBox: true });
    s.addText(text, { x, y: ty + 1.02, w: cw - 0.15, h: 1.0, margin: 0, fontFace: SANS, fontSize: 12.5, color: SAGE, lineSpacing: 17, isTextBox: true });
  });

  card(s, M, 5.18, W - 2 * M, 1.5, DARK_2);
  const st = [["15%", "минимальная эффективная ставка"], ["750 млн €", "порог выручки группы"], ["60+", "юрисдикций уже внедрили"]];
  st.forEach(([v, l], i) => {
    const x = M + 0.4 + i * 2.55;
    s.addText(v, { x, y: 5.36, w: 2.4, h: 0.44, margin: 0, fontFace: SERIF, fontSize: 24, bold: true, color: ACCENT_L, isTextBox: true });
    s.addText(l, { x, y: 5.82, w: 2.4, h: 0.55, margin: 0, fontFace: SANS, fontSize: 11.5, color: SAGE, lineSpacing: 15, isTextBox: true });
  });
  s.addText("Недобранное одной страной доберёт другая — через QDMTT или правило включения дохода. Налоговая льгота перестаёт быть конкурентным преимуществом юрисдикции.", {
    x: M + 8.2, y: 5.36, w: W - 2 * M - 8.6, h: 1.1, margin: 0,
    fontFace: SANS, fontSize: 12.5, color: "FFFFFF", lineSpacing: 17, isTextBox: true,
  });

  s.addNotes(
    "План BEPS 2015 года — ответ на разрыв между местом создания стоимости и местом уплаты налога. Инструмент быстрого внедрения — конвенция MLI, " +
    "Россия применяет её с 2021 года; ключевая новелла — тест основной цели. " +
    "Pillar Two: глобальный минимальный налог 15 процентов для групп с выручкой свыше 750 миллионов евро. " +
    "Россия правила не внедряла, но российские группы с иностранными дочерними компаниями попадают под них извне."
  );
}

// ───────────────────────────────────── 13. CBAM ──
{
  const s = lightSlide();
  kicker(s, "МЕЖДУНАРОДНАЯ ПОВЕСТКА · 2");
  title(s, "CBAM: не налог по форме, налог по существу");
  lede(s, "Регламент (ЕС) 2023/956. Импортёр в ЕС оплачивает углеродный след ввезённого товара по цене квот европейской системы торговли выбросами.");

  card(s, M, 2.5, 5.79, 2.2, TINT);
  badge(s, "1", M + 0.34, 2.8, 0.44, MUTED, "FFFFFF", 13);
  s.addText("Октябрь 2023 — декабрь 2025", { x: M + 0.98, y: 2.82, w: 4.6, h: 0.32, margin: 0, fontFace: SERIF, fontSize: 17, bold: true, color: DARK, isTextBox: true });
  s.addText("Переходный период", { x: M + 0.98, y: 3.16, w: 4.6, h: 0.28, margin: 0, fontFace: SANS, fontSize: 12, bold: true, color: MUTED, isTextBox: true });
  body(s, "Только отчётность о выбросах. Платежей нет — ЕС собирает данные и приучает импортёров к учёту углеродного следа.", { x: M + 0.34, y: 3.62, w: 5.11, h: 0.85, fontSize: 12.5, color: MUTED });

  const x2 = M + 5.79 + 0.35;
  card(s, x2, 2.5, 5.79, 2.2, TINT_2);
  badge(s, "2", x2 + 0.34, 2.8, 0.44, ACCENT, "FFFFFF", 13);
  s.addText("С 1 января 2026 года", { x: x2 + 0.98, y: 2.82, w: 4.6, h: 0.32, margin: 0, fontFace: SERIF, fontSize: 17, bold: true, color: ACCENT_D, isTextBox: true });
  s.addText("Финансовая фаза", { x: x2 + 0.98, y: 3.16, w: 4.6, h: 0.28, margin: 0, fontFace: SANS, fontSize: 12, bold: true, color: MUTED, isTextBox: true });
  body(s, "Импортёр обязан покупать CBAM-сертификаты. Механизм из отчётного превращается в фискальный по последствиям.", { x: x2 + 0.34, y: 3.62, w: 5.11, h: 0.85, fontSize: 12.5, color: MUTED });

  s.addText("Охваченные товары", { x: M, y: 4.96, w: 5.0, h: 0.3, margin: 0, fontFace: SANS, fontSize: 12, bold: true, charSpacing: 1.3, color: MUTED, isTextBox: true });
  const goods = ["Цемент", "Чёрные металлы", "Алюминий", "Удобрения", "Электроэнергия", "Водород"];
  goods.forEach((g, i) => chip(s, g, M + i * 2.02, 5.34, 1.88, i % 2 === 0 ? DARK : ACCENT, "FFFFFF"));

  card(s, M, 6.0, W - 2 * M, 0.92, TINT);
  s.addText("Значение для темы: инструмент, не являющийся налогом по форме, влияет на трансграничную торговлю сильнее многих налогов — и обходит как правила ВТО о пошлинах, так и налоговые соглашения.", {
    x: M + 0.34, y: 6.0, w: W - 2 * M - 0.68, h: 0.92, margin: 0, valign: "middle",
    fontFace: SANS, fontSize: 13, italic: true, color: DARK, lineSpacing: 18, isTextBox: true,
  });

  s.addNotes(
    "CBAM формально не налог, но экономически — платёж при импорте цемента, чёрных металлов, алюминия, удобрений, электроэнергии и водорода. " +
    "Переходный период с одной отчётностью шёл с октября 2023 года, финансовая фаза началась 1 января 2026 года. " +
    "Это важный прецедент: не-налоговый по форме инструмент влияет на торговлю сильнее многих налогов."
  );
}

// ───────────────────────── 14. Российский контур ──
{
  const s = lightSlide();
  kicker(s, "РОССИЙСКИЙ КОНТУР");
  title(s, "Что определяет картину в 2023–2026 годах");

  const blocks = [
    ["01", "Приостановление соглашений", [
      "Указ Президента от 08.08.2023 № 585 и ФЗ от 19.12.2023 № 598-ФЗ",
      "Приостановлены отдельные положения СИДН с 38 государствами",
      "Применяются национальные ставки: 15% по дивидендам, 25% по процентам и роялти",
      "Вторая сторона тоже перестаёт устранять двойное налогообложение — проблема стала практической",
    ], DARK],
    ["02", "Переориентация договорной сети", [
      "Соглашения заключаются с новыми партнёрами",
      "СИДН с ОАЭ подписано 17 февраля 2025 года, применяется с 1 января 2026 года",
      "Единая ставка 10% по дивидендам, процентам и роялти",
      "ОАЭ исключены из перечня офшорных юрисдикций",
    ], ACCENT],
    ["03", "Рост косвенной нагрузки", [
      "Основная ставка НДС — 22% с 1 января 2026 года",
      "Новые правила ЕАЭС по электронной торговле с 1 июля 2026 года",
      "Обязанности всё чаще возлагаются на платформу и налогового агента",
    ], DARK],
  ];
  const cw = 3.72, gap = 0.35;
  blocks.forEach(([n, head, list, c], i) => {
    const x = M + i * (cw + gap);
    card(s, x, 2.1, cw, 4.55, i === 1 ? TINT_2 : TINT);
    badge(s, n, x + 0.34, 2.42, 0.46, c, "FFFFFF", 13);
    s.addText(head, { x: x + 0.34, y: 3.06, w: cw - 0.68, h: 0.75, margin: 0, valign: "top", fontFace: SERIF, fontSize: 18, bold: true, color: i === 1 ? ACCENT_D : DARK, lineSpacing: 22, isTextBox: true });
    bullets(s, list, { x: x + 0.34, y: 3.9, w: cw - 0.68, h: 2.5, fontSize: 12 });
  });

  s.addNotes(
    "Три процесса. Первый — приостановление отдельных положений соглашений с 38 государствами: льготные ставки не применяются, действуют национальные. " +
    "Второй — переориентация договорной сети, самое значимое соглашение — с ОАЭ, ставка 10 процентов по всем трём видам пассивного дохода. " +
    "Третий — рост косвенной нагрузки: НДС 22 процента и новые правила ЕАЭС по электронной торговле."
  );
}

// ────────────────────────────── 15. Выводы (тёмный) ──
{
  const s = darkSlide();
  ring(s, 11.0, 4.5, 4.2, "1C5A4F", 1.25);
  kicker(s, "ВЫВОДЫ", SAGE);
  title(s, "Четыре тезиса", "FFFFFF");

  const outs = [
    ["01", "Единого права трансграничной торговли не существует", "Есть национальные нормы и сеть из более чем трёх тысяч двусторонних соглашений. Устойчивость держится на их согласованности — и опыт приостановления показал, насколько она хрупка."],
    ["02", "Привязка смещается к рынку сбыта", "Принцип страны назначения, изначально принадлежавший косвенному налогообложению, распространяется и на прямое."],
    ["03", "Обязанным лицом становится посредник", "Маркетплейс, платформа, банк — вместо самого налогоплательщика. Собираемость растёт, издержки администрирования переходят на бизнес."],
    ["04", "Главный риск — не ставка, а доказывание", "Подтверждение нулевой ставки, фактического права на доход, рыночности цены, углеродного следа."],
  ];
  outs.forEach(([n, head, text], i) => {
    const y = 2.05 + i * 1.16;
    badge(s, n, M, y + 0.02, 0.46, i % 2 === 0 ? ACCENT_L : "2A6A5E", i % 2 === 0 ? DARK : "FFFFFF", 13);
    s.addText(head, { x: M + 0.72, y: y - 0.02, w: 5.1, h: 0.75, margin: 0, valign: "top", fontFace: SERIF, fontSize: 17.5, bold: true, color: "FFFFFF", lineSpacing: 21, isTextBox: true });
    s.addText(text, { x: M + 6.05, y, w: W - M - (M + 6.05), h: 0.9, margin: 0, fontFace: SANS, fontSize: 12.5, color: SAGE, lineSpacing: 17, isTextBox: true });
    if (i < 3) hline(s, M, y + 0.98, W - 2 * M, "1C5A4F");
  });

  s.addNotes("Четыре вывода. Последний — практический: экономика трансграничной сделки определяется не тем, сколько нужно заплатить, а тем, что удастся доказать.");
}

// ───────────────────────────────── 16. Финал ──
{
  const s = darkSlide();
  ring(s, 9.6, -0.9, 5.0, "1C5A4F", 1.5);
  ring(s, 10.4, -0.1, 3.4, ACCENT_L, 1.25);

  s.addText("«Экономика трансграничной сделки\nопределяется не тем, сколько нужно\nзаплатить, а тем, что удастся доказать»", {
    x: M, y: 2.0, w: 8.4, h: 2.4, margin: 0,
    fontFace: SERIF, fontSize: 27, bold: true, color: "FFFFFF", lineSpacing: 40, isTextBox: true,
  });
  hline(s, M, 4.75, 3.6, "2A6A5E");
  s.addText("Спасибо за внимание. Готов ответить на вопросы.", {
    x: M, y: 4.98, w: 8.0, h: 0.4, margin: 0,
    fontFace: SANS, fontSize: 15, color: SAGE, isTextBox: true,
  });
  s.addText("Нормативная база: НК РФ · Договор о ЕАЭС, Приложение № 18 · Решение Совета ЕЭК № 112 · Модельная конвенция ОЭСР · MLI · GloBE · Регламент (ЕС) 2023/956", {
    x: M, y: 6.35, w: W - 2 * M, h: 0.6, margin: 0,
    fontFace: SANS, fontSize: 11, color: "6F9188", lineSpacing: 15, isTextBox: true,
  });
  s.addNotes("Финальный слайд — ключевая мысль доклада и переход к вопросам.");
}

pres.writeFile({ fileName: "prezentaciya.pptx" }).then(() => console.log("ok: prezentaciya.pptx"));

// Сборка doklad.docx из doklad.md — оформление по стандарту учебной работы:
// Times New Roman 14 пт, полуторный интервал, выравнивание по ширине, абзацный отступ 1,25 см.
// Запуск: node build-doklad-docx.js
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel, LevelFormat, convertMillimetersToTwip,
} = require("docx");

const FONT = "Times New Roman";
const SIZE = 28;        // 14 пт
const LINE = 360;       // полуторный интервал
const INDENT = 709;     // 1,25 см

const src = fs.readFileSync("doklad.md", "utf8").split("\n");

// разбор **жирного** внутри строки
function runs(text, extra = {}) {
  const out = [];
  text.split(/(\*\*[^*]+\*\*)/g).forEach((part) => {
    if (!part) return;
    const b = part.startsWith("**") && part.endsWith("**");
    out.push(new TextRun(Object.assign({
      text: b ? part.slice(2, -2) : part,
      font: FONT, size: SIZE, bold: b || undefined,
    }, extra)));
  });
  return out;
}

const children = [];
let buf = [];         // накопитель строк одного абзаца
let mode = "text";    // text | bullet

function flush() {
  if (!buf.length) return;
  const text = buf.join(" ").replace(/\s+/g, " ").trim();
  buf = [];
  if (!text) return;

  if (mode === "bullet") {
    children.push(new Paragraph({
      children: runs(text),
      numbering: { reference: "dash", level: 0 },
      alignment: AlignmentType.JUSTIFIED,
      spacing: { line: LINE, after: 0 },
    }));
    return;
  }

  // курсивная строка целиком: *…*
  const it = /^\*([^*].*)\*$/.exec(text);
  if (it) {
    children.push(new Paragraph({
      children: runs(it[1], { italics: true }),
      alignment: AlignmentType.CENTER,
      spacing: { line: LINE, after: 240 },
    }));
    return;
  }

  children.push(new Paragraph({
    children: runs(text),
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: INDENT },
    spacing: { line: LINE, after: 0 },
  }));
}

for (const raw of src) {
  const line = raw.replace(/\s+$/, "");

  if (/^\s*---\s*$/.test(line)) { flush(); mode = "text"; continue; }

  if (line.startsWith("# ")) {
    flush(); mode = "text";
    children.push(new Paragraph({
      children: runs(line.slice(2), { bold: true, size: 32 }),
      alignment: AlignmentType.CENTER,
      spacing: { line: LINE, after: 240 },
    }));
    continue;
  }

  if (line.startsWith("### ") || line.startsWith("## ")) {
    flush(); mode = "text";
    const t = line.replace(/^#+\s/, "");
    children.push(new Paragraph({
      children: runs(t, { bold: true }),
      heading: line.startsWith("## ") ? HeadingLevel.HEADING_1 : HeadingLevel.HEADING_2,
      alignment: AlignmentType.LEFT,
      spacing: { line: LINE, before: 280, after: 120 },
    }));
    continue;
  }

  if (/^- /.test(line)) { flush(); mode = "bullet"; buf.push(line.slice(2)); continue; }

  if (line.trim() === "") { flush(); mode = "text"; continue; }

  // продолжение переноса внутри абзаца или пункта списка
  buf.push(line.trim());
}
flush();

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: SIZE } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: SIZE, bold: true, color: "000000" } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: SIZE, bold: true, color: "000000" } },
    ],
  },
  numbering: {
    config: [{
      reference: "dash",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "—", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 794, hanging: 397 } }, run: { font: FONT, size: SIZE } },
      }],
    }],
  },
  sections: [{
    properties: {
      page: {
        margin: {
          top: convertMillimetersToTwip(20),
          bottom: convertMillimetersToTwip(20),
          left: convertMillimetersToTwip(30),
          right: convertMillimetersToTwip(15),
        },
      },
    },
    children,
  }],
});

Packer.toBuffer(doc).then((b) => {
  fs.writeFileSync("doklad.docx", b);
  console.log("ok: doklad.docx,", children.length, "абзацев");
});

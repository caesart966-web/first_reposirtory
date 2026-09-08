'use strict';
/**
 * Профессиональный буклет A4 из структурированного содержания.
 *
 * Содержание пишется простыми объектами (см. content/*.js), вёрстка целиком
 * здесь: обложка, оглавление, разделители глав, нумерация разделов, сноски,
 * врезки, таблицы, чек-листы, библиография и указатель.
 */
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageBreak,
  PageNumber, Footer, Header, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, PositionalTab, PositionalTabAlignment, PositionalTabRelativeTo,
  PositionalTabLeader, LevelFormat, convertMillimetersToTwip,
} = require('docx');
const { inline, plain } = require('./inline');

const SERIF = 'Times New Roman';
const SANS = 'Arial';
const MONO = 'Courier New';

const INK = '1A1A1A';
const ACCENT = '1F3864';
const SOFT = '5A6472';
const RULE = 'B7BFCC';

const BODY_SIZE = 22;          // 11pt
const CONTENT_WIDTH = convertMillimetersToTwip(210 - 25 - 25);

const NO_BORDER = { style: BorderStyle.NONE, size: 0, color: 'auto' };

const BOX_KINDS = {
  definition: { label: 'DEFINITION', fill: 'EEF2F8', edge: ACCENT },
  field: { label: 'FIELD NOTE', fill: 'F2F5EF', edge: '4F6B3A' },
  warning: { label: 'WATCH OUT', fill: 'FCF2EE', edge: '9C3B22' },
  case: { label: 'CASE STUDY', fill: 'F4F1EA', edge: '7A6234' },
  exercise: { label: 'PRACTICAL EXERCISE', fill: 'EFF1F4', edge: '3F4756' },
};

// ---------------------------------------------------------------------------
// Küçük yapı taşları
// ---------------------------------------------------------------------------

function para(text, opts = {}) {
  const { addFootnote, base, ...rest } = opts;
  return new Paragraph(Object.assign({
    children: inline(text, { addFootnote, base: Object.assign({ font: SERIF, size: BODY_SIZE, color: INK }, base) }),
    spacing: { after: 120, line: 276 },
    alignment: AlignmentType.JUSTIFIED,
  }, rest));
}

function heading(text, level, opts = {}) {
  const sizes = { 1: 32, 2: 26, 3: 23 };
  return new Paragraph(Object.assign({
    heading: { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 }[level],
    spacing: { before: level === 2 ? 320 : 240, after: 120 },
    keepNext: true,
    children: [new TextRun({
      text, font: SANS, size: sizes[level], bold: true,
      color: level === 3 ? SOFT : ACCENT,
    })],
  }, opts));
}

function cell(children, opts = {}) {
  return new TableCell(Object.assign({
    children,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    width: { size: opts.width || 1000, type: WidthType.DXA },
  }, opts.cellOpts || {}));
}

function tableBlock(spec, ctx) {
  const columns = spec.head.length;
  const weights = spec.widths || new Array(columns).fill(1);
  const total = weights.reduce((a, b) => a + b, 0);
  const widths = weights.map((w) => Math.round((CONTENT_WIDTH * w) / total));
  widths[columns - 1] = CONTENT_WIDTH - widths.slice(0, -1).reduce((a, b) => a + b, 0);

  const headRow = new TableRow({
    tableHeader: true,
    children: spec.head.map((text, i) => cell([
      new Paragraph({
        children: [new TextRun({ text, font: SANS, size: 18, bold: true, color: 'FFFFFF' })],
        spacing: { after: 0 },
      }),
    ], {
      width: widths[i],
      cellOpts: { shading: { type: ShadingType.CLEAR, fill: ACCENT, color: 'auto' } },
    })),
  });

  const rows = spec.rows.map((row, r) => new TableRow({
    children: row.map((text, i) => cell([
      new Paragraph({
        children: inline(String(text), { base: { font: SANS, size: 18, color: INK }, addFootnote: ctx.addFootnote }),
        spacing: { after: 0, line: 240 },
      }),
    ], {
      width: widths[i],
      cellOpts: r % 2 ? { shading: { type: ShadingType.CLEAR, fill: 'F4F6F9', color: 'auto' } } : {},
    })),
  }));

  const table = new Table({
    columnWidths: widths,
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    rows: [headRow, ...rows],
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE },
      left: NO_BORDER, right: NO_BORDER,
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      insideVertical: NO_BORDER,
    },
  });

  const out = [];
  if (spec.title) {
    out.push(new Paragraph({
      children: [new TextRun({ text: spec.title, font: SANS, size: 18, bold: true, color: ACCENT })],
      spacing: { before: 200, after: 80 },
      keepNext: true,
    }));
  }
  out.push(table);
  if (spec.note) {
    out.push(new Paragraph({
      children: inline(spec.note, { base: { font: SANS, size: 16, color: SOFT, italics: true }, addFootnote: ctx.addFootnote }),
      spacing: { before: 80, after: 200 },
    }));
  } else {
    out.push(new Paragraph({ text: '', spacing: { after: 160 } }));
  }
  return out;
}

function boxBlock(spec, ctx) {
  const kind = BOX_KINDS[spec.kind] || BOX_KINDS.definition;
  const paragraphs = [
    new Paragraph({
      children: [
        new TextRun({ text: kind.label, font: SANS, size: 15, bold: true, color: kind.edge, characterSpacing: 30 }),
        ...(spec.title ? [new TextRun({ text: '  ' + spec.title, font: SANS, size: 19, bold: true, color: INK })] : []),
      ],
      spacing: { after: 100 },
    }),
  ];
  for (const item of spec.body) {
    if (typeof item === 'string') {
      paragraphs.push(new Paragraph({
        children: inline(item, { base: { font: SERIF, size: 21, color: INK }, addFootnote: ctx.addFootnote }),
        spacing: { after: 100, line: 264 },
        alignment: AlignmentType.JUSTIFIED,
      }));
    } else if (item.bullets) {
      for (const line of item.bullets) {
        paragraphs.push(new Paragraph({
          numbering: { reference: 'box-bullets', level: 0 },
          children: inline(line, { base: { font: SERIF, size: 21, color: INK }, addFootnote: ctx.addFootnote }),
          spacing: { after: 60, line: 264 },
        }));
      }
    }
  }
  return [
    new Table({
      columnWidths: [CONTENT_WIDTH],
      width: { size: CONTENT_WIDTH, type: WidthType.DXA },
      rows: [new TableRow({
        children: [new TableCell({
          children: paragraphs,
          margins: { top: 160, bottom: 120, left: 200, right: 200 },
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, fill: kind.fill, color: 'auto' },
        })],
      })],
      borders: {
        top: { style: BorderStyle.SINGLE, size: 2, color: kind.edge },
        bottom: { style: BorderStyle.SINGLE, size: 2, color: kind.edge },
        left: { style: BorderStyle.SINGLE, size: 18, color: kind.edge },
        right: { style: BorderStyle.SINGLE, size: 2, color: kind.edge },
        insideHorizontal: NO_BORDER, insideVertical: NO_BORDER,
      },
    }),
    new Paragraph({ text: '', spacing: { after: 200 } }),
  ];
}

module.exports = {
  SERIF, SANS, MONO, INK, ACCENT, SOFT, RULE, BODY_SIZE, CONTENT_WIDTH,
  NO_BORDER, para, heading, tableBlock, boxBlock, cell,
};

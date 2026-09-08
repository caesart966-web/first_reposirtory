'use strict';
/** Собирает готовый документ из спецификации буклета. */
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, PageBreak, PageNumber,
  Footer, Header, LevelFormat, BorderStyle, convertMillimetersToTwip, HeadingLevel,
  TabStopType, LeaderType,
} = require('docx');
const fs = require('fs');
const { inline, plain } = require('./inline');
const B = require('./booklet');

const { SERIF, SANS, INK, ACCENT, SOFT, RULE, BODY_SIZE, CONTENT_WIDTH } = B;

function numberingConfig() {
  const bullet = (reference) => ({
    reference,
    levels: [{
      level: 0,
      format: LevelFormat.BULLET,
      text: '–',
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 480, hanging: 240 } }, run: { font: SERIF, size: BODY_SIZE } },
    }],
  });
  return {
    config: [
      bullet('bullets'),
      bullet('box-bullets'),
      {
        reference: 'steps',
        levels: [{
          level: 0,
          format: LevelFormat.DECIMAL,
          text: '%1.',
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 520, hanging: 280 } }, run: { font: SANS, size: 20, bold: true, color: ACCENT } },
        }],
      },
    ],
  };
}

/** Bir bölümün gövdesini paragraflara çevirir ve numaralandırmayı yürütür. */
function renderBlocks(blocks, ctx) {
  const out = [];
  for (const block of blocks) {
    if (block.h2) {
      ctx.h2 += 1; ctx.h3 = 0;
      if (ctx.chapter === null) {
        // Ön sayfalarda (önsöz) numaralandırma yok.
        ctx.section = block.h2;
        out.push(B.heading(block.h2, 2));
      } else {
        const label = `${ctx.chapter}.${ctx.h2}`;
        ctx.section = label;
        ctx.headings.push({ key: `S${label}`, label, title: block.h2, level: 2 });
        out.push(B.heading(`${label}  ${block.h2}`, 2));
      }
    } else if (block.h3) {
      ctx.h3 += 1;
      if (ctx.chapter === null) {
        out.push(B.heading(block.h3, 3));
      } else {
        const label = `${ctx.chapter}.${ctx.h2}.${ctx.h3}`;
        ctx.section = label;
        out.push(B.heading(`${label}  ${block.h3}`, 3));
      }
    } else if (block.p) {
      ctx.record(block.p);
      out.push(B.para(block.p, { addFootnote: ctx.addFootnote }));
    } else if (block.lead) {
      ctx.record(block.lead);
      out.push(B.para(block.lead, {
        addFootnote: ctx.addFootnote,
        base: { size: 23, color: '2B3442' },
        spacing: { after: 200, line: 288 },
      }));
    } else if (block.bullets) {
      block.bullets.forEach((line, i) => {
        ctx.record(line);
        out.push(new Paragraph({
          numbering: { reference: 'bullets', level: 0 },
          children: inline(line, { base: { font: SERIF, size: BODY_SIZE, color: INK }, addFootnote: ctx.addFootnote }),
          spacing: { after: i === block.bullets.length - 1 ? 160 : 60, line: 264 },
        }));
      });
    } else if (block.steps) {
      block.steps.forEach((line, i) => {
        ctx.record(line);
        out.push(new Paragraph({
          numbering: { reference: 'steps', level: 0 },
          children: inline(line, { base: { font: SERIF, size: BODY_SIZE, color: INK }, addFootnote: ctx.addFootnote }),
          spacing: { after: i === block.steps.length - 1 ? 160 : 80, line: 264 },
        }));
      });
    } else if (block.checklist) {
      block.checklist.forEach((line, i) => {
        ctx.record(line);
        out.push(new Paragraph({
          indent: { left: 400, hanging: 260 },
          children: [
            new TextRun({ text: '☐ ', font: SANS, size: BODY_SIZE, color: ACCENT }),
            ...inline(line, { base: { font: SERIF, size: BODY_SIZE, color: INK }, addFootnote: ctx.addFootnote }),
          ],
          spacing: { after: i === block.checklist.length - 1 ? 160 : 60, line: 264 },
        }));
      });
    } else if (block.table) {
      (block.table.rows || []).forEach((row) => row.forEach((c) => ctx.record(String(c))));
      ctx.record(block.table.title || '');
      out.push(...B.tableBlock(block.table, ctx));
    } else if (block.box) {
      block.box.body.forEach((item) => ctx.record(typeof item === 'string' ? item : (item.bullets || []).join(' ')));
      ctx.record(block.box.title || '');
      out.push(...B.boxBlock(block.box, ctx));
    } else if (block.quote) {
      ctx.record(block.quote);
      out.push(new Paragraph({
        children: inline(block.quote, { base: { font: SERIF, size: 24, italics: true, color: ACCENT } }),
        alignment: AlignmentType.LEFT,
        indent: { left: 560, right: 560 },
        border: { left: { style: BorderStyle.SINGLE, size: 12, color: RULE, space: 12 } },
        spacing: { before: 200, after: block.by ? 40 : 240, line: 288 },
      }));
      if (block.by) {
        out.push(new Paragraph({
          children: [new TextRun({ text: '— ' + block.by, font: SANS, size: 17, color: SOFT })],
          indent: { left: 560 },
          spacing: { after: 240 },
        }));
      }
    } else if (block.spacer) {
      out.push(new Paragraph({ text: '', spacing: { after: block.spacer } }));
    } else {
      throw new Error('Bilinmeyen blok: ' + JSON.stringify(Object.keys(block)));
    }
  }
  return out;
}

function coverPage(meta) {
  const line = (text, opts) => new Paragraph(Object.assign({
    alignment: AlignmentType.CENTER, spacing: { after: 160 },
    children: [new TextRun(Object.assign({ font: SANS, color: INK }, opts.run))],
  }, opts.para));

  return [
    new Paragraph({ text: '', spacing: { after: 2600 } }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 120 },
      children: [new TextRun({ text: meta.eyebrow, font: SANS, size: 19, bold: true, color: ACCENT, characterSpacing: 60 })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: ACCENT, space: 12 } },
      children: [new TextRun({ text: '', size: 2 })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 },
      children: [new TextRun({ text: meta.title, font: SANS, size: 52, bold: true, color: INK })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 600 },
      children: [new TextRun({ text: meta.subtitle, font: SERIF, size: 26, italics: true, color: SOFT })],
    }),
    ...meta.blurb.map((text) => new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 120 },
      indent: { left: 900, right: 900 },
      children: inline(text, { base: { font: SERIF, size: 21, color: '3A414D' } }),
    })),
    new Paragraph({ text: '', spacing: { after: 1800 } }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 80 },
      children: [new TextRun({ text: meta.institutional, font: SANS, size: 19, bold: true, color: ACCENT })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: meta.edition, font: SANS, size: 17, color: SOFT })],
    }),
  ];
}

function tocPage(headings, pages) {
  const out = [
    B.heading('Table of Contents', 1, { spacing: { after: 240 }, heading: HeadingLevel.HEADING_1 }),
  ];
  for (const item of headings) {
    const page = pages ? pages[item.key] : null;
    const isChapter = item.level === 1;
    out.push(new Paragraph({
      spacing: { before: isChapter ? 160 : 20, after: 20 },
      indent: { left: isChapter ? 0 : 420 },
      tabStops: [{
        type: TabStopType.RIGHT,
        position: B.CONTENT_WIDTH - (isChapter ? 0 : 420),
        leader: LeaderType.DOT,
      }],
      children: [
        new TextRun({
          text: isChapter ? item.title : `${item.label}  ${item.title}`,
          font: isChapter ? SANS : SERIF,
          size: isChapter ? 21 : 20,
          bold: isChapter,
          color: isChapter ? ACCENT : INK,
        }),
        new TextRun({ text: '\t', font: SERIF, size: 19, color: SOFT }),
        new TextRun({
          text: page ? String(page) : '–',
          font: SANS, size: 19, bold: isChapter, color: isChapter ? ACCENT : SOFT,
        }),
      ],
    }));
  }
  return out;
}

function chapterDivider(chapter, number) {
  return [
    new Paragraph({ children: [new PageBreak()] }),
    new Paragraph({ text: '', spacing: { after: 2200 } }),
    new Paragraph({
      spacing: { after: 120 },
      children: [new TextRun({ text: `CHAPTER ${number}`, font: SANS, size: 19, bold: true, color: SOFT, characterSpacing: 80 })],
    }),
    new Paragraph({
      spacing: { after: 240 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 14 } },
      children: [new TextRun({ text: chapter.title, font: SANS, size: 40, bold: true, color: ACCENT })],
    }),
    ...chapter.abstract.map((text) => new Paragraph({
      spacing: { after: 160, line: 300 },
      alignment: AlignmentType.JUSTIFIED,
      children: inline(text, { base: { font: SERIF, size: 23, color: '2B3442' } }),
    })),
    ...(chapter.outcomes ? [
      new Paragraph({
        spacing: { before: 320, after: 120 },
        children: [new TextRun({ text: 'By the end of this chapter you should be able to', font: SANS, size: 19, bold: true, color: INK })],
      }),
      ...chapter.outcomes.map((text) => new Paragraph({
        numbering: { reference: 'bullets', level: 0 },
        spacing: { after: 60, line: 264 },
        children: inline(text, { base: { font: SERIF, size: 21, color: INK } }),
      })),
    ] : []),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

module.exports = { numberingConfig, renderBlocks, coverPage, tocPage, chapterDivider };

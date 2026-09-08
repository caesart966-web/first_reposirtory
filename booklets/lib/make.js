'use strict';
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, PageBreak, PageNumber,
  Footer, Header, BorderStyle, convertMillimetersToTwip, HeadingLevel,
} = require('docx');
const { inline, plain } = require('./inline');
const B = require('./booklet');
const D = require('./document');

const { SERIF, SANS, INK, ACCENT, SOFT, RULE, BODY_SIZE } = B;

const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

function makeContext() {
  const ctx = {
    chapter: null, h2: 0, h3: 0, section: '—',
    headings: [],
    footnotes: {},
    footnoteId: 0,
    sectionText: {},
    addFootnote(text) {
      ctx.footnoteId += 1;
      ctx.footnotes[ctx.footnoteId] = {
        children: [new Paragraph({
          children: inline(text, { base: { font: SERIF, size: 17, color: '333333' } }),
          spacing: { after: 40, line: 220 },
        })],
      };
      ctx.record(text);
      return ctx.footnoteId;
    },
    record(text) {
      const key = ctx.section;
      ctx.sectionText[key] = (ctx.sectionText[key] || '') + ' ' + plain(text).toLowerCase();
    },
  };
  return ctx;
}

function frontSection(title, blocks, ctx) {
  ctx.chapter = null; ctx.h2 = 0; ctx.h3 = 0;
  ctx.section = title;
  return [
    new Paragraph({ children: [new PageBreak()] }),
    B.heading(title, 1),
    ...D.renderBlocks(blocks, ctx),
  ];
}

function bibliographySection(entries) {
  return [
    new Paragraph({ children: [new PageBreak()] }),
    B.heading('Bibliography', 1),
    new Paragraph({
      spacing: { after: 240 },
      children: inline(
        'Sources are listed alphabetically. Institutional publications are cited by issuing body; ' +
        'where a source is updated periodically, consult the latest edition rather than the one current at the time of writing.',
        { base: { font: SERIF, size: 19, italics: true, color: SOFT } },
      ),
    }),
    ...entries.slice().sort((a, b) => plain(a).localeCompare(plain(b))).map((entry) => new Paragraph({
      spacing: { after: 100, line: 252 },
      indent: { left: 480, hanging: 480 },
      children: inline(entry, { base: { font: SERIF, size: 20, color: INK } }),
    })),
  ];
}

function indexSection(terms, ctx) {
  const rows = [];
  for (const term of terms) {
    const needle = plain(term).toLowerCase();
    const hits = Object.keys(ctx.sectionText)
      .filter((key) => /^(\d+|[A-Z])\.\d/.test(key) && ctx.sectionText[key].includes(needle))
      .sort((a, b) => a.localeCompare(b, 'en', { numeric: true }));
    if (hits.length) rows.push([term, hits.map((h) => '§' + h).join(', ')]);
  }
  rows.sort((a, b) => a[0].localeCompare(b[0]));

  return [
    new Paragraph({ children: [new PageBreak()] }),
    B.heading('Index', 1),
    new Paragraph({
      spacing: { after: 240 },
      children: inline(
        'References are to numbered sections (§), not pages, so they remain valid if the booklet is reformatted or reprinted.',
        { base: { font: SERIF, size: 19, italics: true, color: SOFT } },
      ),
    }),
    ...rows.map(([term, refs]) => new Paragraph({
      spacing: { after: 40, line: 240 },
      indent: { left: 420, hanging: 420 },
      children: [
        new TextRun({ text: term + '  ', font: SERIF, size: 20, color: INK }),
        new TextRun({ text: refs, font: SANS, size: 17, color: SOFT }),
      ],
    })),
  ];
}

function buildBooklet(spec, pages) {
  const ctx = makeContext();
  const body = [];

  // Ön sayfalar
  ctx.section = 'foreword';
  const foreword = spec.foreword ? frontSection('Foreword', spec.foreword, ctx) : [];

  // Bölümler
  const chapterBlocks = [];
  spec.chapters.forEach((chapter, i) => {
    ctx.chapter = i + 1; ctx.h2 = 0; ctx.h3 = 0;
    ctx.section = `chapter-${i + 1}`;
    ctx.headings.push({ key: `C${i + 1}`, title: `Chapter ${i + 1} — ${chapter.title}`, level: 1 });
    chapterBlocks.push(...D.chapterDivider(chapter, i + 1));
    chapterBlocks.push(...D.renderBlocks(chapter.blocks, ctx));
  });

  // Ekler
  const appendixBlocks = [];
  (spec.appendices || []).forEach((appendix, i) => {
    const letter = LETTERS[i];
    ctx.chapter = letter; ctx.h2 = 0; ctx.h3 = 0;
    ctx.section = `appendix-${letter}`;
    ctx.headings.push({ key: `A${letter}`, title: `Appendix ${letter} — ${appendix.title}`, level: 1 });
    appendixBlocks.push(new Paragraph({ children: [new PageBreak()] }));
    appendixBlocks.push(B.heading(`Appendix ${letter} — ${appendix.title}`, 1));
    appendixBlocks.push(...D.renderBlocks(appendix.blocks, ctx));
  });

  const backBlocks = [];
  if (spec.bibliography) {
    ctx.headings.push({ key: 'BIB', title: 'Bibliography', level: 1 });
    backBlocks.push(...bibliographySection(spec.bibliography));
  }
  if (spec.index) {
    ctx.headings.push({ key: 'IDX', title: 'Index', level: 1 });
    backBlocks.push(...indexSection(spec.index, ctx));
  }

  // Oglavlenie: bölüm ve alt bölüm başlıkları, sıraya göre
  const tocEntries = [];
  if (spec.foreword) tocEntries.push({ key: 'FWD', title: 'Foreword', level: 1 });
  for (const h of ctx.headings) tocEntries.push(h);

  const toc = D.tocPage(tocEntries, pages);

  body.push(...toc, ...foreword, ...chapterBlocks, ...appendixBlocks, ...backBlocks);

  const margin = {
    top: convertMillimetersToTwip(20),
    bottom: convertMillimetersToTwip(18),
    left: convertMillimetersToTwip(25),
    right: convertMillimetersToTwip(25),
  };

  const doc = new Document({
    creator: spec.meta.institutional,
    title: spec.meta.title,
    description: spec.meta.subtitle,
    numbering: D.numberingConfig(),
    footnotes: ctx.footnotes,
    styles: {
      default: {
        document: { run: { font: SERIF, size: BODY_SIZE, color: INK } },
      },
    },
    sections: [
      {
        properties: { page: { margin } },
        children: D.coverPage(spec.meta),
      },
      {
        properties: { page: { margin } },
        headers: {
          default: new Header({
            children: [new Paragraph({
              spacing: { after: 60 },
              border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE, space: 6 } },
              children: [new TextRun({ text: spec.meta.runningHead, font: SANS, size: 16, color: SOFT, characterSpacing: 20 })],
            })],
          }),
        },
        footers: {
          default: new Footer({
            children: [new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [new TextRun({ children: [PageNumber.CURRENT], font: SANS, size: 17, color: SOFT })],
            })],
          }),
        },
        children: body,
      },
    ],
  });

  return { doc, headings: tocEntries, ctx };
}

async function writeBooklet(spec, outFile, pages) {
  const { doc, headings, ctx } = buildBooklet(spec, pages);
  const buffer = await Packer.toBuffer(doc);
  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  fs.writeFileSync(outFile, buffer);
  return { headings, footnotes: ctx.footnoteId, sections: Object.keys(ctx.sectionText).length };
}

module.exports = { buildBooklet, writeBooklet };

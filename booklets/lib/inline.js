'use strict';
const { TextRun, FootnoteReferenceRun, ExternalHyperlink } = require('docx');

const BODY = { font: 'Georgia', size: 21 }; // 10.5pt

/**
 * Küçük satır içi biçimleme: **kalın**, *italik*, `kod`, [^dipnot], [bağlantı](url).
 * Amaç, içerik dosyalarının düz metin gibi okunabilmesi; docx API'si metnin
 * arasına karışmasın.
 */
function inline(text, opts = {}) {
  const base = Object.assign({}, BODY, opts.base || {});
  const addFootnote = opts.addFootnote;
  const runs = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[\^[^\]]+\]|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) {
      runs.push(new TextRun(Object.assign({}, base, { text: text.slice(last, match.index) })));
    }
    const token = match[0];
    if (token.startsWith('**')) {
      runs.push(new TextRun(Object.assign({}, base, { text: token.slice(2, -2), bold: true })));
    } else if (token.startsWith('`')) {
      runs.push(new TextRun(Object.assign({}, base, {
        text: token.slice(1, -1), font: 'Consolas', size: base.size - 2,
      })));
    } else if (token.startsWith('[^')) {
      if (!addFootnote) throw new Error('Dipnot bu bağlamda kullanılamaz: ' + token);
      runs.push(new FootnoteReferenceRun(addFootnote(token.slice(2, -1))));
    } else if (token.startsWith('[')) {
      const [, label, url] = token.match(/\[([^\]]+)\]\(([^)]+)\)/);
      runs.push(new ExternalHyperlink({
        link: url,
        children: [new TextRun(Object.assign({}, base, {
          text: label, style: 'Hyperlink',
        }))],
      }));
    } else {
      runs.push(new TextRun(Object.assign({}, base, { text: token.slice(1, -1), italics: true })));
    }
    last = pattern.lastIndex;
  }
  if (last < text.length) {
    runs.push(new TextRun(Object.assign({}, base, { text: text.slice(last) })));
  }
  return runs;
}

/** Dizin ve arama için: biçimleme işaretlerinden arındırılmış düz metin. */
function plain(text) {
  return String(text)
    .replace(/\[\^[^\]]+\]/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[*`]/g, '');
}

module.exports = { inline, plain, BODY };

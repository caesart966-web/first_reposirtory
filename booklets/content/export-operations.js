'use strict';
const meta = require('./export/meta');

module.exports = Object.assign({}, meta, {
  chapters: [
    require('./export/ch1'),
    require('./export/ch2'),
    require('./export/ch3'),
    require('./export/ch4'),
    require('./export/ch5'),
    require('./export/ch6'),
  ],
  appendices: require('./export/appendices'),
  index: [
    'A.TR', 'anti-dumping', 'ATA carnet', 'bill of lading', 'CBAM', 'CE marking',
    'certificate of origin', 'CMR', 'commodity code', 'container', 'cut-off',
    'demurrage', 'detention', 'discrepancy', 'documentary collection',
    'documentary credit', 'dual-use', 'EORI', 'EUR.1', 'e-invoice',
    'export declaration', 'FCA', 'FOB', 'free time', 'gate-in', 'HS code',
    'Incoterms', 'insurance', 'inward processing', 'ISPM 15', 'letter of credit',
    'loading programme', 'material master', 'origin', 'packing list',
    'phytosanitary', 'proforma invoice', 'REACH', 'roll-over', 'sanctions',
    'screening', 'seal number', 'Section 232', 'UCP 600', 'UKCA', 'VAT refund',
    'verified gross mass', 'vessel', 'YYS',
  ],
});

'use strict';

module.exports = [
  {
    title: 'Incoterms® 2020 Quick Reference',
    blocks: [
      { h2: 'The eleven rules at a glance' },
      {
        p: 'The table below is an aid to memory for people who already know the rules. It is not a ' +
          'substitute for the ICC text, which is the only authority and which your desk should own.',
      },
      {
        table: {
          title: 'Table A.1 — Cost and risk allocation',
          head: ['Rule', 'Mode', 'Risk passes to buyer', 'Seller pays carriage to', 'Export / import clearance'],
          widths: [1.2, 1.8, 3, 2.6, 2.4],
          rows: [
            ['EXW', 'Any', 'At seller\'s premises', 'Nothing', 'Buyer / buyer'],
            ['FCA', 'Any', 'On delivery to buyer\'s carrier', 'Named place only', 'Seller / buyer'],
            ['FAS', 'Sea / inland waterway', 'Alongside the vessel', 'Quay at port of shipment', 'Seller / buyer'],
            ['FOB', 'Sea / inland waterway', 'On board the vessel', 'Port of shipment', 'Seller / buyer'],
            ['CFR', 'Sea / inland waterway', 'On board the vessel', 'Named port of destination', 'Seller / buyer'],
            ['CIF', 'Sea / inland waterway', 'On board the vessel', 'Named port of destination + insurance (min. ICC C)', 'Seller / buyer'],
            ['CPT', 'Any', 'On handover to first carrier', 'Named place of destination', 'Seller / buyer'],
            ['CIP', 'Any', 'On handover to first carrier', 'Named place + insurance (min. ICC A)', 'Seller / buyer'],
            ['DAP', 'Any', 'At destination, ready for unloading', 'Named place of destination', 'Seller / buyer'],
            ['DPU', 'Any', 'At destination, after unloading', 'Named place, unloaded', 'Seller / buyer'],
            ['DDP', 'Any', 'At destination, cleared for import', 'Named place, duty paid', 'Seller / seller'],
          ],
          note: 'Incoterms® is a registered trademark of the International Chamber of Commerce. Always write the rule with its named place and edition: *FCA Gebze, Türkiye (Incoterms® 2020)*.',
        },
      },
      { h2: 'Five things people get wrong' },
      {
        bullets: [
          '**Incoterms do not determine when title passes.** Title is a matter for the sale contract and the governing law.',
          '**They do not set payment terms.** CIF does not mean the buyer pays on arrival.',
          '**FOB is for bulk and break-bulk, not containers.** For containers handed over at a terminal, FCA reflects reality.',
          '**A rule without a named place is incomplete**, and a named place that is a country rather than a point is nearly as bad.',
          '**Only CIF and CIP oblige the seller to insure**, and they require different minimum covers.',
        ],
      },
    ],
  },
  {
    title: 'Classification: Working with HS Codes',
    blocks: [
      { h2: 'What the code has to survive' },
      {
        p: 'A commodity code is a legal assertion about what the goods are. It determines duty at ' +
          'destination, whether a licence or certificate is needed, whether a trade defence measure ' +
          'applies, and whether the shipment attracts scrutiny. It also has to be defensible years later, ' +
          'in a post-clearance audit, by someone who has never seen the product.',
      },
      { h2: 'A workable classification method' },
      {
        steps: [
          '**Describe the product physically**, not commercially: material, function, degree of processing, presentation. Marketing language classifies nothing.',
          '**Work down the structure** — chapter, heading, subheading — applying the General Rules of Interpretation in order rather than searching for a familiar word.',
          '**Check the section and chapter notes.** They exclude more than they include and they are binding, not advisory.',
          '**Compare against the explanatory notes** and, where they exist, published classification decisions for similar goods.',
          '**Record the reasoning**, not just the code. Three lines explaining why heading X and not heading Y is what protects the classification later.',
          '**Reconcile with the destination code** your buyer will declare. Beyond the first six digits, national codes diverge, and a divergence is worth knowing about before shipment (§4.7).',
        ],
      },
      {
        box: {
          kind: 'field',
          title: 'When you are genuinely unsure',
          body: [
            'Do not guess and do not adopt the buyer\'s code because it is convenient. Two routes exist: ask ' +
            'your customs broker for a written opinion, or apply for a binding tariff decision from the ' +
            'customs administration. A binding decision takes time but ends the argument, and for a product ' +
            'you will ship for years it is cheap.',
          ],
        },
      },
      {
        box: {
          kind: 'warning',
          title: 'The two classification errors that cost most',
          body: [
            {
              bullets: [
                '**Classifying to the duty you want.** A code chosen because it carries a lower rate is a misdeclaration; the retroactive assessment lands on your customer and the relationship does not survive it.',
                '**Letting the code drift from the product.** A material master coded correctly in 2019 for a product that has since changed its composition is now wrong, quietly, on every shipment.',
              ],
            },
          ],
        },
      },
    ],
  },
  {
    title: 'Glossary',
    blocks: [
      {
        table: {
          title: 'Table C.1 — Terms used in this guide',
          head: ['Term', 'Meaning'],
          widths: [2.6, 7.4],
          rows: [
            ['A.TR', 'Movement certificate evidencing free circulation status in the EU–Türkiye Customs Union. Not a proof of origin.'],
            ['AEO / YYS', 'Authorised economic operator; in Türkiye, *Yetkilendirilmiş Yükümlü Sertifikası*. Brings simplified customs procedures.'],
            ['ATA carnet', 'International customs document for temporary admission of goods such as samples and exhibition material.'],
            ['CAD', 'Cash against documents; a documentary collection in which documents are released against payment.'],
            ['CBAM', 'The EU carbon border adjustment mechanism, which attaches an emissions cost to imports of covered goods.'],
            ['CMR', 'The convention governing international carriage of goods by road, and the consignment note issued under it.'],
            ['Cut-off', 'The carrier\'s deadline — separately for documentation, verified gross mass and gate-in — before a sailing.'],
            ['Demurrage / detention', 'Charges for keeping a container beyond free time inside the terminal (demurrage) or outside it (detention).'],
            ['Discrepancy', 'A defect in documents presented under a documentary credit, entitling the bank to refuse.'],
            ['EUR.1', 'Movement certificate evidencing preferential origin under a free trade agreement.'],
            ['GÇB', '*Gümrük Çıkış Beyannamesi* — the Turkish export customs declaration.'],
            ['HS code', 'Harmonised System commodity code; internationally harmonised to six digits, extended nationally beyond that.'],
            ['Incoterms®', 'ICC rules allocating cost, risk and obligations between seller and buyer in a sale of goods.'],
            ['Inward processing', 'Regime allowing duty relief on imported inputs that are processed and re-exported.'],
            ['ISPM 15', 'International standard requiring treatment and marking of solid wood packaging material.'],
            ['L/C', 'Documentary credit; a bank undertaking to pay against complying documents, governed in practice by UCP 600.'],
            ['Roll-over', 'The carrier moving a booked container to a later sailing.'],
            ['UCP 600', 'The ICC Uniform Customs and Practice for Documentary Credits, 2007 revision.'],
            ['URC 522', 'The ICC Uniform Rules for Collections, governing documentary collections.'],
            ['VGM', 'Verified gross mass of a packed container, required under SOLAS before loading.'],
          ],
        },
      },
    ],
  },
  {
    title: 'Where to Check: Primary Sources',
    blocks: [
      {
        p: 'Nothing in this guide should be relied on without checking the source. The list below is what ' +
          'an export desk should have bookmarked; it is deliberately short, because a source you actually ' +
          'open beats ten you have collected.',
      },
      {
        table: {
          title: 'Table D.1 — What to check where',
          head: ['Question', 'Authoritative source'],
          widths: [4.4, 5.6],
          rows: [
            ['Turkish export procedure, licences, regime decisions', 'Ministry of Trade (Ticaret Bakanlığı)'],
            ['Tariff classification, customs procedure, authorised operator status', 'Turkish customs administration and the integrated tariff system'],
            ['VAT exemption and refund procedure', 'Revenue Administration (Gelir İdaresi Başkanlığı)'],
            ['Repatriation of export proceeds', 'The current export circular (*İhracat Genelgesi*) and your bank'],
            ['Exporters\' association registration and sector data', 'Turkish Exporters Assembly (TİM) and the relevant exporters\' association'],
            ['Export credit, guarantees and buyer credit insurance', 'Türk Eximbank'],
            ['Incoterms®, UCP 600, URC 522 texts', 'International Chamber of Commerce publications'],
            ['EU tariff, measures, and product legislation', 'The EU integrated tariff database and the Official Journal'],
            ['UK tariff, origin rules and product marking', 'UK government trade tariff and guidance'],
            ['US tariff, entry requirements and sanctions listings', 'US Customs and Border Protection; OFAC sanctions lists'],
            ['EAEU technical regulations and conformity', 'Eurasian Economic Commission'],
            ['Chinese product registration and inspection', 'General Administration of Customs of China (GACC)'],
          ],
          note: 'Where a rule can change, this guide has said so. Where it has not said so, assume it can change anyway and check.',
        },
      },
    ],
  },
];

'use strict';

module.exports = {
  title: 'Country Compliance Desk',
  abstract: [
    'A Turkish exporter operates under one body of law and is reached by several others. Turkish rules ' +
    'bind you directly and are enforced against you. Foreign rules reach you through your buyer, your ' +
    'bank and your contract — and they are enforced by losing the shipment, the payment or the customer.',
    'This chapter is a desk reference for the six jurisdictions that dominate Turkish export practice. It ' +
    'is deliberately structured the same way for each: what governs, what it means for your documents, ' +
    'and what most often goes wrong.',
  ],
  outcomes: [
    'Identify, for any destination, which requirements are yours and which are your buyer\'s.',
    'Run a screening routine before quoting, not after shipping.',
    'Recognise the recurring compliance traps in EU, UK, US, Russian and Chinese trade.',
    'Know when to stop a transaction and how to record that decision.',
  ],
  blocks: [
    { h2: 'Using this chapter' },
    {
      lead: 'Everything below is a map, not a legal text. Tariff lines, listings and thresholds change on a ' +
        'timescale of weeks, and a guide that pretended otherwise would be dangerous rather than useful.',
    },
    {
      p: 'Each section names the primary source you must open before you rely on anything. The discipline ' +
        'that separates a professional from an enthusiastic amateur is not knowing the rule from memory — ' +
        'it is knowing which source is authoritative and checking it at the moment of commitment. Quote ' +
        'the source in your internal file note; when the rule changes six months later, your file will ' +
        'show that the decision was reasonable when it was made.',
    },
    {
      box: {
        kind: 'warning',
        title: 'Where this guide stops',
        body: [
          'This chapter explains how to establish that a transaction is lawful, how to document that ' +
          'determination, and when to decline. It does not explain how to move restricted goods, how to ' +
          'route payments around a control, or how to structure a sale so that a prohibition does not ' +
          'appear to apply. Those are not grey areas that experienced operators quietly navigate; they are ' +
          'the conduct that ends companies, removes correspondent banking relationships and creates ' +
          'personal liability for the people who signed.',
          'If your analysis reaches "this is prohibited unless we present it differently", the analysis is ' +
          'finished and the answer is no. Escalate it in writing.',
        ],
      },
    },

    { h2: 'Türkiye — the baseline that binds you' },
    {
      p: 'Turkish export law is the only body of rules in this chapter that can be enforced against you ' +
        'directly and routinely. The framework rests on the Customs Law and the export regime instruments ' +
        'issued under it, administered through the customs administration and, for most exporters, ' +
        'experienced day to day through the exporters\' associations and the single window.',
    },
    {
      table: {
        title: 'Table 4.1 — Turkish framework: what each instrument does to your desk',
        head: ['Instrument', 'What it governs', 'Where it touches your work'],
        widths: [2.8, 3.4, 4.2],
        rows: [
          ['Customs Law No. 4458 and its implementing regulation', 'Declarations, procedures, transit, penalties, post-clearance control', 'Every declaration; the record retention you will need years later'],
          ['Export Regime Decree and Export Regulation', 'Which goods may be exported, and under what registration or licence', 'Goods subject to registration or authorisation; prohibited and restricted lists'],
          ['Exporters\' associations regime', 'Registration of the declaration and the associations\' contribution', 'A declaration lodged without registration is a refund problem later'],
          ['e-invoicing rules', 'Electronic issue of the export invoice and its match to the declaration', 'The invoice is created in a state system before it enters your set'],
          ['Single Window System', 'Electronic submission of permits and certificates', 'Licences and certificates flow to customs electronically; paper is the exception'],
          ['Inward Processing Regime', 'Relief on imported inputs used in exported goods', 'Only if the authorisation is in place *before* the inputs arrive'],
          ['Export proceeds circular', 'Repatriation of proceeds and sale of a share to the Central Bank', 'Percentage and period have changed repeatedly — verify each period'],
          ['VAT legislation', 'Export exemption with credit, and refund procedure', 'The closed declaration is the key that unlocks the refund'],
        ],
        note: 'Primary sources: Ministry of Trade (Ticaret Bakanlığı) and the Revenue Administration (Gelir İdaresi Başkanlığı). Check the current text before relying on any line in this table.',
      },
    },
    {
      box: {
        kind: 'field',
        title: 'Inward processing is decided before the input is bought',
        body: [
          'The Inward Processing Regime lets you bring in inputs without paying duty and VAT, provided the ' +
          'finished goods are exported within the authorisation period. It is one of the largest ' +
          'competitiveness levers available to a Turkish manufacturer — and it is unavailable ' +
          'retroactively. Purchasing imports the material, but it is the export desk that knows the ' +
          'material is destined for an export order. If that information does not move at purchase-order ' +
          'time, the relief is lost for that batch.',
        ],
      },
    },

    { h2: 'European Union — the Customs Union and everything it does not cover' },
    {
      p: 'The EU–Türkiye Customs Union removes customs duty on industrial goods in free circulation, ' +
        'evidenced by an A.TR movement certificate. Junior desks read this as "no barriers to the EU". ' +
        'Experienced desks read it as "no *duty* on *industrial* goods, and every other kind of ' +
        'requirement still applies".',
    },
    {
      bullets: [
        '**Scope.** The Customs Union covers industrial products and processed agricultural goods; primary agricultural products and, historically, coal and steel are handled under separate arrangements. Confirm the treatment of your specific tariff line rather than your sector.',
        '**A.TR is free circulation, not origin.** Trade defence duties — anti-dumping, countervailing — are applied by origin regardless of the A.TR. See the trap in §3.4.',
        '**Product compliance is a separate universe from customs.** CE marking, harmonised standards, REACH, RoHS and sector regulations apply to the product, not to the shipment, and non-compliance surfaces at market surveillance rather than at the border.',
        '**REACH obligations fall on the EU-based importer or on an Only Representative appointed by you.** A Turkish manufacturer exporting substances or mixtures cannot register directly; the practical choice is to let the importer register or to appoint an Only Representative, which keeps the registration under your control if you change distributors.',
        '**General product safety.** For consumer products, the EU requires a responsible economic operator established in the Union whose details appear on the product or packaging. A distributor arrangement that leaves nobody named is a market-access failure, not a paperwork one.',
        '**Carbon border adjustment.** CBAM covers goods including iron and steel, aluminium, cement, fertilisers, hydrogen and electricity. Reporting obligations fall on the EU importer, but the emissions data can only come from you. Exporters in covered sectors should be able to produce installation-level embedded-emissions data on request; those who cannot will lose orders to those who can. Verify current scope, thresholds and timing — this regime is still moving.',
      ],
    },
    {
      box: {
        kind: 'case',
        title: 'Duty-free and still dutiable',
        body: [
          'A Turkish trading company bought steel fasteners of far-eastern origin, held them in free ' +
          'circulation in Türkiye, and sold them to a German distributor under an A.TR. No customs duty was ' +
          'charged on entry, exactly as expected.',
          'Eleven months later the German importer received a post-clearance demand: the goods were subject ' +
          'to an EU anti-dumping duty applied by **origin**, and the A.TR had never displaced it. The ' +
          'importer paid, then turned to the contract. The Turkish seller had described the goods as ' +
          '"Turkish origin" on the invoice because they had been shipped from Türkiye.',
          'The commercial loss was the customer. The lesson is narrow and worth memorising: **an A.TR ' +
          'answers a duty question, a certificate of origin answers an origin question, and only the second ' +
          'protects you against a trade defence measure.**',
        ],
      },
    },

    { h2: 'United Kingdom — a customs border, and a different set of marks' },
    {
      p: 'Since the end of the transition period the United Kingdom is outside the EU customs territory, ' +
        'and therefore outside the EU–Türkiye Customs Union. The A.TR has no application to the UK. Trade ' +
        'runs instead on the bilateral free trade agreement in force since the beginning of 2021, which ' +
        'means **preference must be claimed on origin** rather than assumed on free circulation.',
    },
    {
      bullets: [
        '**Origin proof.** A EUR.1 movement certificate, or an origin declaration on the invoice where you qualify as an approved exporter. The origin rules of the agreement — not the fact of shipping from Türkiye — determine whether the claim is valid.',
        '**Cumulation and verification.** Claims are subject to verification requests years after the event. Keep supplier declarations and production records for the period the agreement specifies.',
        '**Customs formalities.** UK import declarations are made by the UK importer through the customs declaration service; your obligations are documentary. Confirm who holds the GB EORI and who is importer of record before quoting a delivered term.',
        '**Product marking.** The UKCA mark is the UK conformity route, but recognition of CE marking has been extended for a large share of goods. Whether your product may still be placed on the GB market under CE depends on the product area — verify per product, and note that Northern Ireland follows different rules again.',
        '**Sanitary and phytosanitary controls** on food, plants and animal products have been introduced in phases with changing documentary and inspection requirements. For these goods, check the current UK import model rather than relying on last year\'s experience.',
      ],
    },

    { h2: 'United States — your buyer imports, your compliance still travels' },
    {
      p: 'In a sale to a US buyer the importer of record is normally the buyer, and the entry, tariff ' +
        'classification and duty are theirs. This leads to a common misreading — that US rules are not ' +
        'your problem. Three of them are.',
    },
    {
      table: {
        title: 'Table 4.2 — What actually reaches a Turkish seller from the US side',
        head: ['Requirement', 'Whose obligation', 'Why it reaches you'],
        widths: [2.6, 2.4, 5.4],
        rows: [
          ['Importer Security Filing (ISF, "10+2")', 'US importer / carrier', 'The data comes from you, and it is due before the container is loaded in Türkiye. Late data means the box does not sail.'],
          ['CBP entry and HTSUS classification', 'US importer', 'Your invoice description and HS code drive it; a mismatch delays clearance and invites a valuation question'],
          ['Section 232 / Section 301 duties', 'US importer pays', 'Steel and aluminium measures have applied to Turkish goods at varying rates. Confirm the current rate before quoting DDP or agreeing to bear duty.'],
          ['FDA, USDA, FCC, CPSC requirements', 'US importer, but product-based', 'Prior notice for food, facility registration, labelling — all of which depend on documents only you can issue'],
          ['OFAC sanctions', 'US persons; and anyone using USD clearing', 'Your bank screens the transaction. A counterparty or vessel on a list stops the payment, not just the shipment.'],
          ['Forced labour import ban (UFLPA)', 'US importer, on a rebuttable presumption', 'If your inputs include material from the affected region, the burden of tracing falls back to you through the contract'],
        ],
        note: 'AES / Electronic Export Information filing is an obligation on exports **from** the United States. For a Turkish exporter it becomes relevant only on returns, replacements or re-exports out of the US.',
      },
    },
    {
      box: {
        kind: 'field',
        title: 'Supply-chain tracing is now a sales requirement',
        body: [
          'US and EU forced-labour and due-diligence rules have made the origin of *inputs* a commercial ' +
          'question, not only a regulatory one. Buyers increasingly ask for a bill of materials with ' +
          'supplier countries before they place an order. An exporter who can answer in a day wins orders ' +
          'from one who needs a month. Build the input-origin record while the order is being quoted, not ' +
          'when the buyer asks.',
        ],
      },
    },

    { h2: 'Russia — compliance-first, and the discipline of stopping' },
    {
      p: 'Russia remains a significant market for Turkish exporters, and it is the destination where an ' +
        'operations desk is most likely to be asked to do something it should refuse. Türkiye does not ' +
        'apply EU or US sanctions as a matter of Turkish law. That fact is frequently misread as meaning ' +
        'the measures are irrelevant to a Turkish company. They are not, for three practical reasons.',
    },
    {
      steps: [
        '**Your banks apply them.** Turkish banks with correspondent relationships in dollars and euros screen against US, EU and UK lists and will refuse or freeze payments. A contract you may lawfully sign is worth nothing if no bank will settle it.',
        '**Your suppliers pass them down.** EU-origin goods are increasingly sold under contractual clauses prohibiting re-export to Russia, with audit and termination rights attached. Breaching such a clause loses the supplier, and in serious cases the supply chain.',
        '**Anti-circumvention measures target intermediaries.** Both the EU and the US have listed companies in third countries, including Türkiye, for facilitating restricted flows. Listing is commercially terminal: banks, insurers and freight forwarders withdraw.',
      ],
    },
    {
      bullets: [
        '**Screen every party, every time** — buyer, consignee, notify party, end user, the vessel and the bank. Listings change constantly and a customer cleared last quarter is not cleared today.',
        '**Classify the goods against dual-use and restricted lists**, including the common high-priority items lists that the EU, US and partners publish for anti-circumvention. If your product appears on one, expect scrutiny even where the sale is lawful.',
        '**Establish and record the end use and end user.** An end-user statement is evidence of diligence, not a substitute for it; treat inconsistent, evasive or unusually urgent answers as a stop signal.',
        '**Expect market-entry requirements to be technical, not just commercial.** Goods placed on the Eurasian Economic Union market generally require conformity to EAEU technical regulations and, where applicable, the EAC mark, with certification through an accredited body. This is separate from anything sanctions-related.',
        '**The customs declarant in Russia is normally a Russian person**, which constrains delivered terms in the same way discussed in §1.2.2.',
      ],
    },
    {
      box: {
        kind: 'warning',
        title: 'Red flags that should stop a Russian-market order at the desk',
        body: [
          {
            bullets: [
              'A new buyer, incorporated recently, ordering goods unrelated to any visible business activity.',
              'A request to route goods through a third country with no commercial logic, or to name a different consignee from the end user.',
              'A willingness to pay a premium well above market, or an insistence on unusual payment channels.',
              'Refusal to provide end-use information, or an end-use statement that does not match the technical specification ordered.',
              'A request to describe the goods on documents in terms that do not match what is being shipped.',
            ],
          },
          'One of these is a question. Two together is an escalation to compliance, in writing, before you quote.',
        ],
      },
    },

    { h2: 'China — classification, registration and inspection' },
    {
      p: 'Türkiye and China trade on most-favoured-nation terms; there is no free trade agreement between ' +
        'them, so there is no preferential origin claim to make and no EUR.1 to issue. The friction in ' +
        'China-bound shipments is not tariff preference but **admissibility**: classification, product ' +
        'registration and inspection.',
    },
    {
      bullets: [
        '**Classification.** China\'s tariff uses codes extending beyond the six-digit international level. A code that is correct in Türkiye can map to more than one Chinese line with different duty, inspection and licensing consequences. Ask your buyer for the Chinese code they will declare and reconcile it with yours before shipment.',
        '**Registration for food and agricultural products.** Chinese customs requires overseas producers of many food categories to be registered before their goods may be imported, with registration numbers appearing on labels and documents. Registration is the manufacturer\'s obligation and takes time; it cannot be arranged around a sailing date.',
        '**Compulsory certification.** Certain product categories require the CCC mark. Where it applies, it applies before importation, and a shipment arriving without it is not a documentary problem but a rejected entry.',
        '**Inspection and quarantine.** Many categories are subject to inspection on entry, with sampling and testing that add time. Build it into the delivery promise rather than discovering it at the port.',
        '**Labelling.** Chinese-language labelling requirements for consumer and food products are specific and enforced. Agree the label artwork with the buyer in writing and keep the approved version in the order file.',
      ],
    },

    { h2: 'A screening routine that works everywhere' },
    {
      p: 'The six sections above differ in detail and are identical in structure. The routine below takes ' +
        'about fifteen minutes on a new counterparty and almost no time on a repeat one, and it is the ' +
        'single highest-return habit in this guide.',
    },
    {
      steps: [
        '**Screen the parties.** Buyer, consignee, notify party, end user, intermediaries, bank, and — for sensitive lanes — the vessel. Record the date, the lists checked and the result.',
        '**Classify the goods.** Tariff code, and separately: is this dual-use, controlled, or on a high-priority watch list? Classification is a technical question; get engineering to confirm rather than guessing from the sales description.',
        '**Establish the destination and the end use.** Where are the goods going, who will use them, and for what? Note any mismatch between the specification ordered and the stated use.',
        '**Check destination admissibility.** Product marking, registration, certification, labelling and inspection requirements for that market and that product.',
        '**Confirm the money path.** Which bank, which currency, which correspondent. A lawful transaction with no settlement route is not a transaction.',
        '**Write the file note.** Three lines: what you checked, what you found, what you decided. This is what protects you and your company if the transaction is ever questioned.',
      ],
    },
    {
      box: {
        kind: 'exercise',
        title: 'Build your country card',
        body: [
          'For the destination you ship to most, write a single page containing: the origin document you ' +
          'issue and why; the product-compliance marks required; the party who acts as importer of record; ' +
          'the licences or registrations that must exist before shipment; the typical clearance time; and ' +
          'the two things that most often delay a shipment on that lane.',
          'Do this for your top five destinations and you will have replaced most of the questions a ' +
          'five-year veteran answers from memory.',
        ],
      },
    },
  ],
};

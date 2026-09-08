'use strict';

module.exports = {
  title: 'Documentation Master Guide',
  abstract: [
    'Every export document answers one question and is rejected for one of three reasons: the wrong party ' +
    'issued it, it does not say what the reader needs it to say, or it contradicts another document in the ' +
    'same set.',
    'This chapter treats documents as instruments rather than forms. For each one: what it proves, who may ' +
    'issue it, what it must contain, and the specific way it fails.',
  ],
  outcomes: [
    'Say what any document in a standard export set actually proves, and to whom.',
    'Distinguish a document of title from a receipt — and price the difference.',
    'Choose correctly between a certificate of origin, an A.TR and a EUR.1.',
    'Build a document set from one data source so that it cannot contradict itself.',
  ],
  blocks: [
    { h2: 'How to think about a document set' },
    {
      lead: 'A document set has three readers, and they want different things. **Customs** wants to know ' +
        'what the goods are, what they are worth and where they came from. **The carrier** wants to know ' +
        'what it received and from whom. **The bank** wants to know whether the papers match the credit.',
    },
    {
      p: 'Almost every documentary failure is a failure to serve one of those three readers while serving ' +
        'another. An invoice written for the bank in the credit\'s exact wording may describe goods in ' +
        'terms customs finds vague; a description written for the tariff may not match the credit. The ' +
        'professional habit is to decide, per shipment, which reader is the binding constraint — and it is ' +
        'the bank whenever a documentary credit is involved, because that reader can withhold money.',
    },
    {
      box: {
        kind: 'definition',
        title: 'The consistency rule',
        body: [
          'Under UCP 600, data in a document must not conflict with data in that document, with any other ' +
          'stipulated document, or with the credit. Note what this does **not** say: documents need not be ' +
          'identical. A bill of lading may describe goods in general terms, provided the description does ' +
          'not contradict the credit. Only the commercial invoice must reproduce the credit\'s description ' +
          'of the goods.',
          'The practical consequence is that the fields which must match exactly across the set are the ' +
          'countable ones — quantities, weights, marks, numbers, seal and container numbers, dates — and ' +
          'these are exactly the fields that get retyped.',
        ],
      },
    },

    { h2: 'The commercial set' },
    { h3: 'Proforma invoice' },
    {
      p: 'A proforma invoice is an offer, not an accounting document. Its function is to be signed. Once ' +
        'countersigned by the buyer it is the cleanest evidence of the agreed terms, and in many markets it ' +
        'is also what the buyer\'s bank needs in order to open a credit and what the buyer\'s customs needs ' +
        'for an import licence.',
    },
    {
      checklist: [
        'Marked clearly as *Proforma Invoice*, with a number and date.',
        'Seller and buyer legal names and addresses as they will appear on every downstream document.',
        'Goods description, HS code, quantity, unit price, total, currency.',
        'Delivery term with named place and the Incoterms edition.',
        'Payment terms in full, including the bank details you will actually use.',
        'Validity, lead time with its trigger, packing and country of origin.',
        'A signature block for the buyer.',
      ],
    },
    { h3: 'Commercial invoice' },
    {
      p: 'The commercial invoice is the value document: it drives customs valuation at both ends, the ' +
        'accounting entry, and the bank\'s examination. In Türkiye it is issued electronically — exports ' +
        'are invoiced through the e-invoice system under the export scenario, and the electronic invoice is ' +
        'matched to the customs declaration. Practically, that means the invoice exists in a government ' +
        'system before it exists in your document set, and correcting it after the fact is a formal ' +
        'process, not an edit.',
    },
    {
      box: {
        kind: 'warning',
        title: 'What must never be quietly adjusted',
        body: [
          'Buyers occasionally ask for an invoice value lower than the contract price — to reduce import ' +
          'duty — or for a description that fits a lower tariff line. This is not a favour with a small ' +
          'risk; it is a false declaration in both countries, it invalidates your insurance, it breaks the ' +
          'match between the invoice and the closed declaration that your VAT refund depends on, and it ' +
          'exposes named individuals. The correct answer is no, and the correct escalation is to your ' +
          'manager and, in writing, to the customer.',
        ],
      },
    },
    { h3: 'Packing list' },
    {
      p: 'The packing list is the reconciliation document: it is what a customs officer at a red line, or a ' +
        'surveyor after damage, uses to check what is physically present against what was declared. It ' +
        'earns its place only if it is granular — package by package, with marks, dimensions, net and gross ' +
        'weight — and if it carries the same container and seal numbers as the transport document.',
    },

    { h2: 'Transport documents' },
    {
      lead: 'The single most consequential distinction in export documentation: some transport documents ' +
        'control delivery of the goods, and some merely record it.',
    },
    {
      table: {
        title: 'Table 3.1 — Transport documents and what they give you',
        head: ['Document', 'Mode', 'Document of title?', 'What this means in practice'],
        widths: [2.4, 1.4, 1.8, 4.8],
        rows: [
          ['Bill of lading (negotiable, to order)', 'Sea', 'Yes', 'Goods are released against surrender of an original. This is what makes CAD and letters of credit work.'],
          ['Straight (consigned) bill of lading', 'Sea', 'No, in substance', 'Named consignee takes delivery on identification. Little payment protection.'],
          ['Sea waybill', 'Sea', 'No', 'Fast and paperless; use only on open account or against advance payment.'],
          ['Air waybill (AWB)', 'Air', 'No', 'Consigned to a named party. To retain control, consign to the bank with its written agreement, never without it.'],
          ['CMR consignment note', 'Road', 'No', 'A receipt and a contract of carriage. Delivery is to the named consignee.'],
          ['TIR carnet', 'Road (transit)', 'No', 'A customs transit and guarantee instrument, not a commercial document.'],
          ['CIM consignment note', 'Rail', 'No', 'As CMR, for rail carriage.'],
          ['Multimodal / FIATA FBL', 'Multimodal', 'Can be, if negotiable', 'Check the form: a FIATA negotiable FBL is a title document; a forwarder\'s certificate of receipt is not.'],
        ],
        note: 'Rule of thumb: if the payment term relies on the buyer needing a piece of paper from you, verify that the transport document is genuinely negotiable before you ship.',
      },
    },
    {
      box: {
        kind: 'field',
        title: 'Reading a bill of lading the way a bank does',
        body: [
          {
            bullets: [
              '**Clean.** No clause declaring a defective condition of goods or packaging. A remark about the condition of the packaging is what makes a bill "claused", and a claused bill under a credit is a discrepancy.',
              '**On board.** A received-for-shipment bill needs an on-board notation with a date; that date is the shipment date.',
              '**Consignee and notify party.** Exactly as the credit says. "To order of [issuing bank]" and "to order" are different.',
              '**Freight prepaid or collect.** Must match the delivery term. A CFR shipment with a "freight collect" bill is an immediate discrepancy.',
              '**Number of originals issued.** Usually three; the credit will say how many must be presented. Surrendering one original releases the goods, so never send a full set unsecured.',
            ],
          },
        ],
      },
    },

    { h2: 'Origin, preference and free circulation' },
    {
      lead: 'This section causes more expensive errors than any other in Turkish export documentation, ' +
        'because three quite different documents are all loosely called "the origin paper".',
    },
    {
      table: {
        title: 'Table 3.2 — Three documents that are not interchangeable',
        head: ['Document', 'What it actually certifies', 'Where it is used', 'Issued / endorsed by'],
        widths: [2.2, 3.6, 2.4, 2.2],
        rows: [
          ['Certificate of origin (*Menşe Şahadetnamesi*)', 'The country in which the goods were produced', 'Non-preferential purposes: import formalities, tenders, letters of credit, some sanctions and quota regimes', 'Chamber of commerce'],
          ['A.TR movement certificate', '**Free circulation status** in the EU–Türkiye Customs Union — not origin', 'Industrial goods moving between Türkiye and the EU', 'Chamber, endorsed by customs'],
          ['EUR.1 / origin declaration', '**Preferential origin** under a specific free trade agreement', 'Türkiye\'s FTA partners, and EU trade in goods outside the Customs Union\'s scope', 'Chamber, endorsed by customs; or the exporter, where approved'],
        ],
        note: 'Verify current coverage and procedure with the Ministry of Trade and your chamber before relying on this table for a specific shipment.',
      },
    },
    {
      box: {
        kind: 'warning',
        title: 'The A.TR trap',
        body: [
          'An A.TR lets goods enter the EU without customs duty because they are in free circulation in the ' +
          'Customs Union. It says nothing about where they were made. Two consequences follow, and both ' +
          'have cost Turkish exporters money.',
          {
            bullets: [
              'An A.TR does **not** exempt goods from trade defence measures — anti-dumping and countervailing duties are applied by origin. Goods of third-country origin, in free circulation in Türkiye, can arrive in the EU duty-free under A.TR and still attract an anti-dumping duty on their true origin.',
              'An A.TR is **not** acceptable as proof of origin where a buyer or a third country asks for origin — for a tender, for onward preferential claims, or for sanctions screening. That requires a certificate of origin or, for preference, a EUR.1.',
            ],
          },
          'When a customer asks for "the origin document", ask what they need it for. The answer changes which document you issue.',
        ],
      },
    },
    {
      p: 'Preferential origin is earned, not asserted. Every free trade agreement contains origin rules — ' +
        'wholly obtained, sufficient transformation, a change of tariff heading, a maximum share of ' +
        'non-originating value — and a claim you cannot support with production records is a claim that ' +
        'will be withdrawn on verification, retroactively, with duty payable by your customer. Keep the ' +
        'supplier declarations and the bill of materials that support each claim, for as long as the ' +
        'agreement requires.',
    },

    { h2: 'Insurance' },
    {
      p: 'Only two Incoterms rules oblige the seller to insure: CIF and CIP. Everywhere else, insurance is a ' +
        'commercial decision about your own exposure between the point where risk passes and the point ' +
        'where you are paid — which are rarely the same point.',
    },
    {
      bullets: [
        '**CIF** requires cover complying at minimum with Institute Cargo Clauses (C) — a restricted, named-perils cover.',
        '**CIP** requires, since the 2020 revision, cover complying at minimum with Institute Cargo Clauses (A) — an all-risks cover.',
        'Under a documentary credit, insurance is typically required for 110 per cent of the CIF or CIP value, in the currency of the credit, and must be issued no later than the shipment date.',
        'An insurance **certificate** issued under an open policy is normally acceptable; a broker\'s cover note usually is not.',
      ],
    },
    {
      box: {
        kind: 'field',
        title: 'Insure to the point of payment, not the point of risk transfer',
        body: [
          'On an FCA sale with sixty-day open-account terms, your risk in the goods ends at the carrier\'s ' +
          'vehicle but your exposure to the transaction ends only when the money arrives. If the cargo is ' +
          'lost in transit and the buyer\'s own insurance disputes the claim, you may find yourself ' +
          'negotiating with a customer who has no goods and no enthusiasm for paying. Contingent or ' +
          'seller\'s-interest cover exists for exactly this gap and is inexpensive.',
        ],
      },
    },

    { h2: 'Regulatory, product and special documents' },
    {
      table: {
        title: 'Table 3.3 — Situational documents and their triggers',
        head: ['Document', 'Triggered by', 'Watch for'],
        widths: [2.8, 3.8, 3.8],
        rows: [
          ['Phytosanitary certificate', 'Plants, plant products, and often wood packaging', 'Issued by the agriculture authority; inspection must precede loading, not follow it'],
          ['Health / veterinary certificate', 'Food of animal origin', 'Destination-specific wording; establishment must be listed by the importing country'],
          ['ISPM 15 marking', 'Solid wood packaging and dunnage', 'Marking on the wood itself; a certificate does not replace the stamp'],
          ['Certificate of analysis / conformity', 'Chemicals, food, technical products', 'Must be issued by the party the contract or credit names'],
          ['Pre-shipment inspection certificate', 'Buyer, destination regime or credit', 'Book the inspection against the loading date; a missed inspection cannot be recovered after sealing'],
          ['Dangerous goods declaration', 'Classified hazardous cargo', 'Correct UN number, packing group and IMDG segregation; booking must be made as hazardous from the start'],
          ['ATA carnet', 'Temporary export: samples, exhibitions, professional equipment', 'Goods must return in the same state and within validity, or duty becomes payable'],
          ['Legalisation / consular attestation', 'Several Middle Eastern and North African markets', 'Chamber attestation, then consulate; allow days, and check whether electronic attestation is accepted'],
        ],
      },
    },

    { h2: 'The consistency matrix' },
    {
      p: 'The single most effective documentary control is not a checklist of documents but a matrix of ' +
        '**fields** — the countable values that must agree wherever they appear. Build it once, per ' +
        'shipment, from one source, and check the finished set against it before anything leaves the office.',
    },
    {
      table: {
        title: 'Table 3.4 — Fields that must agree across the set',
        head: ['Field', 'Invoice', 'Packing list', 'Transport doc', 'Origin doc', 'Credit'],
        widths: [3.2, 1.36, 1.6, 1.6, 1.4, 1.24],
        rows: [
          ['Seller / beneficiary name', '•', '•', '•', '•', '•'],
          ['Buyer / consignee name', '•', '•', '•', '•', '•'],
          ['Goods description', 'exact', 'general', 'general', 'general', 'source'],
          ['Quantity and unit', '•', '•', '•', '•', '•'],
          ['Net and gross weight', '•', '•', '•', '', ''],
          ['Marks and numbers', '•', '•', '•', '', ''],
          ['Container and seal number', '•', '•', '•', '', ''],
          ['Delivery term and named place', '•', '', '', '', '•'],
          ['Country of origin', '•', '', '', '•', '•'],
          ['Invoice number and date', '•', '•', 'often', '•', ''],
        ],
        note: '"Exact" means reproduced from the credit word for word; "general" means consistent but not necessarily identical; "source" means the credit is the origin of the wording.',
      },
    },
    {
      box: {
        kind: 'exercise',
        title: 'Audit your last presentation',
        body: [
          'Take the last document set your company presented under a credit. Fill in Table 3.4 from the ' +
          'actual documents and mark every cell where two documents disagree, however trivially. Then check ' +
          'those cells against the discrepancies the bank raised, if any.',
          'On most desks this exercise finds two or three latent disagreements that were not raised — that ' +
          'time. Those are the discrepancies waiting for a stricter examiner.',
        ],
      },
    },
  ],
};

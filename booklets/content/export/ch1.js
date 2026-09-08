'use strict';

module.exports = {
  title: 'Export Sales Operations',
  abstract: [
    'The export sales desk is where a commercial promise becomes an operational obligation. Everything ' +
    'that later goes wrong in logistics, documentation or payment was, in most cases, decided here — in ' +
    'a quotation written in four minutes, an Incoterm chosen by habit, or an order confirmation that ' +
    'repeated the customer\'s wording instead of the seller\'s.',
    'This chapter follows one order from enquiry to closure and shows, at each step, what an experienced ' +
    'specialist is protecting.',
  ],
  outcomes: [
    'Build a quotation whose price still holds when freight, packing and payment terms are added.',
    'Convert an enquiry into an order confirmation that will survive a dispute.',
    'Run the weekly shipment rhythm without letting a single order fall between departments.',
    'Recognise the four moments in an order cycle where silence is a warning sign.',
  ],
  blocks: [
    { h2: 'What the desk actually owns' },
    {
      lead: 'On paper, export sales receives orders and issues documents. In practice the desk owns a ' +
        'single, unglamorous thing: **the promise date**. Every other department optimises its own ' +
        'constraint. You are the only person whose job is the customer\'s delivery.',
    },
    {
      p: 'That framing decides how you spend your day. Production plans capacity; shipping books space; ' +
        'finance protects cash. None of them is wrong, and none of them is looking at the whole line from ' +
        'purchase order to arrival. When you understand that the desk exists to hold that line, the ' +
        'apparently administrative parts of the role — chasing a proforma signature, confirming a cut-off, ' +
        're-reading a letter of credit — stop looking like paperwork and start looking like what they are: ' +
        'the points where the promise can quietly break.',
    },
    {
      table: {
        title: 'Table 1.1 — The order cycle and what is at stake at each stage',
        head: ['Stage', 'Who leads', 'What can silently go wrong', 'Cost if missed'],
        widths: [2.2, 1.5, 4, 2.3],
        rows: [
          ['Enquiry and quotation', 'Export sales', 'Freight or packing excluded; validity period omitted', 'Margin, or an unwinnable renegotiation'],
          ['Order entry and confirmation', 'Export sales', 'Customer PO terms silently accepted', 'Contractual exposure on delivery and payment'],
          ['Production slotting', 'Planning', 'Order accepted for a week with no capacity', 'Late shipment, penalty, roll-over'],
          ['Freight booking', 'Foreign trade', 'Space booked without matching the ready date', 'Demurrage, detention, missed vessel'],
          ['Documentation', 'Export sales / foreign trade', 'Document set built from the invoice, not the L/C', 'Discrepancy, delayed or lost payment'],
          ['Customs clearance', 'Broker', 'HS code or origin claim unverified', 'Line inspection, fine, retroactive duty at destination'],
          ['Post-shipment', 'Export sales', 'Arrival not tracked; claim window missed', 'Uncovered damage, unrecoverable claim'],
          ['Closure', 'Foreign trade / finance', 'Declaration not closed in the tax system', 'Blocked VAT refund'],
        ],
        note: 'The right-hand column is the one to memorise. It is the argument you will use when you need another department to move.',
      },
    },

    { h2: 'Quotation: the price that has to survive' },
    {
      p: 'A quotation is not a price. It is a price attached to a delivery term, a validity period, a ' +
        'payment method, a packing specification and a lead time — and it is only as strong as its weakest ' +
        'attachment. The most common failure on a junior desk is a number that is correct in isolation and ' +
        'indefensible in context.',
    },
    { h3: 'Build the price in layers' },
    {
      p: 'Work outward from the ex-works cost, and never quote a delivery term whose costs you have not ' +
        'actually listed. The discipline matters more than the arithmetic: it is the listing, not the ' +
        'adding, that catches the omission.',
    },
    {
      steps: [
        '**Ex-works cost.** Goods, export packing, marking and palletising. Export packing is not domestic packing; if your factory quotes domestic, you are already short.',
        '**Inland leg.** Factory to port or border, including loading, waiting time and any escort or permit for out-of-gauge cargo.',
        '**Origin charges.** Terminal handling, documentation fee, seal, VGM, customs brokerage, and the exporters\' association registration fee.',
        '**Main carriage.** Ocean or road freight for the specific equipment type, plus current surcharges — bunker, congestion, war risk, low-sulphur, peak season.',
        '**Destination charges, if your term reaches that far.** Terminal handling at destination, customs clearance, duty and import taxes for DDP.',
        '**Money costs.** Letter of credit confirmation and negotiation fees, forward cover if you are quoting in a currency you do not hold, and the cost of the credit period you are granting.',
        '**Risk margin.** Not padding: a named allowance for the things that have historically gone wrong on this lane.',
      ],
    },
    {
      box: {
        kind: 'warning',
        title: 'The three quotation omissions that cost the most',
        body: [
          {
            bullets: [
              '**No validity period.** A price without an expiry is a price forever. Freight rates on a single lane can move by half in a quarter; a quotation issued in a soft market and accepted in a tight one is a loss you agreed to in writing. State a validity, and state that freight is subject to reconfirmation at booking.',
              '**No packing specification.** "Standard export packing" means whatever the buyer imagines. When the buyer imagines sea-worthy crates and you shipped shrink-wrapped pallets, the damage claim is yours to argue.',
              '**A delivery term chosen to sound generous.** DDP quoted to a market whose import duties and VAT registration rules you have not checked is the single most expensive habit on a junior desk. See §1.2.2.',
            ],
          },
        ],
      },
    },
    { h3: 'Choosing the delivery term, and what each one really costs you' },
    {
      p: 'Incoterms 2020 allocate cost, risk and obligation between seller and buyer. They are not shipping ' +
        'instructions and they are not payment terms, and the most common commercial errors come from ' +
        'treating them as either. Three questions decide the term: **where does my risk end**, **who is ' +
        'better placed to clear customs at each end**, and **whose freight rate is better**.',
    },
    {
      table: {
        title: 'Table 1.2 — Delivery terms from the Turkish seller\'s seat',
        head: ['Term', 'Risk passes', 'What it costs the seller in practice'],
        widths: [1.3, 2.6, 6.1],
        rows: [
          ['EXW', 'At your premises', 'Simplest, and often the wrong answer: you still need the export declaration in your name to obtain the exit record for a VAT refund. Prefer FCA.'],
          ['FCA', 'On delivery to the buyer\'s carrier', 'The safe default for containerised cargo. Export clearance is yours, main carriage is theirs. In FCA the buyer can instruct the carrier to issue an on-board bill of lading to you — useful under a letter of credit.'],
          ['FOB', 'On board the vessel', 'Widely used and widely misused. For containers handed over at a terminal days before loading, FOB leaves you carrying risk you cannot control. Use FCA instead.'],
          ['CFR / CIF', 'On board the vessel; you pay carriage (and, in CIF, insurance)', 'Your cost runs past your risk. CIF requires only Institute Cargo Clauses (C) as a minimum — a narrow cover that surprises buyers who expected all-risks.'],
          ['CPT / CIP', 'On handover to the first carrier; you pay carriage (and, in CIP, insurance)', 'The multimodal equivalents. Note the 2020 change: CIP now requires Institute Cargo Clauses (A) as a minimum, CIF still (C).'],
          ['DAP / DPU', 'At the named destination (DPU: after unloading)', 'You carry the main carriage risk to destination. Import clearance stays with the buyer, which is what keeps this manageable.'],
          ['DDP', 'At destination, cleared for import', 'You accept import duty, import VAT and, in several markets, an obligation you may not legally be able to meet as a non-resident. Quote it only after checking the destination\'s rules.'],
        ],
        note: 'Source: ICC Incoterms® 2020. The rules are a copyright text; buy the current edition and keep it on the desk — a summary table is an aid to memory, not an authority.',
      },
    },
    {
      box: {
        kind: 'field',
        title: 'Why an experienced desk resists DDP',
        body: [
          'DDP moves the import clearance to you, and import clearance is usually reserved to a resident or ' +
          'registered party. In much of the EU a non-established seller cannot act as importer of record ' +
          'without a fiscal representative or a local VAT registration; in the United Kingdom you will need ' +
          'a GB EORI and a route for import VAT; in Russia the customs declarant must generally be a ' +
          'Russian person. The result is that DDP is quoted, accepted, and then delivered as DAP with the ' +
          'seller paying charges through the forwarder — an arrangement with no contractual clarity and no ' +
          'recoverable import VAT.',
          'When a buyer insists on DDP, the professional answer is not refusal. It is: *"We can deliver DAP ' +
          'to your door and quote the duty and import VAT separately as an estimate, or we can quote DDP ' +
          'once we have confirmed we can act as importer of record in your country. Which do you prefer?"* ' +
          'That sentence has saved more margin than any negotiation technique.',
        ],
      },
    },

    { h2: 'Order entry: turning a purchase order into your contract' },
    {
      p: 'The moment a customer purchase order arrives, two documents are in play: theirs and yours. Their ' +
        'PO carries their standard terms — often including delivery penalties, retention, a governing law ' +
        'and a dispute forum you have never read. Your order confirmation, or the proforma invoice you ask ' +
        'them to sign, carries yours. Whichever one is last accepted without objection tends to govern.',
    },
    {
      p: 'This is why an order confirmation is not an acknowledgement. It is a counter-offer, and it must ' +
        'restate every commercial term in your own words rather than referring to theirs.',
    },
    {
      checklist: [
        'Full legal names and addresses of both parties, exactly as they will appear on the customs and banking documents.',
        'Goods description that matches the HS code you intend to declare, and the description the letter of credit will use, if there is one.',
        'Quantity with tolerance (for example ±5 per cent at seller\'s option) where the product is produced to weight or length.',
        'Unit price, total, currency, and the delivery term with a **named place** — "FCA" alone is not a delivery term, "FCA Gebze, Türkiye (Incoterms® 2020)" is.',
        'Payment terms in full: instrument, timing, and which party bears which bank charges.',
        'Lead time expressed from a defined trigger — from receipt of the signed proforma, or from receipt of the advance payment, or from receipt of a workable letter of credit. Never simply "30 days".',
        'Packing and marking specification, including pallet type and any heat-treatment (ISPM 15) requirement.',
        'Documents you will provide, listed, and documents the buyer must obtain themselves.',
        'Any inspection requirement, with the party who pays for it and the consequence of failure.',
        'Force majeure, governing law and dispute resolution.',
      ],
    },
    {
      box: {
        kind: 'warning',
        title: 'The lead-time trigger',
        body: [
          'A lead time that starts "on order" starts before you have money, before you have a workable ' +
          'credit, and often before the customer has finalised the specification. Experienced desks tie the ' +
          'clock to the last thing the *buyer* controls. If the buyer is late with the advance payment or ' +
          'the letter of credit, the delivery date moves with it, automatically and without an argument, ' +
          'because that is what the confirmation says.',
        ],
      },
    },

    { h2: 'The weekly rhythm' },
    {
      p: 'Export desks that run smoothly are not staffed by faster people. They are running a weekly cycle ' +
        'that has been stable long enough that every department knows what is expected of it and when. The ' +
        'shape below is common in Turkish manufacturers shipping containerised cargo to Europe and the ' +
        'Middle East; adjust the days, keep the structure.',
    },
    {
      table: {
        title: 'Table 1.3 — A workable weekly cycle',
        head: ['Day', 'Export sales', 'Foreign trade / logistics'],
        widths: [1.2, 4.4, 4.4],
        rows: [
          ['Monday', 'Confirm ready dates with planning; update customers whose dates moved', 'Collect carrier quotes; check equipment availability for the week'],
          ['Tuesday', 'Issue and chase order confirmations; check L/C expiry and latest shipment dates', 'Place bookings against confirmed ready dates; register container pick-up'],
          ['Wednesday', 'Prepare document sets for the week\'s shipments', 'Confirm inland transport; send loading programme to the factory'],
          ['Thursday', 'Send draft documents to the customer or bank for pre-check', 'Follow loading; obtain VGM; submit customs declaration through the broker'],
          ['Friday', 'Close the week: shipped list, pending list, and the exceptions that need Monday', 'Confirm gate-in against the cut-off; record any roll-over risk'],
        ],
        note: 'The single most valuable habit in this table is the Thursday pre-check of documents against the letter of credit. It converts a rejected presentation into a corrected draft, at no cost.',
      },
    },
    {
      box: {
        kind: 'case',
        title: 'A missed cut-off that was visible on Tuesday',
        body: [
          'A machinery exporter in Konya confirmed a 40\'HC to Antwerp for a Friday vessel. Production ' +
          'signalled on Monday that finishing would slip by a day. The desk noted it, told the customer, ' +
          'and did not tell logistics, because the ready date was still "this week".',
          'The booking had a Wednesday 16:00 documentation cut-off and a Thursday 12:00 gate-in. The unit ' +
          'was ready Thursday afternoon. It missed gate-in by four hours, rolled to the next sailing seven ' +
          'days later, and the customer\'s installation crew — already booked — stood idle.',
          'Nothing here was a logistics failure. The information existed on Monday and did not cross a ' +
          'departmental boundary. This is what the weekly cycle is for: **a ready date that moves is a ' +
          'logistics event, not a sales event**, and it is escalated the same day it is known.',
        ],
      },
    },

    { h2: 'Working with the other departments' },
    { h3: 'Planning and production' },
    {
      p: 'Planning\'s constraint is capacity and changeover; yours is the promise date. The productive ' +
        'question is never "can you make it faster" but "what would have to move for this to ship on the ' +
        'fourteenth, and what does that cost us elsewhere". That question gets an answer because it ' +
        'respects the constraint. Bring the destination and the consequence with you: a unit for a plant ' +
        'shutdown window is genuinely different from stock replenishment, and planning cannot know that ' +
        'unless you say so.',
    },
    { h3: 'Shipping and the customs broker' },
    {
      p: 'Your broker is not a document processor; they are the party who will be standing in front of ' +
        'customs when a line is red. Give them the file complete and early, tell them what is unusual ' +
        'about the shipment before they find it, and never let them learn about a value, an origin claim ' +
        'or a licence requirement from the paperwork alone. A broker who trusts your file will call you ' +
        'when something looks wrong; a broker who has been surprised twice will simply file what you sent.',
    },
    { h3: 'Finance' },
    {
      p: 'Finance owns the money and, in Turkey, the export-proceeds obligations that attach to it. Bring ' +
        'them into the file at quotation, not at invoicing, whenever the payment term is anything other ' +
        'than an advance: a letter of credit with a confirmation requirement, a long credit period, or an ' +
        'unfamiliar currency all have costs that belong in the price.',
    },

    { h2: 'Technical support for customer requirements' },
    {
      p: 'A large share of export enquiries are not commercial questions wearing a commercial costume; ' +
        'they are technical questions the customer cannot resolve locally. Specification confirmations, ' +
        'material certificates, tolerance queries, substitution requests, installation and spare-part ' +
        'questions — these arrive at the sales desk because it is the only address the customer has.',
    },
    {
      p: 'The desk\'s job is not to answer them. It is to route them fast and to translate in both ' +
        'directions, and the difference between a desk that does this well and one that does it badly is ' +
        'visible in the reorder rate.',
    },
    {
      bullets: [
        '**Never answer a technical question from memory.** A confident wrong answer about a tolerance or a material grade becomes a claim, and the claim cites your e-mail.',
        '**Translate the question before forwarding it.** Engineering needs the application, not the customer\'s wording. "Can you supply grade X?" is usually "will this work at this temperature in this medium?" — and the second question gets a useful answer.',
        '**Give a date, not a promise.** "Engineering will answer by Thursday" is worth more to a customer than "soon", and it is a commitment you can keep.',
        '**Record the answer in the customer file.** The same question returns, from the same customer, in a different year, to a different colleague.',
        '**Watch for specification drift.** A customer who repeatedly asks whether a slightly different product would do is telling you their requirement has changed. That is a sales signal, and it is routinely missed.',
      ],
    },
    {
      box: {
        kind: 'field',
        title: 'Documents are technical support too',
        body: [
          'Material certificates, test reports, declarations of conformity and safety data sheets are ' +
          'requested late and needed urgently, because the customer\'s own customs or customer asked for ' +
          'them at the last moment. A desk that keeps the current version of each certificate for its ' +
          'top twenty products in one place answers in ten minutes. A desk that requests them from ' +
          'quality each time answers in two days, and occasionally after the vessel has sailed.',
        ],
      },
    },

    { h2: 'Post-shipment: the part juniors drop' },
    {
      p: 'The shipment leaving the gate feels like completion. It is roughly the midpoint. Four things ' +
        'still have to happen, and three of them have deadlines.',
    },
    {
      steps: [
        '**Documents move.** Originals to the bank or courier to the buyer, on the day of shipment. Under a letter of credit, the presentation period runs from the shipment date and is typically 21 days unless the credit says otherwise — and it always also has to be within the credit\'s expiry.',
        '**Arrival is tracked.** Not because the customer cannot track it, but because you want to know about a delay before they do. A roll-over discovered by your customer is a different conversation from one you reported.',
        '**Receipt is confirmed and inspected.** Damage claims against a carrier have short notice windows; for road carriage under CMR, visible damage must be noted on delivery. If your customer signs clean and complains a week later, the claim is already difficult.',
        '**The file is closed.** The export declaration must be closed in the customs system and visible to the tax administration before a VAT refund can be claimed. This is covered in §2.8; it is mentioned here because the sales desk is usually the one holding the missing document.',
      ],
    },
    {
      box: {
        kind: 'field',
        title: 'Reading silence',
        body: [
          'Four silences mean trouble and should be chased rather than waited out.',
          {
            bullets: [
              '**A carrier that stops confirming.** A booking without a written confirmation of vessel and cut-off is not a booking.',
              '**A customer who goes quiet after receiving draft documents.** They are usually checking with their bank or their own customer, and the answer is often a change you would rather hear now.',
              '**A broker who does not confirm the declaration number.** The declaration may not have been lodged.',
              '**A bank that acknowledges a presentation but does not comment.** Under UCP 600 the issuing bank has a maximum of five banking days following presentation to examine and to give a single notice of refusal; silence approaching that limit is worth a call.',
            ],
          },
        ],
      },
    },
    {
      box: {
        kind: 'exercise',
        title: 'Rebuild a quotation',
        body: [
          'Take a live enquiry from your desk and rebuild the quotation using the seven layers in §1.2.1. ' +
          'Write down every figure you had to guess or ask for. That list is your gap list — it is exactly ' +
          'the knowledge a five-year specialist carries without looking anything up, and it is short enough ' +
          'to close in a month.',
        ],
      },
    },
  ],
};

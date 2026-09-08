'use strict';

module.exports = {
  title: 'Risk Management and Common Pitfalls',
  abstract: [
    'Experienced operators are not people who avoid problems. They are people who recognise a problem ' +
    'early, know roughly what it will cost, and know whether to absorb it or escalate it.',
    'This chapter names the risks an export desk actually carries, gives each one an early signal and a ' +
    'containment move, and ends with the two habits that convert incidents into institutional memory.',
  ],
  outcomes: [
    'Classify a live problem quickly and act on the right axis.',
    'Judge when to absorb a cost and when to escalate it, and justify the judgement.',
    'Run a shipment through a pre-mortem before it goes wrong instead of after.',
    'Write the note that stops the same failure happening to a colleague next quarter.',
  ],
  blocks: [
    { h2: 'A working taxonomy' },
    {
      lead: 'Export risk is usually discussed as a list of bad outcomes. It is more useful as a list of ' +
        '**places where control is handed over**, because that is where the desk can still act.',
    },
    {
      table: {
        title: 'Table 6.1 — Where control is handed over, and what it costs when it fails',
        head: ['Handover', 'Risk that appears', 'Earliest reliable signal'],
        widths: [2.6, 4.2, 4.2],
        rows: [
          ['Quotation accepted', 'Price no longer covers cost; term is unworkable', 'Freight requote at booking differs materially from the quoted figure'],
          ['Order confirmed', 'Buyer\'s terms govern; lead time started too early', 'Buyer references their PO terms in correspondence'],
          ['Production slot given', 'Ready date will not hold', 'Any slip announced by planning, however small'],
          ['Booking placed', 'Roll-over; equipment unavailable', 'Booking confirmation missing vessel name or cut-off'],
          ['Goods handed to carrier', 'Cargo damage; risk has passed but payment has not', 'Driver or terminal raising a condition remark at collection'],
          ['Documents presented', 'Discrepancy; delayed or refused payment', 'Bank acknowledging receipt without comment as day five approaches'],
          ['Goods arrive', 'Refusal to take delivery; demurrage', 'Buyer stops answering after arrival notice'],
          ['File closed', 'Blocked VAT refund; unrecoverable input tax', 'Declaration still open in the system a month after shipment'],
        ],
      },
    },

    { h2: 'Counterparty and payment risk' },
    {
      p: 'The largest single loss an export desk can cause is shipping goods that are never paid for. It is ' +
        'almost never a surprise in retrospect: the warning signs are commercial, and they appear before ' +
        'the shipment.',
    },
    {
      bullets: [
        '**A first order that is unusually large.** Credit is extended on a relationship that does not yet exist. Stage the first order, or take an advance.',
        '**Pressure to ship before the credit is workable.** "Ship now, we will amend the L/C" is a request to give up the protection you priced into the deal.',
        '**Payment terms renegotiated after production has started.** The leverage has moved and the buyer knows it. This is why lead-time triggers matter (§1.3).',
        '**A change of consignee or delivery address late in the cycle.** Sometimes routine; sometimes the first visible sign of a diversion or a party you have not screened.',
        '**Slow acceptance of documents.** A buyer who does not collect documents is a buyer with a cash problem or a market problem.',
      ],
    },
    {
      box: {
        kind: 'field',
        title: 'Match the instrument to the risk, not to the habit',
        body: [
          {
            bullets: [
              '**Advance payment** for new counterparties, small values and difficult jurisdictions.',
              '**Confirmed documentary credit** where you doubt the issuing bank or the country, not the buyer. Confirmation buys you a bank in a jurisdiction you trust.',
              '**Unconfirmed credit** where the bank is strong and the country is stable.',
              '**Documents against payment** only where the transport document is genuinely negotiable (§3.3).',
              '**Open account** for established relationships — ideally with credit insurance, which also gives you a second opinion on the buyer.',
            ],
          },
          'Turkish exporters have access to export credit insurance and financing through Türk Eximbank; where a buyer relationship is growing faster than your comfort, that is the conversation to have with finance rather than a tighter payment term the customer will resist.',
        ],
      },
    },

    { h2: 'Cargo, transport and the claim you did not preserve' },
    {
      p: 'Cargo claims are lost more often through procedure than through cover. Insurers pay when the loss ' +
        'is documented; they decline when the record is silent about when the damage appeared.',
    },
    {
      steps: [
        '**Note damage on delivery.** Under road carriage governed by the CMR convention, apparent damage must be noted at delivery, and there are short deadlines for notice of non-apparent damage. A clean receipt signed by your customer is evidence against you.',
        '**Photograph before, during and after loading.** Container interior, stow, lashing, seal. This costs two minutes and settles most disputes about whether the cargo was stowed properly.',
        '**Preserve the packaging and the goods.** Do not let the consignee dispose of damaged material before a survey; that alone defeats many claims.',
        '**Notify the insurer immediately**, even before the extent is known, and notify the carrier in writing within the time limit in the transport contract.',
        '**Keep the survey report and the repair or replacement costing together** with the original commercial documents. A claim file assembled six weeks later is missing exactly the documents that mattered.',
      ],
    },

    { h2: 'Documentary risk' },
    {
      p: 'Chapter 3 covered how documents work. The risk view is simpler: **the cost of a discrepancy is not ' +
        'the discrepancy fee, it is the delay and the loss of leverage.** Once documents are refused, the ' +
        'buyer can accept them, negotiate on them, or wait — and the goods are usually already at their ' +
        'port.',
    },
    {
      bullets: [
        'Build the set from the credit rather than the order, and do it the day the credit arrives.',
        'Have a colleague check the set against the credit — not the person who prepared it. Cross-checking finds errors that re-reading does not.',
        'Ask the advising bank for an informal pre-check when the value is large. Many will do it, and it is far cheaper than a refusal.',
        'When a discrepancy is unavoidable, tell the buyer before the bank does, and ask for a waiver in advance. A discrepancy the buyer already agreed to waive is an administrative step; one they learn about from their bank is a negotiation.',
      ],
    },

    { h2: 'The human failures that produce most incidents' },
    {
      p: 'The incidents that recur on export desks are rarely exotic. Four patterns account for most of them.',
    },
    {
      table: {
        title: 'Table 6.2 — Four recurring failure patterns',
        head: ['Pattern', 'What it looks like', 'Countermeasure'],
        widths: [2.4, 4.4, 4.2],
        rows: [
          ['Information that does not cross a boundary', 'A date change known in sales on Monday, discovered by logistics on Thursday', 'A standing rule: any date change is communicated the day it is known (§1.4)'],
          ['Data retyped instead of generated', 'Weights and seal numbers keyed separately into three documents', 'One data source per shipment; documents generated, not typed'],
          ['Verbal agreements with carriers and brokers', '"They said they would hold the booking"', 'Written confirmation of vessel, cut-off and free time on every booking'],
          ['Silence treated as agreement', 'No answer from bank, carrier or customer read as "fine"', 'The four silences in §1.6, chased rather than waited out'],
        ],
      },
    },
    {
      box: {
        kind: 'field',
        title: 'Absorb or escalate?',
        body: [
          'Junior specialists escalate too late, then over-correct and escalate everything. Three questions ' +
          'settle it quickly.',
          {
            bullets: [
              '**Is the cost bounded and within my authority?** A courier fee, a day of detention, a small re-work — absorb, record, move on.',
              '**Does the fix require someone else to change a commitment?** A production slot, a credit amendment, a price — escalate, because you cannot deliver it alone.',
              '**Could this become a legal, compliance or reputational matter?** Sanctions, a false declaration, a safety issue, a customer alleging breach — escalate immediately and in writing, regardless of size.',
            ],
          },
          'The third category has no discretion attached to it. Escalating it is not an admission that you ' +
          'could not handle it; not escalating it is the mistake.',
        ],
      },
    },

    { h2: 'Building the desk\'s memory' },
    {
      p: 'Everything in this guide is compressed experience. The reason experience is normally slow to ' +
        'accumulate is that it is stored in individuals and leaves when they do. Two lightweight habits ' +
        'fix that.',
    },
    {
      steps: [
        '**The incident note.** After any shipment that went wrong, write five lines: what happened, when it first became visible, what it cost, what would have caught it earlier, what changed as a result. File them in one place. A year of these is a better training manual than anything bought externally.',
        '**The pre-mortem.** Before a shipment that is unusual — new market, new product, first order with a customer, unusual delivery term — spend ten minutes with the question: *"It is six weeks from now and this went badly. What happened?"* Write the three most likely answers and act on the cheapest one.',
      ],
    },
    {
      box: {
        kind: 'exercise',
        title: 'Run a pre-mortem on your next unusual shipment',
        body: [
          'Take the next order that differs from your routine. Write the three most likely failures, the ' +
          'earliest signal for each, and one preventive action per failure that costs less than an hour. ' +
          'Keep the sheet and review it after the shipment closes.',
          'Over a year this exercise builds the thing this whole guide is trying to transfer: not knowledge ' +
          'of procedures, but a calibrated sense of what usually goes wrong and how early it can be seen.',
        ],
      },
    },
  ],
};

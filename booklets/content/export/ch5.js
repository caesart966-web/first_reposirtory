'use strict';

module.exports = {
  title: 'SAP in Export Operations',
  abstract: [
    'SAP is not a filing cabinet with a login. It is a chain of linked documents in which each step ' +
    'inherits from the last, and almost every export problem attributed to "the system" is in fact a piece ' +
    'of master data that was wrong before the order was created.',
    'This chapter covers what an export desk actually needs: the document flow, the fields that decide ' +
    'whether your customs and banking documents come out right, and the habits that keep the data clean.',
  ],
  outcomes: [
    'Explain the sales document flow and find where a shipment is stuck without asking IT.',
    'Identify the fields that drive the export invoice, the declaration and the shipping documents.',
    'Work with purchasing and warehouse colleagues in their own transactions rather than through e-mail.',
    'Recognise a master-data problem before it becomes a documentary one.',
  ],
  blocks: [
    { h2: 'The document flow is the whole idea' },
    {
      lead: 'In SAP, a sale is not one record. It is a sequence — enquiry, quotation, sales order, ' +
        'delivery, goods issue, billing — in which each document copies from its predecessor. Understanding ' +
        'that copying relationship is the difference between fixing a problem and reporting it.',
    },
    {
      p: 'Two consequences follow immediately. First, **an error corrected downstream does not correct ' +
        'itself upstream**: fixing an address on an invoice does not fix the customer master, and the next ' +
        'order will repeat the error. Second, **a document that has already flowed cannot always be ' +
        'changed** — once goods issue is posted, quantities and dates are largely fixed, and correcting ' +
        'them means reversing rather than editing.',
    },
    {
      table: {
        title: 'Table 5.1 — The export document flow and the usual transactions',
        head: ['Step', 'What it creates', 'Typical transaction', 'What the export desk checks here'],
        widths: [2.2, 2.6, 1.8, 4.4],
        rows: [
          ['Sales order', 'Commercial commitment', 'VA01 / VA02 / VA03', 'Incoterm and named place, payment terms, delivery date, ship-to, plant'],
          ['Delivery', 'Picking and shipping document', 'VL01N / VL02N', 'Picked quantity, batch, packing, shipping point, route'],
          ['Packing / handling units', 'Package structure and weights', 'VL02N / HU transactions', 'Gross and net weight — these become the VGM and the packing list'],
          ['Goods issue', 'Stock movement and the accounting entry', 'VL02N (PGI)', 'Posting date: it drives the shipment date on your documents'],
          ['Billing', 'Commercial invoice', 'VF01 / VF02', 'Value, currency, description, and the export invoice output'],
          ['Foreign trade data', 'Commodity code, origin, procedure', 'Foreign trade tabs / VI-series', 'Data that feeds the customs declaration'],
          ['Freight / transport', 'Freight order or forwarding order', 'TM transactions', 'Carrier, equipment, cut-off dates, freight cost'],
        ],
        note: 'Transaction codes and screen layouts vary with release, activated components and your company\'s configuration. Confirm your own landscape; the sequence is universal even where the codes are not.',
      },
    },
    {
      box: {
        kind: 'field',
        title: 'Where is my shipment? — answering it yourself',
        body: [
          'From the sales order, open the document flow. It shows every subsequent document and its status ' +
          'in one view: whether a delivery exists, whether picking is complete, whether goods issue has ' +
          'been posted, whether billing has run. Ninety per cent of the "where is it?" questions on an ' +
          'export desk are answered there in fifteen seconds, without an e-mail to the warehouse.',
          'The habit to build: **before asking a colleague, look at the flow and ask a narrower question.** ' +
          '"Delivery 80012345 is picked but not goods-issued — is it waiting on the truck or on the ' +
          'inspection?" gets an answer. "Where is my order?" gets a delay.',
        ],
      },
    },

    { h2: 'The fields that decide your documents' },
    {
      p: 'A surprising share of documentary discrepancies are traceable to four data points that were ' +
        'entered once, months earlier, by someone who was not thinking about a letter of credit.',
    },
    {
      bullets: [
        '**Sold-to, ship-to, bill-to and payer.** These are separate partner functions and they print on different documents. A credit that names the applicant\'s head office while the goods go to a plant needs both, correctly assigned — not one address used everywhere.',
        '**Incoterm and its location field.** SAP stores the term and the place separately. A term entered without the location produces documents that say "FCA" with no named place, which is not a delivery term and is a discrepancy waiting to be cited.',
        '**Commodity code and country of origin.** Held on the material master per plant. If they are wrong, they are wrong on the declaration, on the invoice output and on every origin document generated from the system.',
        '**Weights and units of measure.** Net and gross weight on the material master feed the delivery, the packing list and the verified gross mass. A material with a default weight of one kilogram will produce a packing list nobody can reconcile.',
      ],
    },
    {
      box: {
        kind: 'warning',
        title: 'The material master is a document, not a setting',
        body: [
          'On most desks the material master is treated as something technical that somebody else owns. In ' +
          'export it is a documentary source: its description, commodity code, origin, weights and packaging ' +
          'data all print. When you find an error there, do not correct the outgoing document and move on — ' +
          'raise the master-data change, then correct the document. Otherwise you will correct the same ' +
          'document every month.',
        ],
      },
    },

    { h2: 'Working with purchasing and the warehouse' },
    {
      p: 'Two things bring an export specialist into the materials side of the system: inward processing, ' +
        'where imported inputs must be traceable to exported outputs, and stock reality, where the ' +
        'confirmed date depends on whether the material actually exists.',
    },
    {
      bullets: [
        '**Purchase orders and goods receipts** establish the origin and the duty status of inputs. Where an inward processing authorisation is in play, the link between the receipt and the eventual export must be demonstrable; that is a data discipline, not a paperwork one.',
        '**Stock and batch reporting** tells you what is genuinely available, in which plant and in which storage location. Available-to-promise is a calculation, not an observation: understand what your configuration includes before promising against it.',
        '**Movement history** is the fastest way to answer where a batch went and when — invaluable when a customer disputes a quantity or a claim requires you to trace a specific lot.',
      ],
    },

    { h2: 'Transport, and the limits of automation' },
    {
      p: 'Where a transport management component is in use, freight orders and forwarding orders carry ' +
        'carrier, equipment, dates and cost, and can be linked back to the delivery. That gives you two ' +
        'genuine advantages: freight cost lands on the shipment rather than in a monthly lump, and carrier ' +
        'performance becomes measurable by booking rather than by memory.',
    },
    {
      p: 'What it does not give you is the cut-off. Carrier deadlines change after booking, and the system ' +
        'holds what was entered. Treat the transport document as the record of the plan and the carrier\'s ' +
        'written confirmation as the record of the deadline — and reconcile them the day before gate-in.',
    },
    {
      box: {
        kind: 'field',
        title: 'If your company runs a trade compliance component',
        body: [
          'Larger exporters run a dedicated global trade component that screens business partners against ' +
          'sanctions lists, checks licence requirements and blocks documents automatically. When it blocks ' +
          'an order, the correct response is never to find another way to release the shipment. It is to ' +
          'read the block reason, take it to compliance and document the outcome — exactly the routine in ' +
          '§4.8. A screening block that is routinely overridden is worse than no screening at all, because ' +
          'it produces a record showing the company knew.',
        ],
      },
    },

    { h2: 'Reporting without drowning' },
    {
      p: 'Standard reporting will give you far more than you need. Four lists cover the working week on ' +
        'most export desks.',
    },
    {
      table: {
        title: 'Table 5.2 — Four lists worth having ready',
        head: ['List', 'What it answers', 'When to run it'],
        widths: [3, 4.4, 3.6],
        rows: [
          ['Open sales orders by customer and date', 'What have we promised and when', 'Monday, and before any customer call'],
          ['Deliveries due for shipment', 'What must physically move this week', 'Daily'],
          ['Deliveries with goods issue posted but not billed', 'What has shipped without an invoice', 'Daily — this is where documents get forgotten'],
          ['Billing documents with output errors', 'Which invoices failed to transmit', 'Daily; an untransmitted e-invoice is not an invoice'],
        ],
        note: 'Save each as a personal variant with your own selection criteria. The five minutes spent building the variant is repaid in the first week.',
      },
    },
    {
      box: {
        kind: 'exercise',
        title: 'Trace one order end to end',
        body: [
          'Take a shipment that has already been delivered and paid. Open the sales order, walk the ' +
          'document flow to the billing document, and write down which field on which document produced ' +
          'each line of the commercial invoice and the packing list.',
          'You will find at least one field you assumed came from somewhere else. That is the field that ' +
          'will surprise you under a letter of credit.',
        ],
      },
    },
  ],
};

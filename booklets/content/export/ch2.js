'use strict';

module.exports = {
  title: 'Foreign Trade and Logistics Operations',
  abstract: [
    'If export sales owns the promise, foreign trade owns the physics: a box of a particular size has to ' +
    'be at a particular gate before a particular hour, with a declaration lodged, a weight verified and a ' +
    'document set that a bank in another country will accept without comment.',
    'This chapter is organised around the clock, because almost every operational failure in export ' +
    'logistics is a timing failure wearing a different costume.',
  ],
  outcomes: [
    'Turn a production plan into a loading programme that carriers can actually book against.',
    'Read a freight quotation and know which parts are negotiable and which are not.',
    'Manage cut-off, ETD and ETA as one chain rather than three separate facts.',
    'Prepare a letter of credit presentation that does not come back.',
    'Close an export file so that the VAT refund is not blocked six months later.',
  ],
  blocks: [
    { h2: 'The loading programme' },
    {
      lead: 'The loading programme is the single document that connects production output to booked ' +
        'transport capacity. Where it is missing, its absence is filled by phone calls, and phone calls do ' +
        'not survive an audit or a Monday morning.',
    },
    {
      p: 'A workable programme is built backwards from the vessel or the truck, not forwards from the ' +
        'factory. Take the sailing you intend to catch, subtract the documentation cut-off, subtract the ' +
        'gate-in deadline, subtract the inland transit, subtract the loading and lashing time, and you have ' +
        'the hour at which the goods must be finished, packed and weighed. That hour — not the vessel date — ' +
        'is what production needs from you.',
    },
    {
      table: {
        title: 'Table 2.1 — Working backwards from a Friday sailing (typical container export, Marmara to North Europe)',
        head: ['Milestone', 'Timing', 'Owner', 'Failure consequence'],
        widths: [3, 2, 2, 3.6],
        rows: [
          ['Vessel ETD', 'Friday', 'Carrier', '—'],
          ['Port gate-in (container in terminal)', 'Thursday, typically 24–48 h before ETD', 'Inland carrier', 'Roll-over to next sailing'],
          ['Documentation cut-off (shipping instructions, VGM)', 'Wednesday, often earlier than gate-in', 'Foreign trade', 'No bill of lading on the intended vessel'],
          ['Customs declaration lodged and closed', 'Wednesday', 'Broker', 'Container cannot enter the terminal'],
          ['Container loaded and sealed at the factory', 'Tuesday–Wednesday', 'Shipping / factory', 'Inland transit compressed, overtime cost'],
          ['Container collected from the depot', 'Tuesday', 'Inland carrier', 'Empty not available; loading date slips'],
          ['Goods finished, packed, weighed, marked', 'Monday–Tuesday', 'Production', 'Everything downstream moves'],
        ],
        note: 'Transit times and cut-offs vary by port, carrier and season. Build this table once for each lane you use regularly and keep it current; it is the most useful single page on a foreign trade desk.',
      },
    },
    {
      box: {
        kind: 'warning',
        title: 'Documentation cut-off is usually earlier than gate-in',
        body: [
          'Juniors plan to the gate-in because it is physical and easy to picture. Carriers, however, close ' +
          'the documentation window first — shipping instructions and verified gross mass have to be in the ' +
          'system before the manifest is built. A container that is physically inside the terminal but ' +
          'missing its VGM does not sail. Track both deadlines separately on every booking.',
        ],
      },
    },

    { h2: 'Freight: how the number is built' },
    {
      p: 'A freight quotation looks like one price and is in fact a stack of separate charges with ' +
        'different owners, different volatility and very different negotiability. Reading the stack is what ' +
        'allows you to argue about the right line.',
    },
    {
      table: {
        title: 'Table 2.2 — Anatomy of an ocean freight quotation',
        head: ['Component', 'What it is', 'How negotiable'],
        widths: [2.8, 5, 2.8],
        rows: [
          ['Ocean freight (base)', 'Port-to-port carriage for the equipment type', 'Negotiable, and the main lever on volume lanes'],
          ['BAF / bunker or low-sulphur surcharge', 'Fuel cost pass-through', 'Rarely negotiable line by line; negotiate the all-in instead'],
          ['THC origin and destination', 'Terminal handling at each end', 'Tariffed by the terminal; who *pays* it is negotiable, the amount usually is not'],
          ['Documentation / bill of lading fee', 'Issuing the transport document', 'Small, but check for duplicates when a forwarder is in the chain'],
          ['Seal, VGM, ISPS, congestion, peak season', 'Fixed and situational surcharges', 'Ask for them to be listed at quotation, not added at invoice'],
          ['Inland haulage (merchant or carrier haulage)', 'Factory to port', 'Compare both: carrier haulage is simpler, merchant haulage is often cheaper and always more controllable'],
          ['Free time (demurrage / detention)', 'Days allowed before penalties start', 'The most under-negotiated line on the sheet'],
        ],
        note: 'Demurrage runs on the container inside the terminal; detention runs on the container outside it. Confusing them is a common and expensive error.',
      },
    },
    {
      box: {
        kind: 'field',
        title: 'Negotiate free time before you negotiate rate',
        body: [
          'On a lane where your customer is slow to clear, five extra free days at destination are worth ' +
          'more than a rate reduction, and they cost the carrier less to give. A forwarder who will not move ' +
          'on rate will very often move on free time, because it does not touch their published tariff.',
          'Always ask for the free-time figure **in writing on the booking confirmation**. "Standard free ' +
          'time" means whatever the destination agent decides when the invoice is issued.',
        ],
      },
    },
    { h3: 'Equipment: choosing the box' },
    {
      p: 'Equipment choice is a volume-versus-weight decision, and the constraint is almost never the ' +
        'container. It is the road: axle and gross-weight limits on the inland leg routinely bind before ' +
        'the container\'s own payload does, and the limit that matters is the one in the country where the ' +
        'truck drives.',
    },
    {
      table: {
        title: 'Table 2.3 — Standard equipment, indicative figures',
        head: ['Type', 'Internal capacity (approx.)', 'Typical use'],
        widths: [1.6, 3.4, 5.6],
        rows: [
          ['20\'DC', 'about 33 m³', 'Dense cargo: stone, machinery, chemicals in drums. Volume is rarely the limit; weight is.'],
          ['40\'DC', 'about 67 m³', 'General cargo where weight per m³ is moderate.'],
          ['40\'HC', 'about 76 m³', 'The default for light, bulky cargo — extra height, same footprint.'],
          ['45\'HC', 'about 86 m³', 'Where the carrier and the road permit it; check inland legality before quoting.'],
          ['Reefer', 'Reduced by insulation and machinery', 'Temperature-controlled; requires set-point, ventilation and pre-trip inspection on the booking.'],
          ['Open top / flat rack', 'Out-of-gauge', 'Requires dimensions, weight distribution and, usually, an out-of-gauge surcharge quoted in advance.'],
        ],
        note: 'Capacities and payloads differ by owner and container age. Confirm the payload of the specific unit with the carrier before you plan a heavy load; never plan to a table.',
      },
    },
    {
      box: {
        kind: 'case',
        title: 'The 20\' that could not leave the yard',
        body: [
          'A marble exporter loaded 26 tonnes into a 20\'DC — comfortably inside the container\'s payload ' +
          'and comfortably outside the road weight limit for the tractor-trailer combination taking it to ' +
          'the port. The unit was refused at the weighbridge, returned to the factory, stripped, and split ' +
          'across two boxes. The cost was two days, one missed sailing and a second set of handling charges.',
          'The lesson is not about marble. It is that **the container payload and the legal road weight are ' +
          'two different limits, and the smaller one governs.** Ask for the road limit on the specific ' +
          'route, in writing, before you plan a heavy load.',
        ],
      },
    },

    { h2: 'Inland transport and port organisation' },
    {
      p: 'Under merchant haulage you control the inland leg and therefore own its failures. That is usually ' +
        'the right trade: you can choose the depot, sequence the collection and speak to the driver. Three ' +
        'habits separate a controlled inland leg from a hopeful one.',
    },
    {
      steps: [
        '**Book the empty against the loading slot, not the sailing.** Depots run out of the specific type you need, and a 40\'HC promised on Tuesday is not a 40\'HC standing in your yard on Tuesday.',
        '**Inspect the empty before loading.** Holes, previous cargo residue, a floor that fails a light test, a missing CSC plate — all are yours to reject at the gate and impossible to argue after loading. Photograph the interior and the container number.',
        '**Seal, photograph, record.** The seal number goes on the packing list, the bill of lading instruction and the declaration. A seal number that does not match across the three is a documentary discrepancy and, at destination, a customs question.',
      ],
    },
    {
      box: {
        kind: 'field',
        title: 'Verified gross mass, and who is liable',
        body: [
          'Since the 2016 amendment to SOLAS chapter VI, a packed container may not be loaded on a ship ' +
          'without a verified gross mass declared by the shipper. Two methods are permitted: weighing the ' +
          'packed container, or weighing the cargo and adding the certified tare. The obligation sits with ' +
          'the party named as shipper on the bill of lading — which, in an FCA or FOB sale, is very often ' +
          'you rather than your buyer. Confirm who is submitting the VGM at booking, every time.',
        ],
      },
    },

    { h2: 'The clock: cut-off, ETD, ETA and roll-over' },
    {
      p: 'These four words describe one chain, and treating them as separate facts is what produces the ' +
        'characteristic junior surprise: a shipment that was "on track" until the day it was not.',
    },
    {
      bullets: [
        '**Cut-off** is a set of deadlines, not one: documentation cut-off, VGM cut-off, gate-in cut-off, and sometimes a separate cut-off for hazardous or reefer cargo. Record all of them on the booking.',
        '**ETD** is an estimate that carriers revise. A vessel that slips by a day at origin does not usually recover it, and a slip announced late in the week is often a sign that the vessel is already full.',
        '**ETA** is an estimate compounded by transhipment. On a routing with one transhipment, ask which leg is the constraint; the connection, not the ocean, is where time is lost.',
        '**Roll-over** is the carrier moving your container to a later sailing, usually because the vessel is overbooked. It is not a breach of anything. Your protection is early gate-in, a named booking reference confirmed in writing, and — on critical shipments — a written request for loading confirmation once the vessel has sailed.',
      ],
    },
    {
      box: {
        kind: 'warning',
        title: 'Tell the customer before the system does',
        body: [
          'Modern buyers track containers themselves. A roll-over your customer discovers on a tracking ' +
          'portal costs you credibility that a roll-over you report does not. The rule on an experienced ' +
          'desk is simple: **any date change reaches the customer the same working day it reaches you**, ' +
          'with the new date and the recovery plan in the same message.',
        ],
      },
    },

    { h2: 'Customs: the declaration and the line' },
    {
      p: 'In Türkiye the export declaration (*gümrük çıkış beyannamesi*) is lodged electronically by the ' +
        'customs broker acting under your authority. Once lodged, the system assigns an inspection line, ' +
        'and the line determines how long the shipment takes and what can still go wrong.',
    },
    {
      table: {
        title: 'Table 2.4 — Inspection lines and what they mean on the day',
        head: ['Line', 'What happens', 'What the desk should do'],
        widths: [1.6, 4.4, 4.6],
        rows: [
          ['Green (*yeşil*)', 'No documentary or physical check; the declaration proceeds', 'Nothing — but keep the file complete; post-clearance audit still applies'],
          ['Yellow (*sarı*)', 'Documentary check by the customs officer', 'Have the invoice, packing list, licences and any origin document immediately available in the exact form declared'],
          ['Red (*kırmızı*)', 'Documentary and physical examination of the goods', 'Expect a day; make sure someone can attend, and that the goods are physically accessible and marked as declared'],
          ['Blue (*mavi*)', 'Cleared now, examined afterwards under post-clearance control', 'Archive the complete file; this is the line where a weak file surfaces months later'],
        ],
        note: 'Line assignment is risk-based and not disclosed in advance. Consistency between what you declare and what you ship is the only thing you control — and it is what the risk system measures.',
      },
    },
    {
      p: 'Three declaration fields cause most of the trouble, and all three are decided by the export sales ' +
        'desk long before the broker sees the file: **the commodity code**, **the declared value**, and ' +
        '**the origin claim**. Chapter 3 treats each as a document problem; here it is enough to say that ' +
        'the broker cannot verify any of them for you. They file what you assert.',
    },
    {
      box: {
        kind: 'field',
        title: 'Authorised operator status changes the calculus',
        body: [
          'Türkiye operates an authorised operator regime — *Yetkilendirilmiş Yükümlü Sertifikası* (YYS), ' +
          'the Turkish AEO — which brings simplified procedures, fewer physical examinations and, in ' +
          'particular, the ability to complete formalities at the exporter\'s own premises. If your company ' +
          'ships regular volume and does not hold it, the business case is usually strong and the ' +
          'application is largely an exercise in documenting the processes this chapter describes. Confirm ' +
          'the current requirements with the Ministry of Trade before building a case.',
        ],
      },
    },

    { h2: 'Payment operations: letters of credit and documents against payment' },
    {
      p: 'Two instruments dominate Turkish export practice outside open account: the documentary credit ' +
        '(letter of credit) and documentary collection, usually cash against documents. They protect you to ' +
        'very different degrees, and they fail in very different ways.',
    },
    { h3: 'The documentary credit' },
    {
      p: 'A credit is a bank\'s undertaking to pay against **documents that comply with the credit** — not ' +
        'against goods, and not against performance. This single sentence, from UCP 600, explains every ' +
        'behaviour that frustrates newcomers: banks deal in documents alone, and a perfect shipment ' +
        'documented imperfectly does not get paid on time.',
    },
    {
      steps: [
        '**Check the credit the day it arrives, not the week you ship.** Read it as a list of things you must produce. Anything you cannot produce is an amendment request, and amendments take days you will not have later.',
        '**Check the dates as a set:** latest shipment date, presentation period, and expiry. A credit expiring at the counters of the issuing bank abroad means your documents must arrive there before expiry, not leave Türkiye before it.',
        '**Check the description of goods.** It must be reproduced on the commercial invoice; other documents may describe the goods in general terms, but they must not contradict.',
        '**Check who issues each document and what it must state.** "Certificate of origin issued by the Chamber of Commerce" and "certificate of origin" are different requirements.',
        '**Present early.** A presentation made with days to spare can be corrected once; a presentation made on the last day cannot.',
      ],
    },
    {
      table: {
        title: 'Table 2.5 — Discrepancies most often cited on Turkish presentations',
        head: ['Discrepancy', 'Why it happens', 'Prevention'],
        widths: [3, 4, 3.6],
        rows: [
          ['Late presentation', 'Documents assembled after shipment rather than before', 'Build the set from the credit before the goods are ready'],
          ['Credit expired', 'Expiry read as a shipment deadline', 'Diarise expiry, latest shipment and presentation period separately'],
          ['Goods description differs from the credit', 'Invoice copied from the sales order', 'Copy the description from the credit, character for character'],
          ['Documents inconsistent with each other', 'Weight, marks or seal number retyped per document', 'Generate all documents from one data set; never retype'],
          ['Bill of lading not marked as required', '"Clean on board", freight prepaid, notify party omitted', 'Send the draft B/L to the carrier with the credit\'s wording quoted'],
          ['Insurance below the required percentage or wrong currency', 'Policy issued to standard terms', 'Instruct the insurer with the credit text, typically 110 per cent of CIF value in the credit currency'],
          ['Missing signature, stamp or legalisation', 'Requirement buried in the credit\'s additional conditions', 'Read the additional conditions field last and again'],
        ],
        note: 'Under UCP 600 the issuing bank has a maximum of five banking days following the day of presentation to determine compliance, and any refusal must be given in a single notice stating each discrepancy.',
      },
    },
    { h3: 'Documents against payment' },
    {
      p: 'In a documentary collection the banks act as couriers with instructions, not as guarantors. Your ' +
        'protection is control of the transport document: with a negotiable bill of lading consigned to ' +
        'order, the buyer cannot take delivery without the originals the bank holds. That protection ' +
        'evaporates on a straight consigned air waybill or a road consignment note, where the named ' +
        'consignee can collect the goods without any document from you at all.',
    },
    {
      box: {
        kind: 'warning',
        title: 'CAD by truck to a nearby market is weaker than it looks',
        body: [
          'A CMR consignment note is not a document of title. If you ship on CAD terms by road, consigned ' +
          'directly to the buyer, the goods will be delivered on arrival whether or not the buyer has paid ' +
          'the collecting bank. Where you cannot ship to order, either take an advance payment or accept ' +
          'that you are, in substance, on open account and price accordingly.',
        ],
      },
    },

    { h2: 'Closing the file' },
    {
      p: 'An export is not finished when the goods arrive. In Türkiye it is finished when the declaration is ' +
        'closed, the proceeds are handled as the regulations require, and the VAT position is settled. This ' +
        'is where the foreign trade desk earns its keep quietly, and where neglected files turn into ' +
        'blocked refunds months later.',
    },
    {
      steps: [
        '**Confirm the declaration is closed.** The customs system records the exit of the goods; the closed declaration is what the tax administration will look for. An open declaration is the single most common cause of a stalled refund.',
        '**Collect and archive the closed declaration and the transport document** with the invoice and the exporters\' association registration. Archive retention periods are set by customs and tax legislation; keep the file whole rather than scattered across departments.',
        '**Handle the proceeds according to the current export circular.** Türkiye has, since 2018, operated an obligation to repatriate export proceeds within a set period, with a share to be sold to the Central Bank. Both the period and the percentage have changed repeatedly. Never work from memory here — check the current *İhracat Genelgesi* with finance for each period.',
        '**Submit the VAT refund file.** Exports are exempt with credit, so input VAT is recoverable. Depending on the amount and the method chosen, refunds may require a certified public accountant\'s report or a guarantee. Finance owns the submission; you own the completeness of the underlying documents.',
      ],
    },
    {
      box: {
        kind: 'warning',
        title: 'Three things that block a refund months later',
        body: [
          {
            bullets: [
              'A declaration that was never closed because the goods left under a different declaration number after a re-loading.',
              'An invoice whose value or quantity does not match the closed declaration after a post-shipment credit note.',
              'A missing exporters\' association registration on a declaration that was lodged in a hurry.',
            ],
          },
          'All three are cheap to fix in the week they happen and expensive to reconstruct in the quarter they surface.',
        ],
      },
    },

    { h2: 'Monthly reporting' },
    {
      p: 'A monthly operations report exists to change decisions. If it does not change a carrier ' +
        'allocation, a lane, a term or a customer conversation, it is a ritual. Five measures are enough ' +
        'for most manufacturers.',
    },
    {
      table: {
        title: 'Table 2.6 — A five-measure operations report',
        head: ['Measure', 'Definition', 'The decision it should drive'],
        widths: [2.6, 4, 4],
        rows: [
          ['Shipped tonnage and volume', 'By lane and by equipment type', 'Where to seek a contract rate rather than spot'],
          ['Freight cost per tonne and per unit', 'All-in, including surcharges and inland', 'Whether the delivery term you quote still makes sense'],
          ['On-time gate-in', 'Containers gated in before cut-off, as a share of bookings', 'Which internal step is causing roll-overs'],
          ['Carrier reliability', 'Sailed as booked, without roll-over, by carrier', 'Allocation for the next quarter'],
          ['Documentary rejection rate', 'Presentations returned by banks, with reason', 'Which document to redesign, and who to retrain'],
        ],
        note: 'Report the rejection rate by *reason*, not as a total. A single recurring reason is a process fix; a scatter of one-off reasons is a training issue.',
      },
    },
    {
      box: {
        kind: 'exercise',
        title: 'Build your lane sheet',
        body: [
          'Pick the lane you ship most often. On one page, record: the carriers you use, the documentation ' +
          'and gate-in cut-offs, the transit time, the free time at both ends, the inland transit, and the ' +
          'last three roll-overs with their causes. Keep it current for one quarter.',
          'That page will answer more daily questions than any system you have access to, and it is the ' +
          'artefact that most clearly distinguishes an experienced desk from a busy one.',
        ],
      },
    },
  ],
};

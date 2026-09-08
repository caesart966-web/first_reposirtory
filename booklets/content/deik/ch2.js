'use strict';

module.exports = {
  title: 'International Trade Architecture',
  abstract: [
    'Trade rules are usually taught as a legal system. They are more usefully understood as a bargain ' +
    'about power: states accept constraints on what they may do to foreign goods in exchange for the same ' +
    'constraint on others, and the interesting questions are always about who is constrained, who is ' +
    'not, and what happens when the enforcement mechanism weakens.',
    'This chapter covers the architecture a specialist must be able to navigate — the multilateral system, ' +
    'the preferential agreements that matter to Türkiye, the remedies that reshape specific markets, and ' +
    'the control regimes that increasingly sit alongside them.',
  ],
  outcomes: [
    'Explain the WTO\'s core disciplines and the practical consequences of the dispute settlement impasse.',
    'Describe Türkiye\'s preferential architecture, including the structural asymmetry in the Customs Union.',
    'Recognise a trade remedy case early and understand what an affected exporter can actually do.',
    'Place sanctions and export controls within the trade system rather than outside it.',
  ],
  blocks: [
    { h2: 'What the rules are for' },
    {
      lead: 'The multilateral trading system exists because bilateral trade bargaining has a bad ' +
        'equilibrium. Without common rules, each state has an incentive to protect its own producers, and ' +
        'the result is worse for everyone than the cooperative outcome — a structure familiar from any ' +
        'account of collective action.',
    },
    {
      p: 'Three disciplines carry most of the weight. **Most-favoured-nation treatment** requires that an ' +
        'advantage given to one member be given to all, which is what stops the system fragmenting into ' +
        'bilateral deals. **National treatment** requires that imported goods, once inside, be treated no ' +
        'less favourably than domestic ones, which is what stops tariff concessions being undone by ' +
        'internal regulation. **Binding** commits members to ceiling tariff rates they cannot exceed ' +
        'without compensation.[^The Marrakesh Agreement Establishing the World Trade Organization (1994) ' +
        'and the GATT 1994, particularly Articles I, II and III. Texts are published by the WTO.]',
    },
    {
      p: 'Preferential agreements are the recognised exception to the first discipline, permitted where ' +
        'they liberalise substantially all trade between the parties. That exception has grown until it ' +
        'is arguably the main event, which is why an economic diplomat spends far more time on ' +
        'preferential architecture than on multilateral rounds.',
    },

    { h2: 'The WTO, and the strain it is under' },
    {
      p: 'The WTO does three things: it holds the rulebook, it provides a forum for negotiation, and it ' +
        'adjudicates disputes. The first function remains intact, the second has largely stalled since the ' +
        'Doha round, and the third is impaired in a way that has direct consequences for exporters.',
    },
    {
      box: {
        kind: 'definition',
        title: 'The Appellate Body impasse, and why an exporter should care',
        body: [
          'WTO dispute settlement was designed as a two-stage process: a panel, then an appeal to a standing ' +
          'Appellate Body. Since December 2019 the Appellate Body has lacked the quorum to hear appeals, ' +
          'because appointments to it have been blocked. A losing party can therefore appeal a panel report ' +
          '"into the void", suspending the dispute indefinitely.[^On the functioning of dispute settlement, ' +
          'see the Understanding on Rules and Procedures Governing the Settlement of Disputes (DSU), and ' +
          'the WTO\'s own documentation on the current status of appointments. Members have also ' +
          'established an interim appeal arbitration arrangement under DSU Article 25 among participating ' +
          'members.]',
          'The practical consequence for a Turkish exporter facing a measure they believe is inconsistent ' +
          'with WTO rules: the legal route is slower and less certain than it was, and the negotiated and ' +
          'political routes — which is where a business council operates — have become correspondingly ' +
          'more important. This is not a technicality. It is a change in where leverage lives.',
        ],
      },
    },

    { h2: 'Türkiye\'s preferential architecture' },
    {
      p: 'Türkiye\'s trade relationships sit on several layers, and a specialist must be able to say which ' +
        'layer governs a given flow. Getting this wrong produces confident advice that is simply ' +
        'inapplicable.',
    },
    {
      table: {
        title: 'Table 2.1 — Layers of Turkish trade relations',
        head: ['Layer', 'What it covers', 'What a specialist must remember'],
        widths: [2.4, 3.8, 3.8],
        rows: [
          ['EU–Türkiye Customs Union', 'Industrial goods and processed agricultural products in free circulation', 'Duty-free movement, common external tariff for covered goods — but not a proof of origin, and agriculture and services largely outside'],
          ['Free trade agreements', 'Bilateral preferential access with a range of partners, including the United Kingdom', 'Preference must be claimed on **origin**, under the specific rules of each agreement'],
          ['WTO most-favoured-nation terms', 'Everything else, including large partners with no agreement', 'The default; the applicable rate is the MFN rate of the importing country'],
          ['Unilateral schemes', 'Preferences granted by or to developing countries', 'Conditional and revocable; verify current eligibility before relying on it'],
          ['Regional cooperation bodies', 'Political and technical cooperation frameworks such as the OIC, ECO, D-8 and BSEC', 'Valuable for convening and networks; generally not sources of enforceable market access'],
        ],
        note: 'Confirm the current status of any agreement with the Ministry of Trade before relying on it in advice to a member company.',
      },
    },
    {
      box: {
        kind: 'field',
        title: 'The asymmetry problem, and how to explain it in one minute',
        body: [
          'Under the Customs Union, Türkiye aligns its external tariff for covered goods with the EU\'s. ' +
          'When the EU concludes a free trade agreement with a third country, that country\'s goods can ' +
          'therefore enter Türkiye on the EU\'s preferential terms — while Turkish goods do not ' +
          'automatically gain reciprocal access to that country, because Türkiye is not a party to the ' +
          'agreement.',
          'The consequence is a standing incentive for Türkiye to negotiate parallel agreements, and a ' +
          'standing negotiating point in its relationship with the EU. This is one of the few structural ' +
          'features of Turkish trade policy that a specialist should be able to explain without notes: it ' +
          'comes up in almost every serious conversation about the Customs Union\'s modernisation.',
        ],
      },
    },

    { h2: 'Trade remedies: where policy meets a specific exporter' },
    {
      p: 'Trade remedies are the instruments through which a general trade regime becomes a very specific ' +
        'problem for one sector. Three exist, and they answer different questions.',
    },
    {
      table: {
        title: 'Table 2.2 — Three remedies and what triggers them',
        head: ['Instrument', 'The allegation', 'What must be shown', 'Typical duration'],
        widths: [2.2, 2.8, 3.4, 1.6],
        rows: [
          ['Anti-dumping duty', 'Goods sold for export below normal value', 'Dumping, injury to the domestic industry, and a causal link', 'Five years, reviewable'],
          ['Countervailing duty', 'Goods benefit from an actionable subsidy', 'Subsidy, injury, causation', 'Five years, reviewable'],
          ['Safeguard measure', 'Imports have surged, whether or not unfairly', 'Increased imports, serious injury, causation — and compensation may be owed', 'Time-limited, degressive'],
        ],
        note: 'The governing texts are the Anti-Dumping Agreement, the Agreement on Subsidies and Countervailing Measures, and the Agreement on Safeguards.',
      },
    },
    {
      box: {
        kind: 'case',
        title: 'What an exporter can actually do when an investigation opens',
        body: [
          'A remedy investigation is an administrative proceeding with deadlines, and the most common ' +
          'failure of exporters caught in one is **non-participation**. An exporter who does not respond ' +
          'to the questionnaire is assessed on "facts available", which in practice means the highest ' +
          'plausible margin.',
          {
            bullets: [
              '**Register and respond.** Individual margins are calculated for cooperating exporters; non-cooperating ones receive the residual rate.',
              '**Get the sectoral association involved early.** Industry-wide submissions carry weight that individual ones do not, and this is precisely the coordination role a business council or exporters\' association is built for.',
              '**Understand the injury argument, not only the dumping one.** Many cases are winnable on causation — the domestic industry\'s difficulties may have another explanation — and that argument requires data the industry, not the lawyer, holds.',
              '**Watch the review clock.** Measures expire unless renewed on review; an expiry review is a second opportunity, and it is frequently missed.',
            ],
          },
          'The institutional lesson for a specialist: when a remedy case opens against a Turkish sector, ' +
          'the value your organisation adds is *coordination and information*, delivered in the first two ' +
          'weeks. After the deadlines pass there is very little anyone can do.',
        ],
      },
    },

    { h2: 'Sanctions and export controls as part of the architecture' },
    {
      p: 'Sanctions were once treated as an exception to trade policy. They are now a permanent feature of ' +
        'it, and any specialist working Türkiye\'s bilateral relationships must be able to reason about ' +
        'them without either alarm or naivety.',
    },
    {
      bullets: [
        '**Different regimes bind different people.** United Nations measures bind all members. European Union measures bind EU persons and EU-connected conduct. United States measures bind US persons — and, through dollar clearing and secondary designations, reach much further in practice.',
        '**Export controls are separate from sanctions** and often more important commercially. Dual-use control lists restrict goods by technical specification regardless of destination politics, and a company can be entirely outside any sanctions regime and still require a licence.',
        '**Enforcement increasingly targets intermediaries.** Anti-circumvention measures have made third-country trading companies a focus of attention, with commercial consequences — loss of banking, insurance and forwarding relationships — that arrive long before any legal finding.',
        '**Türkiye applies UN measures as a matter of law and is not bound by autonomous EU or US measures** — but Turkish banks and companies operating internationally are exposed to them through counterparties, correspondents and contracts. The distinction between what is legally required and what is commercially unavoidable is one a specialist must be able to draw precisely.',
      ],
    },
    {
      box: {
        kind: 'warning',
        title: 'The institutional line',
        body: [
          'An organisation that convenes businesses will occasionally be asked, directly or obliquely, to ' +
          'facilitate a transaction that is restricted somewhere. The professional answer is to explain ' +
          'the regime accurately, point the company to specialist legal advice, and decline to be part of ' +
          'a structure whose purpose is to obscure a prohibited flow. Institutional reputation is the ' +
          'principal asset of a private-sector diplomacy body, and it is not recoverable.',
        ],
      },
    },

    { h2: 'Services, digital trade and where the agenda is moving' },
    {
      p: 'Goods trade is the subject of most of the architecture and a shrinking share of the value. Three ' +
        'areas are where the substantive negotiation now happens, and where a specialist who is fluent ' +
        'will be unusually useful.',
    },
    {
      bullets: [
        '**Services.** Governed multilaterally by the GATS, and liberalised far less than goods. Barriers are regulatory rather than tariff-based — licensing, qualification recognition, establishment requirements — which makes them harder to negotiate and much harder to measure.',
        '**Digital trade.** Data flows, data localisation, source-code requirements and the treatment of electronic transmissions. Plurilateral work has advanced further than multilateral, and the outcomes will matter more to Turkish services exporters than most tariff lines.',
        '**Trade and climate.** Carbon border measures, deforestation-linked import rules and product-level environmental requirements now function as market access conditions. For Türkiye, with its export concentration in the EU and in emissions-intensive sectors, this is arguably the single most consequential development in the trade architecture for the coming decade.',
      ],
    },
    {
      box: {
        kind: 'exercise',
        title: 'Map a live trade policy position',
        body: [
          'Choose a current trade dispute or measure affecting a Turkish export sector. In two pages: ' +
          'identify the measure and its legal basis; identify the Turkish interest and which companies ' +
          'hold it; state the arguments available on each side; and set out three options for a ' +
          'private-sector body, with the trade-offs of each.',
          'Note where you had to guess. Those gaps are the ones to close with the sources in Appendix A ' +
          'before anyone reads your work.',
        ],
      },
    },
  ],
};

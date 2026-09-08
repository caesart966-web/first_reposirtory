'use strict';

module.exports = [
  {
    title: 'Key Data Sources and Databases',
    blocks: [
      {
        p: 'This appendix is the single most practically useful page in the guide. Every figure you ' +
          'publish should come from one of these, with an extraction date recorded.',
      },
      {
        table: {
          title: 'Table A.1 — Sources by question',
          head: ['Question', 'Source', 'Note'],
          widths: [3, 3.2, 3.8],
          rows: [
            ['Turkish macro and trade statistics', 'Turkish Statistical Institute (TurkStat / TÜİK)', 'The primary source for Turkish national accounts, trade and prices'],
            ['Turkish monetary, balance of payments, FDI', 'Central Bank of the Republic of Türkiye (TCMB)', 'Balance of payments and investment position statistics'],
            ['Turkish trade policy, agreements, procedures', 'Ministry of Trade (Ticaret Bakanlığı)', 'Authoritative on agreements, regimes and export procedure'],
            ['Turkish sector export performance', 'Turkish Exporters Assembly (TİM) and sectoral associations', 'Monthly export figures by sector, ahead of official statistics'],
            ['Bilateral trade at commodity-code level', 'UN Comtrade', 'The reference database for detailed bilateral flows'],
            ['Market analysis and tariffs for exporters', 'ITC Trade Map and Market Access Map', 'The most usable tools for identifying opportunity at product level'],
            ['Investment flows and policy', 'UNCTAD, World Investment Report and UNCTADstat', 'The standard reference for FDI'],
            ['Macro forecasts and country assessment', 'IMF World Economic Outlook; Article IV consultations', 'Article IV reports are the most rigorous public assessment of most economies'],
            ['Direction of trade', 'IMF Direction of Trade Statistics', 'Useful for mirror analysis'],
            ['Structural and policy analysis', 'OECD Economic Surveys; World Bank country diagnostics', 'Slower cadence, deeper analysis'],
            ['Trade measures, disputes, notifications', 'WTO', 'Dispute records, notifications, tariff profiles'],
            ['Value-added trade', 'OECD–WTO trade in value added statistics', 'For value-chain position rather than gross flows'],
            ['Governance and fragility', 'Fund for Peace Fragile States Index; Bertelsmann Transformation Index', 'Use sub-indicators, not composite ranks'],
            ['Turkish policy research', 'TEPAV, SETA and Turkish university research centres', 'Useful framing of domestic policy debates'],
            ['International affairs analysis', 'Chatham House, Bruegel, Wilson Center and comparable institutes', 'Argument, not surveillance — read as such'],
          ],
          note: 'Two cautions. First, several once-standard rankings have been discontinued or replaced; check that a flagship still exists before citing it. Second, databases are revised: always record the extraction date.',
        },
      },
    ],
  },
  {
    title: 'Recommended Reading',
    blocks: [
      { h2: 'If you read only five things' },
      {
        bullets: [
          'Krugman, Obstfeld and Melitz, *International Economics: Theory and Policy* — the trade chapters, for the models you will use for the rest of your career.',
          'Rodrik, *The Globalization Paradox* — for the political limits of economic integration, which is the subject of most current trade politics.',
          'Putnam, "Diplomacy and Domestic Politics: The Logic of Two-Level Games" — twenty pages that explain most negotiations you will observe.',
          'Heuer, *Psychology of Intelligence Analysis* — for the cognitive traps in Chapter 5, written more honestly than any policy text.',
          'The most recent IMF Article IV consultation for a country in your portfolio — read as a model of calibrated institutional writing, not only for its content.',
        ],
      },
      { h2: 'Then, by theme' },
      {
        bullets: [
          '**Trade and value chains:** Baldwin, *The Great Convergence*; Gereffi, Humphrey and Sturgeon on value-chain governance.',
          '**Economic statecraft:** Hirschman, *National Power and the Structure of Foreign Trade*; Farrell and Newman on weaponized interdependence; Drezner, *The Sanctions Paradox*.',
          '**International relations theory:** Waltz, *Theory of International Politics*; Keohane and Nye, *Power and Interdependence*; Wendt, *Social Theory of International Politics*.',
          '**International organisations:** Barnett and Finnemore, *Rules for the World*.',
          '**Economic diplomacy as a practice:** Bayne and Woolcock, *The New Economic Diplomacy*.',
          '**Competitiveness:** Porter, *The Competitive Advantage of Nations* — for the diamond framework and its proper scope.',
          '**Judgement and forecasting:** Tetlock and Gardner, *Superforecasting*.',
        ],
      },
    ],
  },
  {
    title: 'Glossary',
    blocks: [
      {
        table: {
          title: 'Table C.1 — Trade and diplomatic terms used in this guide',
          head: ['Term', 'Meaning'],
          widths: [2.6, 7.4],
          rows: [
            ['A.TR', 'Certificate evidencing free circulation status in the EU–Türkiye Customs Union. Not a proof of origin.'],
            ['Anti-dumping duty', 'A duty imposed where imported goods are sold below normal value and cause injury to a domestic industry.'],
            ['Article IV consultation', 'The IMF\'s periodic assessment of a member economy; a benchmark of calibrated institutional analysis.'],
            ['Business council', 'A bilateral body organising private-sector relations between two economies, usually constituted with a counterpart organisation.'],
            ['Chatham House Rule', 'A convention permitting use of information from a meeting without attributing it to any speaker or their affiliation.'],
            ['Comparative advantage', 'The principle that gains from trade arise from differences in opportunity cost, not absolute productivity.'],
            ['Customs union', 'An arrangement removing internal duties and applying a common external tariff.'],
            ['Economic statecraft', 'The use of economic instruments — trade, finance, investment, controls — for political ends.'],
            ['EUR.1', 'Movement certificate evidencing preferential origin under a free trade agreement.'],
            ['Global value chain', 'The sequence of production stages for a good, distributed across countries.'],
            ['Gravity model', 'The empirical regularity that bilateral trade rises with economic size and falls with distance.'],
            ['Intra-industry trade', 'Two-way trade in similar products between similar economies.'],
            ['Mirror statistics', 'Comparison of one country\'s recorded exports with the partner\'s recorded imports.'],
            ['Most-favoured-nation (MFN)', 'The obligation to extend to all WTO members any advantage granted to one.'],
            ['National treatment', 'The obligation to treat imported goods no less favourably than domestic goods once inside the market.'],
            ['Political economy analysis', 'Analysis of who holds power, how they benefit, and what would make reform in their interest.'],
            ['Safeguard measure', 'A temporary restriction in response to a surge in imports causing serious injury.'],
            ['Stakeholder map', 'A structured assessment of who influences an outcome, their disposition, and the route to reach them.'],
            ['Trade in value added', 'Statistics attributing trade to where value was created rather than where goods crossed borders.'],
            ['Two-level game', 'Negotiation understood as simultaneous bargaining at international and domestic levels.'],
          ],
        },
      },
    ],
  },
  {
    title: 'The Business Council Map: How to Read It',
    blocks: [
      {
        p: 'A current, authoritative list of business councils, their chairs and their counterpart ' +
          'organisations is published by the institution itself and changes as agreements are concluded. ' +
          'This appendix therefore does not reproduce a list that would be wrong within months. It gives ' +
          'you something more durable: how to read the map, and what to ask of it.',
      },
      { h2: 'The structure' },
      {
        bullets: [
          '**Country councils** are the main unit: one per partner country, constituted with a counterpart organisation, chaired by a business figure and supported by a coordinator.',
          '**Special purpose and sectoral councils** cut across geography — addressing a function or an industry rather than a country.',
          '**Regional groupings** organise country councils for coordination; they are administrative rather than constitutional, and they change.',
        ],
      },
      { h2: 'Questions to ask of any council before working with it' },
      {
        checklist: [
          'Who is the counterpart organisation, and does it actually convene business in that market?',
          'When was the cooperation agreement signed, and when did the two sides last meet formally?',
          'How many member companies are active — trading now, not registered?',
          'Which sectors dominate the membership, and does that match where the trade opportunity is?',
          'What obstacles has the council raised with government in the last two years, and what happened?',
          'Is there a follow-up register from the last joint meeting, and was it reviewed?',
        ],
      },
      {
        box: {
          kind: 'field',
          title: 'The most useful thing you can build in your first month',
          body: [
            'For your own portfolio, build a one-page card per council: counterpart organisation and its ' +
            'contact; chair; date of last joint meeting; ten most active member companies and what they ' +
            'trade; the two obstacles currently on the table; and the next scheduled engagement.',
            'This is the artefact that turns a new specialist into a useful one. It takes a week to build, ' +
            'it answers most incoming questions immediately, and it is the institutional memory that ' +
            '§4.4 identified as the difference between an effective council and a busy one.',
          ],
        },
      },
    ],
  },
];

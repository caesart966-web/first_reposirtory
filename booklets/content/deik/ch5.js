'use strict';

module.exports = {
  title: 'Country and Regional Research Methodology',
  abstract: [
    'This chapter and the next are the skills core of the guide. Everything before them is the knowledge ' +
    'an economic diplomat needs; these two are the craft an economic diplomat is paid for.',
    'Country research is a discipline with a method. Done well, it produces a defensible judgement in a ' +
    'known amount of time. Done badly, it produces a document that reads like a country\'s own tourism ' +
    'brochure with a trade table appended.',
  ],
  outcomes: [
    'Convert a vague request into a research question that can be answered in the time available.',
    'Navigate the source hierarchy and know which source settles which kind of question.',
    'Read trade data at commodity-code level and extract a commercial opportunity from it.',
    'Conduct an elite interview that produces information you could not have found in a database.',
    'Name the analytical traps you are personally most likely to fall into.',
  ],
  blocks: [
    { h2: 'Start with the question, not the country' },
    {
      lead: 'The commonest failure in country research is starting to read. A request arrives — "we need ' +
        'something on Vietnam" — and the analyst opens twelve tabs. Three days later there is a great deal ' +
        'of material and no answer, because there was never a question.',
    },
    {
      p: 'Distinguish two kinds of request, because they need different work and different documents.',
    },
    {
      table: {
        title: 'Table 5.1 — Strategic and operational research',
        head: ['', 'Strategic', 'Operational'],
        widths: [2, 4, 4],
        rows: [
          ['Question', 'Should we be in this market at all, and in what form?', 'How do we do this specific thing here?'],
          ['Time horizon', 'Three to ten years', 'Weeks to months'],
          ['Typical trigger', 'Portfolio review; a proposal to establish a council', 'A member company with a concrete problem'],
          ['Evidence', 'Structural: demography, growth, institutions, value chains', 'Procedural: regulation, certification, tariffs, logistics, partners'],
          ['Failure mode', 'A thesis with no test attached', 'Accurate detail that answers a question nobody asked'],
        ],
      },
    },
    {
      box: {
        kind: 'field',
        title: 'The scoping conversation',
        body: [
          'Before any research, five questions to whoever commissioned it. They take four minutes and save ' +
          'days.',
          {
            bullets: [
              '**What decision will this inform?**',
              '**Who will read it, and what do they already know?**',
              '**When do you need it, and in what form?**',
              '**What would make this useless?** — the most revealing of the five.',
              '**What do you already believe?** — so you can test it rather than accidentally confirm it.',
            ],
          },
        ],
      },
    },

    { h2: 'The source hierarchy' },
    {
      p: 'Sources are not equal, and the skill is knowing which source settles which question. Working ' +
        'down this hierarchy, each level is more specific and less verifiable than the one above.',
    },
    {
      table: {
        title: 'Table 5.2 — What each source layer is good for',
        head: ['Layer', 'Examples', 'Settles', 'Does not settle'],
        widths: [2, 3.2, 2.6, 2.2],
        rows: [
          ['Official statistics', 'TurkStat, national statistical offices, central banks', 'What was measured, on a defined basis', 'Anything unrecorded or informal'],
          ['International databases', 'UN Comtrade, ITC Trade Map, UNCTADstat, IMF WEO and DOTS, World Bank data', 'Comparable cross-country figures; mirror statistics', 'Why the numbers moved'],
          ['Institutional assessments', 'IMF Article IV, OECD Economic Surveys, World Bank diagnostics', 'Considered judgement on macro and structural conditions', 'Sector-level commercial specifics'],
          ['Commercial intelligence', 'Subscription forecasting and country-risk services', 'Forecasts, sector data, standardised risk scores', 'Anything proprietary to your own members'],
          ['Ground intelligence', 'Commercial counsellors, member companies, counterpart organisations, local chambers', 'How things actually work; who decides; what the real obstacle is', 'Anything requiring representativeness'],
        ],
        note: 'The last layer is the one an institution like a business council can supply and a consultancy generally cannot. It is your comparative advantage; use it.',
      },
    },
    {
      box: {
        kind: 'definition',
        title: 'Mirror statistics',
        body: [
          'Country A\'s recorded exports to country B rarely equal country B\'s recorded imports from ' +
          'country A. Differences arise from valuation (exports recorded free on board, imports including ' +
          'cost, insurance and freight), timing, re-exports through third countries, and misreporting.',
          'Comparing the two — mirror analysis — is a standard technique. A large and persistent gap is ' +
          'itself a finding: it may indicate transit trade through a third country, informal flows, or ' +
          'undervaluation at one end. Any of those is more interesting than the headline figure.',
        ],
      },
    },

    { h2: 'Reading trade data properly' },
    {
      p: 'Trade data is where an economic diplomat can most quickly produce something a member company ' +
        'values. The technique is not complicated; the discipline is in staying at the right level of ' +
        'detail.',
    },
    {
      steps: [
        '**Work at commodity-code level, not sector level.** "Machinery" is not a finding. A specific four- or six-digit heading, with volumes and suppliers, is.',
        '**Establish what the market imports and from whom.** The supplier concentration tells you whether an incumbent must be displaced or whether the market is genuinely open.',
        '**Check what Türkiye already exports to comparable markets.** A product that sells well in three similar economies and not in this one poses a specific question: is the obstacle tariff, regulatory, logistical or relational?',
        '**Look at the tariff and the non-tariff conditions together.** A zero tariff with a certification requirement your members cannot meet is a closed market.',
        '**Compare unit values.** Your export unit value against competitors\' tells you which quality tier you occupy — and whether the competition you actually face is the one you assume.',
        '**Then, and only then, ask a company.** Data identifies the question; practitioners answer it. Arriving at a member with a specific observation earns a far better conversation than arriving with a blank page.',
      ],
    },
    {
      box: {
        kind: 'warning',
        title: 'What trade data cannot tell you',
        body: [
          {
            bullets: [
              '**Services and digital trade are badly captured.** Large and growing flows are close to invisible in customs statistics.',
              '**Re-exports distort bilateral pictures.** Goods routed through a logistics hub are attributed to the hub, not the origin or the destination.',
              '**Recorded trade excludes informal trade**, which in some neighbouring markets is a substantial share of the real relationship.',
              '**Last year\'s data describes last year.** In fast-moving markets it can be a poor guide to current conditions, and it is always worth asking a practitioner whether the picture still holds.',
            ],
          },
        ],
      },
    },

    { h2: 'Qualitative method: interviews that are worth the meeting' },
    {
      p: 'An elite interview — with an official, an executive, a counterpart organisation — is the only ' +
        'way to obtain information about how decisions are actually made. It is also the easiest research ' +
        'method to waste, because a badly prepared interview simply confirms what the interviewee says in ' +
        'public.',
    },
    {
      bullets: [
        '**Do the desk work first.** Never spend an interview on facts available in a database; you will not be given a second meeting.',
        '**Ask about process and experience, not opinion.** "What happens when a foreign company applies for that licence?" produces information. "What do you think about foreign investment?" produces a position.',
        '**Ask for the exception.** "When does that not apply?" is the single most productive question in this kind of interview.',
        '**Note what they will not discuss.** The boundary of the conversation is data about the environment.',
        '**Establish the ground rules at the start.** Whether remarks may be attributed, and to whom the note will circulate. Where a meeting is convened under the Chatham House Rule, information may be used but neither the identity nor the affiliation of speakers may be revealed.',
        '**Write the note the same day.** Recall degrades faster than anyone expects, and an interview note written a week later is a summary of your impressions rather than a record.',
      ],
    },

    { h2: 'Analytical traps' },
    {
      p: 'The literature on intelligence analysis is more honest about cognitive failure than most policy ' +
        'writing, and it is directly applicable.[^Richards J. Heuer Jr., *Psychology of Intelligence ' +
        'Analysis*, Center for the Study of Intelligence, 1999.] Four traps account for most avoidable ' +
        'errors in country work.',
    },
    {
      table: {
        title: 'Table 5.3 — Four traps and their countermeasures',
        head: ['Trap', 'How it shows up in country research', 'Countermeasure'],
        widths: [2.2, 4.4, 3.4],
        rows: [
          ['Mirror-imaging', 'Assuming a foreign government will weigh costs as a Turkish one would', 'Reconstruct their constraints explicitly before predicting their behaviour'],
          ['Recency bias', 'The last event dominates the assessment; a single incident becomes a trend', 'Plot the series before interpreting the latest point'],
          ['Source conflation', 'Three articles citing one original source are treated as three sources', 'Trace every claim to its origin; count originals, not repetitions'],
          ['Over-reliance on official data', 'Treating published figures as reality in low-transparency environments', 'Triangulate with mirror statistics, satellite or logistics proxies, and practitioner accounts'],
        ],
        note: 'A fifth trap deserves naming: **confirmation of the commissioner\'s view**. If your conclusion always matches what the person who asked for the work already believed, that is a finding about your process.',
      },
    },

    { h2: 'A three-day country profile' },
    {
      p: 'Most country work is done under time pressure. The sequence below produces a defensible ' +
        'four-page profile in three working days and is the single most useful routine to internalise ' +
        'early.',
    },
    {
      table: {
        title: 'Table 5.4 — Three-day sequence',
        head: ['Day', 'Work', 'Output at the end of the day'],
        widths: [1.2, 5.2, 3.6],
        rows: [
          ['Day 1', 'Scoping conversation; macro picture from institutional assessments; structure of the economy; political and institutional context', 'A one-page outline and a written statement of the question'],
          ['Day 2', 'Trade and investment data at commodity-code level; tariff and non-tariff conditions; competitor analysis; identification of two or three candidate opportunities', 'Data annex and a draft of the opportunity section'],
          ['Day 3', 'Two or three calls with practitioners to test the candidate opportunities; drafting; internal review', 'Four-page profile with sourced figures and a clear recommendation'],
        ],
        note: 'If the third day has no conversation with a practitioner in it, the profile is desk research and should be labelled as such.',
      },
    },
    {
      box: {
        kind: 'exercise',
        title: 'Produce a four-page country economic profile',
        body: [
          'Take a priority market and produce a four-page profile using only real, cited data: ' +
          'macroeconomic context; trade structure with Türkiye at commodity-code level; two specific ' +
          'opportunities with the evidence for each; the principal risks; and a recommendation on what a ' +
          'business council should do next.',
          'Constraints that make this exercise worth doing: every figure carries a source and a date; no ' +
          'sentence survives that would be true of any country; and the recommendation must be capable of ' +
          'being wrong.',
        ],
      },
    },
  ],
};

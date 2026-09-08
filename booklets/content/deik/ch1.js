'use strict';

module.exports = {
  title: 'Understanding the Global Economy',
  abstract: [
    'An economic diplomat does not need to be an economist. They need to be able to read an economy the ' +
    'way a doctor reads a chart: knowing which indicators are vital signs, which are symptoms, and which ' +
    'are noise — and knowing what a given reading implies for a bilateral trade relationship.',
    'This chapter builds that reading capacity, first through the theory that explains why countries trade ' +
    'at all, then through the Turkish structure a specialist must be able to describe from memory, and ' +
    'finally through the indicators that appear in every brief you will ever write.',
  ],
  outcomes: [
    'Explain, in one paragraph and without jargon, why two countries trade and who gains.',
    'Describe the structure of the Turkish economy to a foreign counterpart in five minutes.',
    'Read a set of macroeconomic indicators and say what they imply for bilateral trade.',
    'Recognise where the standard trade models stop explaining what you observe.',
  ],
  blocks: [
    { h2: 'Why this matters before the operational detail' },
    {
      lead: 'A business council exists to increase trade and investment between two economies. Every ' +
        'activity it runs — a delegation, a forum, a sectoral working group — is an implicit bet about ' +
        'where complementarity exists. Getting that bet right is an economic judgement before it is a ' +
        'diplomatic one.',
    },
    {
      p: 'The specialists who add most value are those who can look at two economies and say where the ' +
        'genuine complementarity lies, rather than where the political relationship is currently warm. ' +
        'Those are different questions, and confusing them produces the characteristic failure of ' +
        'private-sector diplomacy: a well-attended forum in a market where the underlying trade logic was ' +
        'never there, followed by two years of unanswered follow-up.',
    },

    { h2: 'The theory you actually use' },
    { h3: 'Comparative advantage, and its limits' },
    {
      p: 'The Ricardian insight remains the foundation: countries gain from trade by specialising where ' +
        'their **opportunity cost** is lowest, not where they are absolutely most productive. The ' +
        'Heckscher–Ohlin extension explains specialisation by relative factor endowments — capital, ' +
        'labour, land — and predicts that trade will change the returns to those factors within each ' +
        'country, which is where the political economy of trade begins.[^Paul Krugman, Maurice Obstfeld ' +
        'and Marc Melitz, *International Economics: Theory and Policy*, Pearson, latest edition. Chapters ' +
        'on Ricardian trade and the Heckscher–Ohlin model.]',
    },
    {
      p: 'Two limits matter for your work. First, comparative advantage explains the *pattern* of trade, ' +
        'not its *volume* with any specific partner; gravity considerations — economic size and distance — ' +
        'explain far more of the variation in bilateral flows. Second, the theory says nothing about who ' +
        'within a country gains, and a trade relationship that is welfare-improving in aggregate can be ' +
        'politically unsustainable if the losses are concentrated.',
    },
    { h3: 'New trade theory and why similar countries trade' },
    {
      p: 'Classical theory predicts trade between *different* economies. What we observe is that the ' +
        'largest flows run between *similar* ones, and much of it is intra-industry: Türkiye exports ' +
        'vehicles to Germany and imports vehicles from Germany. Economies of scale, product ' +
        'differentiation and consumer preference for variety explain this better than factor endowments ' +
        'do.[^Krugman\'s work on increasing returns and monopolistic competition in trade, developed ' +
        'through the 1980s and summarised in the same textbook.]',
    },
    {
      box: {
        kind: 'field',
        title: 'What this means at a business council meeting',
        body: [
          'If you are working a market whose economic structure resembles Türkiye\'s, do not expect the ' +
          'opportunity to be in broad sectors — it will be in *segments*: a specific component, a quality ' +
          'tier, a niche where scale or specialisation gives one side an edge. The useful question to a ' +
          'member company is therefore not "do you export machinery to this country?" but "which of your ' +
          'lines has no local equivalent there, and why?"',
        ],
      },
    },
    { h3: 'Global value chains: the frame that fits current reality' },
    {
      p: 'Most manufactured goods are no longer produced in one country. They are assembled from stages ' +
        'located wherever each stage is cheapest to perform, and the analytically interesting question ' +
        'becomes not *what* a country exports but *which stage* it occupies and how much value it ' +
        'captures there.[^Gary Gereffi, John Humphrey and Timothy Sturgeon, "The governance of global ' +
        'value chains", *Review of International Political Economy*, 12(1), 2005. See also Richard ' +
        'Baldwin, *The Great Convergence*, Harvard University Press, 2016.]',
    },
    {
      p: 'For a specialist working Türkiye\'s bilateral relationships, the value-chain frame reorganises ' +
        'the whole analysis. It explains why gross bilateral trade figures overstate the real economic ' +
        'relationship; why a tariff on an intermediate good taxes your own exporters; and why "moving up ' +
        'the value chain" is a specific, measurable ambition rather than a slogan.',
    },
    {
      box: {
        kind: 'definition',
        title: 'Gross trade versus value added',
        body: [
          'Conventional trade statistics record the full customs value of a good each time it crosses a ' +
          'border, so a component crossing three borders before final assembly is counted three times. ' +
          'Trade-in-value-added statistics attempt to strip this out and attribute value to where it was ' +
          'actually created.',
          'The practical consequence: a bilateral deficit measured in gross terms can look very different ' +
          'measured in value-added terms, and the difference is often the most interesting sentence in a ' +
          'bilateral brief. The OECD–WTO trade in value added database is the standard source.',
        ],
      },
    },

    { h2: 'The Turkish economy: what a specialist knows without looking up' },
    {
      p: 'You will be asked to describe Türkiye\'s economy by foreign counterparts, in five minutes, ' +
        'without notes, several times a year. The description below is a structure, not a script; fill it ' +
        'with current figures from the sources in Appendix A each time you use it.',
    },
    {
      table: {
        title: 'Table 1.1 — A five-minute structure for describing the Turkish economy',
        head: ['Dimension', 'What to establish', 'Where the current figure comes from'],
        widths: [2.4, 4.6, 3],
        rows: [
          ['Scale and position', 'Size of the economy, population, income level, position among G20 members', 'TurkStat; IMF World Economic Outlook'],
          ['Structure', 'Shares of agriculture, industry and services; the weight of manufacturing relative to peers', 'TurkStat national accounts'],
          ['Trade composition', 'Leading export sectors and leading import categories, and how they differ', 'TurkStat; UN Comtrade; ITC Trade Map'],
          ['Geography of trade', 'Concentration of exports in the EU, and the diversification into neighbouring and distant regions', 'TurkStat; IMF Direction of Trade Statistics'],
          ['External balance', 'Current account position and its structural driver — energy import dependence', 'Central Bank of the Republic of Türkiye (TCMB)'],
          ['Investment', 'Inbound FDI stock and flows by origin; outbound investment as a growing feature', 'TCMB; UNCTAD World Investment Report'],
          ['Monetary and price context', 'Inflation, policy rate, exchange rate regime and recent direction', 'TCMB; TurkStat'],
          ['External financing', 'Sovereign ratings, external debt profile, reserve position', 'Rating agencies; TCMB'],
        ],
        note: 'Never present any of these from memory. The structure is memorised; the numbers are looked up the day you present them.',
      },
    },
    {
      box: {
        kind: 'field',
        title: 'The two structural facts that explain most of the rest',
        body: [
          'If a counterpart has time for only two sentences about the Turkish economy, these are the two ' +
          'that carry the most explanatory weight.',
          {
            bullets: [
              '**Türkiye is a manufacturing economy embedded in European value chains, with a customs union giving industrial goods duty-free access to the EU market.** This shapes the export basket, the investment pattern and much of the regulatory agenda.',
              '**Türkiye is a substantial net importer of energy.** This is the structural driver of the current account, which is why the external balance moves with global energy prices largely independently of domestic policy.',
            ],
          },
          'Almost every other feature of the economy is easier to explain once these two are on the table.',
        ],
      },
    },

    { h2: 'Reading indicators like an analyst' },
    {
      p: 'Indicators are not facts about an economy; they are measurements with definitions, revisions and ' +
        'blind spots. Knowing the definition is what allows you to say something more useful than the ' +
        'number itself.',
    },
    {
      table: {
        title: 'Table 1.2 — Indicators, what they miss, and the question they should prompt',
        head: ['Indicator', 'What it does not tell you', 'The analytical question'],
        widths: [2.2, 4.2, 3.6],
        rows: [
          ['GDP growth', 'Distribution, composition, or whether growth is credit-financed', 'What is driving it, and is the driver repeatable?'],
          ['Trade balance', 'Value added, or the direction of the underlying competitiveness', 'Which sectors moved, and was it price or volume?'],
          ['Current account', 'Whether the deficit is financed by stable or volatile flows', 'How is it funded, and how quickly could that funding stop?'],
          ['CPI inflation', 'Relative price movements; the experience of different income groups', 'Is this a supply shock, a demand shock or exchange-rate pass-through?'],
          ['Exchange rate', 'Competitiveness, without adjusting for relative prices', 'What has the *real effective* rate done?'],
          ['FDI inflows', 'Whether investment is greenfield or a change of ownership', 'Does this add capacity, or only change who owns it?'],
          ['Sovereign rating', 'Anything the market did not already know', 'What changed in the rationale, not the letter?'],
          ['Unemployment', 'Participation, informality, or underemployment', 'What happened to the participation rate at the same time?'],
        ],
      },
    },
    {
      box: {
        kind: 'warning',
        title: 'Three errors that mark out a junior analyst',
        body: [
          {
            bullets: [
              '**Comparing a nominal series across time or countries** without adjusting for prices or exchange rates. A doubling in lira terms may be a decline in real terms.',
              '**Treating a bilateral trade balance as a measure of the health of a relationship.** It measures composition and value-chain position, not friendship or fairness.',
              '**Quoting a growth rate without the base.** Growth from a collapsed base is a recovery, not a performance, and counterparts will know the difference.',
            ],
          },
        ],
      },
    },

    { h2: 'Cycles, shocks and what they do to bilateral trade' },
    {
      p: 'Trade relationships are not equally sensitive to the economic cycle. Capital goods, construction ' +
        'materials and durable consumer goods swing hard; food, pharmaceuticals and basic intermediates ' +
        'swing much less. A business council whose member base is concentrated in the first group will ' +
        'find its agenda dominated by the cycle whether or not anyone plans it that way.',
    },
    {
      p: 'Three propagation channels are worth being able to name, because they determine how a shock in ' +
        'one economy reaches the other: **trade** (demand for exports falls), **finance** (credit ' +
        'tightens, and trade finance is often the first to be withdrawn), and **the exchange rate** ' +
        '(relative prices move, changing competitiveness in both directions at once).',
    },
    {
      box: {
        kind: 'case',
        title: 'Reading a partner economy in trouble',
        body: [
          'Suppose a country in your portfolio enters a sharp currency depreciation with rising inflation ' +
          'and a widening external deficit. The naive reading is that trade with that market will fall. ' +
          'The analytical reading is more differentiated, and it is the one your members need.',
          {
            bullets: [
              '**Their imports of your consumer goods will fall**, and fastest in discretionary categories.',
              '**Their exports become cheaper**, which may create sourcing opportunities for Turkish importers and can be pitched as such.',
              '**Payment risk rises before demand falls.** Letters of credit become harder to confirm; local banks are affected before local customers are.',
              '**Project and investment activity freezes early**, because it depends on financing rather than on income.',
            ],
          },
          'The brief that says "trade will decline" is not wrong. The brief that says which flows decline, ' +
          'which strengthen, and which risk category moves first is the one that changes what a member ' +
          'company does.',
        ],
      },
    },
    {
      box: {
        kind: 'exercise',
        title: 'The one-page economic snapshot',
        body: [
          'Build a one-page economic snapshot of Türkiye for a visiting foreign delegation, using only the ' +
          'sources in Appendix A. Constraints: one page; every figure carries a source and a date; no ' +
          'adjective that is not supported by a number; and it must end with three sentences on what the ' +
          'picture means for a foreign company considering the market.',
          'Then do the same for a country in your portfolio, and note how much longer it took. That ' +
          'difference is the cost of unfamiliarity, and it is what Chapter 5 exists to reduce.',
        ],
      },
    },
  ],
};

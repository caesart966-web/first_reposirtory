'use strict';

module.exports = {
  title: 'Report Writing and Institutional Communication',
  abstract: [
    'An analysis that is not read changes nothing, and an analysis that is read and misunderstood is ' +
    'worse than none. Institutional writing is therefore not a presentational skill added at the end of ' +
    'the work; it is part of the analysis.',
    'This chapter covers the outputs a specialist produces, the structure that makes them usable, the ' +
    'language that expresses confidence honestly, and two annotated templates you can use on Monday.',
  ],
  outcomes: [
    'Write an executive summary that a decision-maker can act on without reading the body.',
    'Distinguish evidence from assertion in your own drafts, and fix the difference.',
    'Express uncertainty in calibrated language that means the same thing to every reader.',
    'Build a country trade opportunity report and a business council activity brief from a template.',
  ],
  blocks: [
    { h2: 'The outputs, and what each is for' },
    {
      lead: 'Institutional writing fails most often because the author chose the wrong document. A ' +
        'twelve-page analysis where a one-page brief was needed is not thorough; it is a failure to ' +
        'identify the reader\'s decision.',
    },
    {
      table: {
        title: 'Table 6.1 — Output types',
        head: ['Output', 'Length', 'Reader and decision', 'The thing it must contain'],
        widths: [2.4, 1.2, 3.2, 3.2],
        rows: [
          ['Country economic profile', '3–6 pages', 'Members and executives assessing a market', 'A clear verdict on whether and how to engage'],
          ['Bilateral trade opportunity report', '6–12 pages', 'Companies deciding where to allocate effort', 'Specific opportunities at product level, with the obstacle named'],
          ['Business council meeting brief', '1–2 pages', 'The chair and delegation, an hour before the meeting', 'Who is in the room, what they want, what we are asking for'],
          ['Post-visit / mission report', '2–4 pages', 'Institution and participants, after the event', 'Commitments made, by whom, with dates'],
          ['Policy position paper', '4–10 pages', 'Government interlocutors', 'A defensible ask supported by member evidence'],
          ['Event concept note', '1–2 pages', 'Internal approval and partners', 'Objective, audience, format, and how success is measured'],
        ],
      },
    },

    { h2: 'The executive summary' },
    {
      p: 'An executive summary is not a summary. A summary describes the document; an executive summary ' +
        'delivers the conclusion and the reasoning in the order a decision-maker needs them. The test is ' +
        'simple: **if the reader stops after the first page, do they know what to do and why?**',
    },
    {
      steps: [
        '**The judgement, in one sentence.** Not the topic — the finding. "The Vietnamese market is open to Turkish machinery exports but access depends on local certification that most members cannot currently meet."',
        '**The three reasons.** The load-bearing evidence, briefly, with sources.',
        '**What follows from it.** The recommendation, with the option not taken and why.',
        '**The main uncertainty.** What would change the judgement, and what you would need to resolve it.',
      ],
    },
    {
      box: {
        kind: 'warning',
        title: 'The four openings that waste the first paragraph',
        body: [
          {
            bullets: [
              '**"This report examines…"** — the title already said that.',
              '**"In today\'s rapidly changing global environment…"** — true of every year since 1914.',
              '**A history lesson.** Background belongs in the body if it belongs anywhere.',
              '**A methodology paragraph.** Method matters, and it matters in an annex.',
            ],
          },
          'The first sentence of any institutional document should be the thing you would say if you had ' +
          'the reader\'s attention for ten seconds in a corridor.',
        ],
      },
    },

    { h2: 'Evidence and assertion' },
    {
      p: 'Every claim in an institutional document falls into one of four categories, and the reader is ' +
        'entitled to know which. Confusing them is the most common way credible analysts lose ' +
        'credibility.',
    },
    {
      table: {
        title: 'Table 6.2 — Four kinds of claim',
        head: ['Type', 'Example', 'What it requires'],
        widths: [1.8, 4.8, 3.4],
        rows: [
          ['Fact', 'Exports in this heading were X in 2025', 'A source and a date'],
          ['Inference', 'The decline reflects the certification requirement introduced in 2024', 'The reasoning stated, and the alternative explanation addressed'],
          ['Judgement', 'The requirement is unlikely to be relaxed within two years', 'Calibrated language and a basis'],
          ['Recommendation', 'The council should prioritise conformity assessment recognition', 'An explicit link to the objective, and the cost of the alternative'],
        ],
        note: 'A useful self-check: highlight every sentence that is an inference or a judgement. If any lacks a stated basis, it is currently an assertion.',
      },
    },

    { h2: 'Calibrated language' },
    {
      p: 'Words expressing probability are read differently by different people, and the resulting ' +
        'ambiguity has real consequences. The intelligence community addressed this decades ago by fixing ' +
        'a vocabulary and publishing it, an approach worth borrowing.[^On the problem of estimative ' +
        'language see Sherman Kent\'s classic treatment of "words of estimative probability"; on ' +
        'calibration and forecasting practice, Philip E. Tetlock and Dan Gardner, *Superforecasting*, ' +
        'Crown, 2015.]',
    },
    {
      table: {
        title: 'Table 6.3 — A house scale worth adopting',
        head: ['Expression', 'Approximate probability', 'Use when'],
        widths: [2.6, 2.6, 4.8],
        rows: [
          ['Almost certainly', 'above 90 per cent', 'Multiple independent indicators point the same way'],
          ['Likely / probably', '60–90 per cent', 'The balance of evidence is clear but not conclusive'],
          ['Roughly even chance', '40–60 per cent', 'Say this rather than hedging; it is a finding'],
          ['Unlikely', '10–40 per cent', 'Possible, and not the way to plan'],
          ['Remote', 'below 10 per cent', 'Worth naming only if the impact is severe'],
        ],
        note: 'Publish the scale in an annex the first time you use it. A reader who knows your scale can act on your judgement; one who does not is guessing.',
      },
    },
    {
      box: {
        kind: 'field',
        title: 'Three habits that make judgement credible',
        body: [
          {
            bullets: [
              '**Separate confidence from probability.** "Unlikely, but we assess this with low confidence because the data is thin" is more useful — and more honest — than either half alone.',
              '**State the falsifier.** "We would revise this if the tariff schedule published in the second quarter retains the current headings."',
              '**Record the judgement with a date.** A file of dated judgements is how an analyst learns whether their calibration is any good. Almost nobody does this, and it is the fastest route to genuine expertise.',
            ],
          },
        ],
      },
    },

    { h2: 'Tables, charts, and the option of neither' },
    {
      bullets: [
        '**Use a table** when the reader needs to look up a specific value, or when categories are compared on several dimensions at once.',
        '**Use a chart** when the point is a shape — a trend, a distribution, a relationship — and the individual values do not matter.',
        '**Use neither** when the finding is one number. "Exports doubled between 2019 and 2024" needs no chart, and a chart of two data points suggests the author had nothing else.',
        '**Never use a chart to decorate.** A visual that does not carry an argument costs the reader attention and gives nothing back.',
        '**Label the finding, not the data.** A chart titled "Exports by year" wastes its most-read line. "Export growth has stalled since 2023" uses it.',
      ],
    },

    { h2: 'Citation in policy documents' },
    {
      p: 'Policy writing is not academic writing, and importing a full academic apparatus makes a brief ' +
        'harder to use. But a document with no sources cannot be checked, and in an institution whose ' +
        'asset is credibility that is a serious defect. The workable middle is a light in-text attribution ' +
        'with footnotes for anything that could be challenged, and a short source list at the end.',
    },
    {
      bullets: [
        'Cite the **issuing body, the publication and the date** for institutional sources: *IMF, Article IV consultation with [country], [year]*.',
        'Cite **database, indicator and extraction date** for data: a figure without an extraction date cannot be reproduced, because databases are revised.',
        'Cite **author, title, publisher and year** for books and articles, in a consistent style. Which style matters far less than consistency.',
        'Attribute **interviews and meetings** by role and date, not by name, unless you have explicit permission: *interview, senior official, ministry of trade, March 2026*.',
        'Never cite a source you have not opened. Second-hand citation is how errors propagate through an institution, and it is discovered at the worst possible moment.',
      ],
    },

    { h2: 'Writing for four different readers' },
    {
      table: {
        title: 'Table 6.4 — The same finding, four ways',
        head: ['Reader', 'What they need', 'What to cut', 'Tone'],
        widths: [1.8, 3.6, 2.6, 2],
        rows: [
          ['Minister or senior official', 'The judgement, the ask, the political cost', 'Method, sector detail, caveats beyond the main one', 'Brief, decisive, no jargon'],
          ['Chief executive of a member company', 'The commercial consequence and the required action', 'Policy architecture, institutional process', 'Concrete, quantified'],
          ['Foreign counterpart organisation', 'A shared framing and a workable proposal', 'Anything that reads as a demand or a criticism', 'Measured, reciprocal'],
          ['Press', 'A clear, quotable, defensible statement', 'Everything speculative or attributable to a third party', 'Plain, cautious, on-the-record'],
        ],
        note: 'The discipline is not writing four documents. It is writing one analysis and four openings.',
      },
    },

    { h2: 'Annotated template: Country Trade Opportunity Report' },
    {
      p: 'The template below is annotated: the left column is the section, the right column is what an ' +
        'experienced author is doing in it. Sections that cannot be filled with something specific should ' +
        'be removed rather than padded.',
    },
    {
      table: {
        title: 'Table 6.5 — Country Trade Opportunity Report, section by section',
        head: ['Section', 'What goes in it, and why'],
        widths: [3, 7],
        rows: [
          ['1. Executive summary (½ page)', 'The verdict, three reasons, the recommendation, the main uncertainty. Written last, read first, and often the only part read at all.'],
          ['2. Purpose and scope (3 lines)', 'The decision this informs and what is deliberately excluded. This paragraph prevents the most common complaint about analytical work — that it answered a different question.'],
          ['3. Market context (½–1 page)', 'Macro picture at the level needed to judge the opportunity: size, growth, external position, currency, and the two structural facts that explain the rest. Sourced and dated.'],
          ['4. The bilateral relationship today (1 page)', 'Trade at commodity-code level in both directions; investment; the institutional framework — agreement, council, government mechanism. Include the mirror-statistics gap if there is one.'],
          ['5. Opportunities (2–3 pages)', 'The core. Two or three, at product level, each with: the demand evidence, current suppliers, why Türkiye can compete, the obstacle, and what would have to be true.'],
          ['6. Barriers and risks (1 page)', 'Tariff and non-tariff conditions; certification; payment and currency; political and security risk. Likelihood and impact separately, with an indicator for each.'],
          ['7. Recommendation (½ page)', 'What the institution should do, in what order, with the resource implication. Include the option rejected and why — this is what makes a recommendation credible.'],
          ['8. Sources and method (annex)', 'Databases with extraction dates; interviews by role and date; the confidence scale used. Short, and never in the body.'],
        ],
      },
    },

    { h2: 'Annotated template: Bilateral Business Council Activity Brief' },
    {
      table: {
        title: 'Table 6.6 — Meeting brief, one to two pages maximum',
        head: ['Section', 'What goes in it, and why'],
        widths: [3, 7],
        rows: [
          ['Meeting and objective (2 lines)', 'What is happening, and the single outcome we want. If the objective cannot be stated in one sentence, the meeting is not ready.'],
          ['Who is in the room', 'Names, positions, and one line on each: their interest, their constraint, and any relevant history with our side. This is the section chairs actually read.'],
          ['State of the relationship (short paragraph)', 'Trade direction, the last significant development, and the current temperature. No history lesson.'],
          ['Our asks', 'At most three, ranked, each phrased as something the counterpart can actually deliver. An ask directed at the wrong institution wastes the meeting.'],
          ['Their likely asks', 'What they will raise, and our line on each — including what we cannot offer and how to say so without closing the subject.'],
          ['Sensitivities', 'What not to raise, and why. Brief, factual, and written so that disclosure would not embarrass anyone.'],
          ['Follow-up', 'Who records outcomes, when the note circulates, and the review date. Agreed before the meeting, not after.'],
        ],
        note: 'A brief longer than two pages will not be read in the car. That is not a reason to write a longer brief; it is a reason to write a better one.',
      },
    },
    {
      box: {
        kind: 'exercise',
        title: 'Rewrite one page',
        body: [
          'Take a report your organisation produced in the last year. Rewrite only its first page against ' +
          '§6.2: judgement, three reasons, recommendation, main uncertainty. Keep it to one page.',
          'Then compare the two openings and ask which one you would act on. This single exercise, ' +
          'repeated a few times, improves institutional writing more than any amount of reading about it.',
        ],
      },
    },
  ],
};

import type { EssayFixture, RubricItem } from '../components/GradedView'

// Static demo data standing in for a real model response — the graded view always
// renders this fixture regardless of what was actually pasted, until the backend
// exists. See UI-DESIGN-HANDOFF.md "Known mock limitations."
export const DEMO_RUBRIC: RubricItem[] = [
  {
    id: 'thesis',
    label: 'Thesis',
    group: null,
    score: 3,
    missing: false,
    reasoning:
      "The claim states an arguable position tied directly to the text (the green light as unreachable promise), which clears the bar for a 3. A 4 on this rubric requires the claim to preview a specific analytical throughline rather than a general symbolic reading — this thesis gestures at the private/collective shift but doesn't name it as the essay's actual structure.",
    strengths: [
      'Clear, defensible claim you can actually argue against.',
      "Signals both halves of the essay's structure — Gatsby's hope, then the era's — in one sentence.",
    ],
    critiques: [
      'Push past "symbolism matters" to name what\'s actually at stake.',
      'Cut "the heart of" — it\'s filler that softens an otherwise strong claim.',
    ],
  },
  {
    id: 'bp1-claim',
    label: 'Claim',
    group: 'Body ¶1',
    score: 4,
    missing: false,
    reasoning:
      "Meets the 4 bar: the claim is specific to this paragraph (Gatsby's romantic hope as identity-defining), arguable on its own, and explicitly subordinate to the thesis rather than a repetition of it.",
    strengths: ['Sharp and arguable.', 'Ties directly back to the thesis without just restating it.'],
    critiques: ['None — this is model-level for the rubric.'],
  },
  {
    id: 'bp1-evidence-1',
    label: 'Evidence 1',
    group: 'Body ¶1',
    score: 3,
    missing: false,
    reasoning:
      'The quotation is directly relevant and correctly attributed, satisfying the 3-band requirement. It stays at 3 rather than 4 because the top band expects evidence to be introduced with more precision about who is speaking and why it matters here.',
    strengths: ['Well-chosen quotation, clearly connected to the claim.'],
    critiques: [
      "Consider quoting Gatsby's own words instead of only Nick's narration, for variety.",
      'Frame the quote with a sharper lead-in rather than dropping straight into it.',
    ],
  },
  {
    id: 'bp1-reasoning-1',
    label: 'Reasoning 1',
    group: 'Body ¶1',
    score: null,
    missing: true,
    reasoning:
      "The rubric requires an explicit reasoning statement connecting each piece of evidence back to the paragraph's claim. No such sentence follows the first piece of evidence — the paragraph moves straight to a second piece of evidence instead. Because there's nothing present to evaluate, this is flagged as missing rather than scored.",
    strengths: [],
    critiques: [
      'Add a sentence explaining why the reaching-toward-the-water gesture supports the claim that Gatsby has built his identity around this hope.',
      'Right now the paragraph jumps from evidence straight to more evidence — reasoning is what turns evidence into an argument.',
    ],
  },
  {
    id: 'bp1-evidence-2',
    label: 'Evidence 2',
    group: 'Body ¶1',
    score: 3,
    missing: false,
    reasoning:
      'A second, distinct piece of support (the mansion and the parties) that triangulates the first quotation rather than repeating it, meeting the 3-band bar for varied evidence. Held at 3 because the connection between this detail and the paragraph\'s claim is stated rather than shown through close reading of specific word choice.',
    strengths: [
      'Genuinely different kind of evidence than the first — action/choice rather than physical gesture.',
      'Strengthens the paragraph by not relying on a single moment.',
    ],
    critiques: [
      'Point to a specific phrase or detail rather than summarizing the mansion/parties in general terms.',
      'This pairs well with Evidence 1 — say so explicitly, so the reader sees the paragraph building a case rather than listing examples.',
    ],
  },
  {
    id: 'bp1-reasoning-2',
    label: 'Reasoning 2',
    group: 'Body ¶1',
    score: 2,
    missing: false,
    reasoning:
      "Held at 2 because this reasoning restates what the evidence shows (parties as bait) without explaining why that specific mechanism matters to the paragraph's claim about identity — the 3-band bar requires reasoning that adds interpretation, not just paraphrase.",
    strengths: ['Correctly identifies the parties as strategic rather than social.'],
    critiques: [
      'Push past restating the evidence — explain why organizing his whole life around one possible arrival is what makes this "identity-defining," per the claim.',
      'This is the shortest reasoning in the essay; it needs another sentence to earn its place next to Reasoning 1.',
    ],
  },
  {
    id: 'bp1-synthesis',
    label: 'Synthesis',
    group: 'Body ¶1',
    score: 2,
    missing: false,
    reasoning:
      "Scored at 2, not 3, because synthesis on this rubric specifically requires connecting the paragraph's claim to something outside the immediate scene. This paragraph's final sentence restates the scene's emotional stakes rather than reaching outward.",
    strengths: ["Correctly links the moment back to this paragraph's own claim."],
    critiques: [
      'Reach outside the novel — to the 1920s context or a second text — that\'s what synthesis at this level asks for.',
      'Right now this paragraph could stand alone in a summary; push past restating the scene.',
    ],
  },
  {
    id: 'bp2-claim',
    label: 'Claim',
    group: 'Body ¶2',
    score: 4,
    missing: false,
    reasoning:
      'Meets the 4 bar on the same grounds as the Body ¶1 claim, and does it more cleanly — the claim explicitly escalates the argument rather than parallel-repeating paragraph one\'s structure.',
    strengths: [
      'The strongest claim in the essay — confident and precise.',
      'Clearly escalates from paragraph one instead of repeating it.',
    ],
    critiques: ['None — this is model-level for the rubric.'],
  },
  {
    id: 'bp2-evidence-1',
    label: 'Evidence 1',
    group: 'Body ¶2',
    score: 4,
    missing: false,
    reasoning:
      "Unlike Body ¶1's first piece of evidence, this quotation does interpretive work in the choosing itself, which meets the top-band bar for evidence that's integrated rather than dropped in.",
    strengths: ['Well-chosen and smoothly integrated — does real interpretive work rather than decorating the paragraph.'],
    critiques: ['None — this is model-level for the rubric.'],
  },
  {
    id: 'bp2-reasoning-1',
    label: 'Reasoning 1',
    group: 'Body ¶2',
    score: 3,
    missing: false,
    reasoning:
      "Reasoning is logically sound and follows from the evidence, meeting the 3-band bar. Held at 3 rather than 4 because roughly a third of the sentence re-states the claim instead of extending it.",
    strengths: ['Solid, logical line of reasoning that follows directly from the evidence.'],
    critiques: [
      'Cut the restatement of the claim — trust the reader to remember it.',
      'Spend that space instead on what "we" specifically implicates about the reader.',
    ],
  },
  {
    id: 'bp2-evidence-2',
    label: 'Evidence 2',
    group: 'Body ¶2',
    score: 4,
    missing: false,
    reasoning:
      "A second, well-chosen piece of support (the Dutch sailors' first sighting of the continent) that widens the paragraph's scope exactly as the claim promises, meeting the top band for evidence that's purposefully sequenced rather than merely additional.",
    strengths: [
      "Excellent choice — extends the essay's central image from Gatsby to a founding national moment.",
      'Placed at the end of the paragraph, which gives it real weight.',
    ],
    critiques: ['None — this is model-level for the rubric.'],
  },
  {
    id: 'bp2-reasoning-2',
    label: 'Reasoning 2',
    group: 'Body ¶2',
    score: 4,
    missing: false,
    reasoning:
      "This reasoning does what Reasoning 1 didn't quite manage — it explains the significance of the evidence (this is a smaller model of a national pattern) rather than restating it, meeting the top-band bar.",
    strengths: [
      "Correctly identifies that this parallel reframes the whole essay's stakes, not just this paragraph's.",
      'Confident, precise closing move for the paragraph.',
    ],
    critiques: ['None — this is model-level for the rubric.'],
  },
  {
    id: 'bp2-synthesis',
    label: 'Synthesis',
    group: 'Body ¶2',
    score: 3,
    missing: false,
    reasoning:
      'Reaches outside the immediate scene toward a broader pattern (the American Dream), which is what separates this from the Body ¶1 synthesis score. Held at 3 rather than 4 because the connection is implied through description rather than named directly.',
    strengths: ['Gestures at the American Dream motif — the right instinct.'],
    critiques: [
      'Name "American Dream" explicitly — right now it\'s implied, which under-sells a strong observation.',
      "Tie back to paragraph one's private/collective distinction to unify the essay.",
    ],
  },
  {
    id: 'conclusion',
    label: 'Conclusion',
    group: null,
    score: 3,
    missing: false,
    reasoning:
      'Accurately synthesizes the essay\'s two-part argument and ends on a purposeful image, meeting the 3-band bar. Held at 3 rather than 4 because the rubric\'s top band for Conclusion asks for a stated "so what" beyond the text, which isn\'t present here.',
    strengths: ['Restates the two-symbol argument cleanly.', 'Ends on a strong, memorable final image.'],
    critiques: [
      'Add one sentence on why this distinction still matters to a reader today.',
      "Consider moving the final clause earlier and ending on the essay's own claim instead.",
    ],
  },
]

export const DEMO_ESSAY: EssayFixture = {
  title: 'The Green Light and the Limits of Longing',
  paras: [
    [
      {
        id: 'thesis',
        text: "In The Great Gatsby, Fitzgerald uses the green light at the end of Daisy's dock as a symbol of the unreachable promises at the heart of the American Dream, one that begins as private longing and ends as a verdict on the era itself.",
      },
    ],
    [
      {
        id: 'bp1-claim',
        text: "In the novel's early chapters, the light functions specifically as a symbol of Gatsby's romantic hope, a single point of meaning he has built an entire identity around reaching. ",
      },
      {
        id: 'bp1-evidence-1',
        text: 'Nick describes Gatsby stretching his arms toward the water, trembling, fixed on a light that is, to anyone else, unremarkable. ',
      },
      { id: 'bp1-reasoning-1', missing: true },
      {
        id: 'bp1-evidence-2',
        text: 'The same hope shapes his choices as much as his posture: he buys a mansion directly across the bay from Daisy\'s dock and fills it nightly with strangers on the chance that she might wander in. ',
      },
      {
        id: 'bp1-reasoning-2',
        text: 'Every party, then, is not really for the guests — it is bait, organized around a single possible arrival, which shows how completely this hope has reorganized his life. ',
      },
      {
        id: 'bp1-synthesis',
        text: 'This private, almost religious hope is what makes his later disillusionment land so hard — the object was never going to survive contact with the person.',
      },
    ],
    [
      {
        id: 'bp2-claim',
        text: "By the novel's final page, however, Fitzgerald widens the light from Gatsby's private symbol into a verdict on the American Dream itself. ",
      },
      {
        id: 'bp2-evidence-1',
        text: "The closing lines describe humanity born to keep striving, carried backward by the very past it's trying to outrun, chasing a future that recedes exactly as fast as we approach it. ",
      },
      {
        id: 'bp2-reasoning-1',
        text: "That widened focus is doing real work: the failure Nick describes is no longer Gatsby's alone, it belongs to anyone who has organized their life around a promise just out of reach. ",
      },
      {
        id: 'bp2-evidence-2',
        text: 'Fitzgerald reaches even further back, invoking the Dutch sailors who first saw the continent itself as a fresh, unclaimed promise. ',
      },
      {
        id: 'bp2-reasoning-2',
        text: "Placed at the very end, that image reframes everything before it: Gatsby's failed romance becomes a smaller-scale model of a much older American habit of chasing horizons that keep receding. ",
      },
      {
        id: 'bp2-synthesis',
        text: "In this light, Gatsby's death reads less as a personal tragedy and more as an early case study of a distinctly American form of hope.",
      },
    ],
    [
      {
        id: 'conclusion',
        text: "The green light, then, is not one symbol but two: first Gatsby's, then everyone's, and Fitzgerald's genius is making the second impossible to unsee once he has shown you the first.",
      },
    ],
  ],
}
